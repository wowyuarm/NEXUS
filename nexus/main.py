"""
NEXUS engine launcher.

Initializes the NexusBus and core services, wires up subscriptions, and runs
long-lived tasks concurrently.
"""

import asyncio
import logging
import os
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from nexus.core.bus import NexusBus
from nexus.interfaces.websocket import WebsocketInterface
from nexus.interfaces import rest
from nexus.services.config import ConfigService
from nexus.services.database.service import DatabaseService
from dotenv import load_dotenv
from nexus.services.llm.service import LLMService
from nexus.services.tool_executor import ToolExecutorService
from nexus.services.context import ContextService
from nexus.services.orchestrator import OrchestratorService
from nexus.services.persistence import PersistenceService
from nexus.services.command import CommandService
from nexus.services.identity import IdentityService
from nexus.tools.registry import ToolRegistry


def _setup_logging() -> None:
    """Configure baseline logging for the engine."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


async def main() -> None:
    """Main entrypoint: initialize bus, services, subscriptions, and run tasks."""
    _setup_logging()
    logger = logging.getLogger("nexus.main")

    # 1): Environment Determination
    load_dotenv()
    environment = os.getenv("NEXUS_ENV", "development")
    logger.info(f"Running in '{environment}' environment")

    # 2): Bootstrap Configuration
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        logger.error("MONGO_URI not found in environment variables. Please check your .env file.")
        return
    
    # Dynamic database name based on environment
    db_name = f"NEXUS_DB_{'DEV' if environment == 'development' else 'PROD'}"
    logger.info(f"Bootstrap configuration - Environment: {environment}, DB: {db_name}")

    # 3): Core Dependency Connection
    logger.info("Initializing database service...")
    bus = NexusBus()
    database_service = DatabaseService(bus, mongo_uri, db_name)
    
    logger.info("Connecting to database...")
    if not database_service.connect():
        logger.error("Failed to connect to database. Please check your MongoDB instance and MONGO_URI configuration.")
        return
    logger.info("Database connection established successfully")

    # 4): Application Configuration Loading
    logger.info("Initializing configuration service...")
    config_service = ConfigService(database_service)
    await config_service.initialize(environment)
    logger.info("Configuration service initialized successfully")

    # 5): Application Construction & Run
    tool_registry = ToolRegistry()

    # Auto-discover and register all tools
    tool_registry.discover_and_register('nexus.tools.definition')
    logger.info("Tools auto-discovery and registration completed")

    # 6) Instantiate services and interfaces with proper dependency injection
    # Order matters: dependencies must be created before dependents

    # Identity service for user identity management
    identity_service = IdentityService(db_service=database_service)

    # Persistence service depends on database service only
    # (Identity gating is handled by OrchestratorService)
    persistence_service = PersistenceService(database_service)

    # Other services
    llm_service = LLMService(bus, config_service)
    tool_executor_service = ToolExecutorService(bus, tool_registry)

    # Context service now depends on config and persistence services
    context_service = ContextService(bus, tool_registry, config_service, persistence_service)

    # Command service for deterministic command processing (inject identity_service)
    command_service = CommandService(bus, database_service=database_service, identity_service=identity_service)

    # Orchestrator service with identity gatekeeper (inject identity_service)
    orchestrator_service = OrchestratorService(bus, config_service, identity_service=identity_service)
    websocket_interface = WebsocketInterface(bus, database_service, identity_service)

    services: List[object] = [
        database_service,
        persistence_service,
        llm_service,
        tool_executor_service,
        context_service,
        command_service,
        orchestrator_service,
        websocket_interface,
    ]

    # 7) Wire subscriptions
    for svc in services:
        subscribe = getattr(svc, "subscribe_to_bus", None)
        if callable(subscribe):
            subscribe()
            logger.info("%s subscribed to bus", svc.__class__.__name__)

    # 8) Get server configuration from config service
    server_host = config_service.get("server.host", "127.0.0.1")
    server_port = config_service.get_int("server.port", 8000)

    # 9) Create unified FastAPI application
    app = FastAPI(title="NEXUS API", version="2.0.0")
    logger.info("Created unified FastAPI application")
    
    # 9.5) Configure CORS middleware with environment-aware origins
    allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "")
    origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]
    
    # Security: Production without configured origins = block all
    if environment == "production" and not origins:
        logger.warning("⚠️ No ALLOWED_ORIGINS configured for production. CORS requests will be blocked.")
        origins = []
    
    logger.info(f"CORS configured for origins: {origins}")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # 10) Add health check endpoints
    @app.get("/")
    async def root_health():
        return {"status": "ok", "service": "NEXUS API"}

    @app.get("/health")
    async def basic_health():
        return {"status": "healthy", "connections": len(websocket_interface.connections)}

    @app.get("/api/v1/health")
    async def comprehensive_health_check():
        """Comprehensive health check including database connectivity."""
        try:
            is_db_healthy = database_service.provider.health_check()
            
            if is_db_healthy:
                return {"status": "ok", "dependencies": {"database": "ok"}}
            else:
                raise HTTPException(
                    status_code=503, 
                    detail={"status": "error", "dependencies": {"database": "unavailable"}}
                )
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(
                status_code=503,
                detail={"status": "error", "dependencies": {"database": "connection_error"}}
            )
    
    # 11) Configure dependency injection for REST interface
    app.dependency_overrides[rest.get_command_service] = lambda: command_service
    logger.info("Configured dependency injection for REST interface")
    
    # 12) Add REST API routes
    app.include_router(rest.router, prefix="/api/v1", tags=["commands"])
    logger.info("Added REST API routes")
    
    # 13) Add WebSocket routes
    websocket_interface.add_websocket_routes(app)
    logger.info("Added WebSocket routes")

    # 14) Long-running tasks (bus listeners)
    bus_task = asyncio.create_task(bus.run_forever(), name="nexusbus.run_forever")

    logger.info(f"NEXUS engine configured with FastAPI app at {server_host}:{server_port}")

    # 15) Import uvicorn and run the FastAPI app
    import uvicorn

    # Create a task for the uvicorn server
    config = uvicorn.Config(app, host=server_host, port=server_port, log_level="info")
    server = uvicorn.Server(config)

    # Run bus and server concurrently
    try:
        await asyncio.gather(
            bus_task,
            server.serve()
        )
    except asyncio.CancelledError:
        logger.info("Shutdown requested; cancelling tasks...")
        bus_task.cancel()
        await server.shutdown()
        # Best-effort wait for cancellations
        await asyncio.gather(bus_task, return_exceptions=True)
        logger.info("All tasks cancelled. Exiting.")


if __name__ == "__main__":
    asyncio.run(main())
