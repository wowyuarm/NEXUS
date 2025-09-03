"""
Pytest fixtures for NEXUS end-to-end testing.

Provides isolated test environment with temporary MongoDB database
and full NEXUS service lifecycle management.
"""

import asyncio
import multiprocessing
import os
import socket
import subprocess
import time
import uuid
from typing import Generator

import httpx
from dotenv import load_dotenv
import pytest
from pymongo import MongoClient


@pytest.fixture(scope="session")
def nexus_service() -> Generator[str, None, None]:
    """
    Fixture that starts NEXUS service in isolated environment.
    
    Creates temporary MongoDB database and patches configuration
    to ensure complete isolation from production environment.
    
    Yields:
        WebSocket URL for connecting to the NEXUS service
    """
    # Generate unique temporary database name (shorter to respect MongoDB limits)
    temp_db_name = f"test_{uuid.uuid4().hex[:16]}"
    
    # Ensure local connections are not routed via proxies which can cause 502/handshake issues
    # We also set NO_PROXY for localhost explicitly. Keep a copy to restore later.
    original_environ = dict(os.environ)
    for key in ["http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"]:
        if key in os.environ:
            os.environ.pop(key, None)
    # Preserve existing NO_PROXY entries while ensuring localhost is excluded from proxying
    existing_no_proxy = original_environ.get("NO_PROXY") or original_environ.get("no_proxy") or ""
    no_proxy_hosts = [h.strip() for h in existing_no_proxy.split(",") if h.strip()]
    for host in ["127.0.0.1", "localhost"]:
        if host not in no_proxy_hosts:
            no_proxy_hosts.append(host)
    os.environ["NO_PROXY"] = ",".join(no_proxy_hosts)

    # Kill any process using port 8000 to avoid conflicts
    _kill_process_on_port(8000)
    
    # Start NEXUS service in subprocess with environment variables
    # Use inherited stdout/stderr so that service logs are visible during tests
    # This greatly helps diagnosing startup issues (e.g., database connectivity)
    env_vars = dict(os.environ)
    # Enable fake LLM path to ensure deterministic E2E without external providers
    env_vars["NEXUS_E2E_FAKE_LLM"] = "1"
    # Ensure child process uses an isolated temporary DB
    env_vars["NEXUS_TEST_DB_NAME"] = temp_db_name

    process = subprocess.Popen(
        ["python", "-m", "nexus.main"],
        env=env_vars,
        stdout=None,  # inherit
        stderr=None   # inherit
    )
    
    # Print process info for debugging
    print(f"Started NEXUS service with PID: {process.pid}")
    
    # Wait for service to start and become fully ready
    service_url = "ws://127.0.0.1:8000"
    # Give the service a moment to start up before health checks
    time.sleep(2.0)
    _wait_for_service_ready()
    
    # Give the service a moment to fully initialize after health check passes
    time.sleep(1.0)
    
    yield service_url
    
    # Cleanup: terminate service and delete temporary database
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
    
    # Print subprocess output for debugging
    stdout, stderr = process.communicate()
    if stdout:
        print(f"NEXUS service stdout:\n{stdout.decode()}")
    if stderr:
        print(f"NEXUS service stderr:\n{stderr.decode()}")
    
    # Restore environment variables (proxies and others)
    os.environ.clear()
    os.environ.update(original_environ)
    
    # Clean up temporary database
    _cleanup_temp_database(temp_db_name)


def _kill_process_on_port(port: int) -> None:
    """Kill any process using the specified port."""
    import subprocess
    try:
        # Find PID of process using the port
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"], 
            capture_output=True, 
            text=True
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid.strip():
                    subprocess.run(["kill", "-9", pid.strip()], capture_output=True)
                    print(f"Killed process {pid} using port {port}")
    except Exception as e:
        print(f"Warning: Failed to kill process on port {port}: {e}")


def _wait_for_service_ready(timeout: int = 60) -> None:
    """Wait for NEXUS service to become fully ready using health check endpoint."""
    health_check_url = "http://127.0.0.1:8000/api/v1/health"
    
    start_time = time.time()
    last_error = None
    
    while time.time() - start_time < timeout:
        try:
            # Use httpx to check health endpoint
            # Disable proxy usage from environment to avoid localhost going through proxies (which can yield 502)
            response = httpx.get(health_check_url, timeout=5.0, trust_env=False)
            
            if response.status_code == 200:
                health_data = response.json()
                if health_data.get("status") == "ok" and health_data.get("dependencies", {}).get("database") == "ok":
                    print(f"NEXUS service fully ready with healthy database")
                    return
                else:
                    print(f"Service available but not fully healthy: {health_data}")
                    time.sleep(1.0)
            elif response.status_code == 503:
                # Service is up but database is not ready yet
                print(f"Service available but database not ready: {response.json()}")
                time.sleep(1.0)
            else:
                print(f"Unexpected health check status: {response.status_code}, response: {response.text}, headers: {dict(response.headers)}")
                time.sleep(1.0)
                
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            # Service not yet accepting connections
            last_error = e
            time.sleep(0.5)
        except Exception as e:
            last_error = e
            print(f"Error during health check: {e}")
            time.sleep(1.0)
    
    # If we get here, service didn't become ready in time
    error_msg = f"NEXUS service did not become fully ready within {timeout} seconds"
    if last_error:
        error_msg += f". Last error: {last_error}"
    raise TimeoutError(error_msg)


def _cleanup_temp_database(db_name: str) -> None:
    """Clean up temporary MongoDB database."""
    try:
        # Get MongoDB connection details from environment - use the same URI as the service
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            # Attempt to load from project .env to support cleanup from test runner process
            try:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(current_dir)
                env_path = os.path.join(project_root, ".env")
                if os.path.exists(env_path):
                    load_dotenv(env_path)
                    mongo_uri = os.getenv("MONGO_URI")
            except Exception as _:
                pass
            if not mongo_uri:
                print(f"Warning: MONGO_URI not set, cannot clean up database {db_name}")
                return
        
        client = MongoClient(mongo_uri)
        client.drop_database(db_name)
        print(f"Cleaned up temporary database: {db_name}")
        client.close()
    except Exception as e:
        print(f"Warning: Failed to clean up temporary database {db_name}: {e}")


@pytest.fixture
def test_session_id() -> str:
    """Generate a unique session ID for each test."""
    return f"test_session_{uuid.uuid4().hex}"