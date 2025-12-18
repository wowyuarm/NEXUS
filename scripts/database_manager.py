#!/usr/bin/env python3
"""
NEXUS Database Management Tool

A comprehensive database management tool for NEXUS that provides:
- Interactive database and collection selection
- Advanced filtering and deletion options
- Batch operations and data export
- Real-time statistics and monitoring
- Safe operation with confirmation prompts

Usage:
    python scripts/database_manager.py [COMMAND] [OPTIONS]

Commands:
    list-dbs          List all databases
    list-collections  List collections in selected database
    stats             Show database statistics
    interactive       Interactive mode (default)
    cleanup           Clean up data
    export            Export data to file
    analyze           Analyze data patterns

Interactive Mode:
    menu              Show interactive menu
    select-db         Select database to work with
    select-collection Select collection to work with

Examples:
    python scripts/database_manager.py --interactive
    python scripts/database_manager.py --list-dbs
    python scripts/database_manager.py --stats
    python scripts/database_manager.py --cleanup --collection messages --role HUMAN --days 30
"""

import sys
import os
import argparse
import logging
import json
import yaml
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from nexus.services.database.providers.mongo import MongoProvider
    from nexus.core.models import Role
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some dependencies not available: {e}")
    print("Limited functionality mode - database operations will be simulated.")
    DEPENDENCIES_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OperationMode(Enum):
    """Operation modes for the database manager."""
    INTERACTIVE = "interactive"
    CLEANUP = "cleanup"
    STATS = "stats"
    EXPORT = "export"
    ANALYZE = "analyze"
    INIT_CONFIG = "init_config"


class FilterStrategy(Enum):
    """Filtering strategies for data operations."""
    BY_AGE = "by_age"
    BY_ROLE = "by_role"
    BY_SESSION = "by_session"
    BY_CONTENT = "by_content"
    BY_CUSTOM = "by_custom"


@dataclass
class DatabaseConfig:
    """Database configuration."""
    mongo_uri: str
    database_name: str
    environment: str = "development"


@dataclass
class CleanupOptions:
    """Options for cleanup operations."""
    collection: str
    count: int = 100
    days: Optional[int] = None
    role: Optional[str] = None  # Use string instead of Role enum for flexibility
    session_id: Optional[str] = None
    content_filter: Optional[str] = None
    newest_first: bool = False
    dry_run: bool = False
    force: bool = False


@dataclass
class ExportOptions:
    """Options for export operations."""
    collection: str
    output_file: str
    format: str = "json"  # json, csv
    filter_query: Optional[Dict[str, Any]] = None
    limit: Optional[int] = None


@dataclass
class InitConfigOptions:
    """Options for configuration initialization."""
    environment: str = "development"
    force: bool = False


class DatabaseManager:
    """Enhanced database management utility for NEXUS."""

    def __init__(self, config: DatabaseConfig):
        """Initialize the database manager."""
        self.config = config
        self.provider: Optional[MongoProvider] = None
        self.client = None
        self.current_db = config.database_name
        self.project_root = Path(__file__).parent.parent
        self._initialize_connection()

    def _initialize_connection(self) -> None:
        """Initialize database connection."""
        global DEPENDENCIES_AVAILABLE

        if not DEPENDENCIES_AVAILABLE:
            logger.warning("Dependencies not available - using mock mode")
            self.client = None
            self.provider = None
            return

        try:
            from pymongo import MongoClient

            self.client = MongoClient(self.config.mongo_uri)
            self.client.admin.command('ping')

            self.provider = MongoProvider(self.config.mongo_uri, self.current_db)
            self.provider.connect()

            logger.info(f"Connected to database: {self.current_db}")

        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            logger.warning("Falling back to mock mode")
            self.client = None
            self.provider = None

    def list_databases(self) -> List[str]:
        """List all available databases."""
        if not self.client:
            # Mock databases for testing
            return ["NEXUS_DB_DEV", "NEXUS_DB_PROD", "NEXUS_DB_TEST"]

        try:
            databases = self.client.list_database_names()
            return [db for db in databases if not db.startswith(('admin', 'config', 'local'))]
        except Exception as e:
            logger.error(f"Error listing databases: {e}")
            return []

    def list_collections(self, db_name: Optional[str] = None) -> List[str]:
        """List collections in a database."""
        if not self.client:
            # Mock collections for testing
            return ["messages", "system_configurations", "sessions"]

        try:
            target_db = db_name or self.current_db
            database = self.client[target_db]
            return database.list_collection_names()
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            return []

    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics for a collection."""
        if not self.client:
            # Mock stats for testing
            mock_stats = {
                "messages": {"document_count": 15420, "storage_size": 5242880},
                "system_configurations": {"document_count": 5, "storage_size": 1024},
                "sessions": {"document_count": 342, "storage_size": 512000}
            }
            return mock_stats.get(collection_name, {"document_count": 0, "storage_size": 0})

        try:
            database = self.client[self.current_db]
            collection = database[collection_name]

            stats = {
                'document_count': collection.count_documents({}),
                'storage_size': 0,
                'index_size': 0
            }

            try:
                coll_stats = database.command('collstats', collection_name)
                stats.update({
                    'storage_size': coll_stats.get('size', 0),
                    'index_size': coll_stats.get('totalIndexSize', 0),
                    'avg_obj_size': coll_stats.get('avgObjSize', 0),
                    'count': coll_stats.get('count', 0)
                })
            except Exception:
                pass

            return stats
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {}

    def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics."""
        collections = self.list_collections()

        stats = {
            'database_name': self.current_db,
            'collections': collections,
            'collection_stats': {},
            'total_documents': 0,
            'total_storage': 0
        }

        for collection_name in collections:
            coll_stats = self.get_collection_stats(collection_name)
            stats['collection_stats'][collection_name] = coll_stats
            stats['total_documents'] += coll_stats.get('document_count', 0)
            stats['total_storage'] += coll_stats.get('storage_size', 0)

        return stats

    def switch_database(self, db_name: str) -> bool:
        """Switch to a different database."""
        try:
            if db_name not in self.list_databases():
                logger.warning(f"Database '{db_name}' does not exist")
                return False

            self.current_db = db_name
            self.provider = MongoProvider(self.config.mongo_uri, db_name)
            self.provider.connect()

            logger.info(f"Switched to database: {db_name}")
            return True
        except Exception as e:
            logger.error(f"Error switching database: {e}")
            return False

    def build_filter_query(self, options: CleanupOptions) -> Dict[str, Any]:
        """Build MongoDB filter query based on options."""
        query = {}

        # Date filtering
        if options.days:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=options.days)
            if options.collection == 'identities':
                query['created_at'] = {'$lt': cutoff_date}
            elif options.collection == 'configurations':
                # configurations may not have timestamp, skip date filtering
                pass
            else:
                query['timestamp'] = {'$lt': cutoff_date}

        # Role filtering (only for messages collection)
        if options.role and options.collection not in ['identities', 'configurations']:
            query['role'] = options.role

        # Session filtering (only for messages collection)
        if options.session_id and options.collection not in ['identities', 'configurations']:
            query['session_id'] = options.session_id

        # Content filtering (only for messages collection)
        if options.content_filter and options.collection not in ['identities', 'configurations']:
            query['content'] = {'$regex': options.content_filter, '$options': 'i'}

        return query

    def get_documents_to_delete(self, options: CleanupOptions) -> List[Dict[str, Any]]:
        """Get documents that match deletion criteria."""
        if not self.provider:
            # Mock documents for testing
            mock_docs = [
                {
                    'id': f'msg_{i}',
                    'timestamp': '2024-01-01T10:00:00Z',
                    'role': 'HUMAN' if i % 2 == 0 else 'AI',
                    'content': f'This is a sample message {i}',
                    'session_id': 'session_123'
                }
                for i in range(min(options.count, 10))
            ]
            return mock_docs

        try:
            # Map collection names to provider attributes
            if options.collection == 'configurations':
                collection = self.provider.config_collection
            else:
                collection = getattr(self.provider, f'{options.collection}_collection')
            if collection is None:
                logger.error(f"Collection '{options.collection}' not found")
                return []

            query = self.build_filter_query(options)

            # Sort direction: -1 for descending (newest first), 1 for ascending (oldest first)
            sort_direction = -1 if options.newest_first else 1

            # Determine sort field based on collection type
            if options.collection == 'identities':
                sort_field = 'created_at'
            elif options.collection == 'configurations':
                sort_field = '_id'  # configurations may not have timestamp
            else:
                sort_field = 'timestamp'

            cursor = collection.find(query).sort(sort_field, sort_direction).limit(options.count)
            documents = list(cursor)

            # Convert ObjectId to string for display
            for doc in documents:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                # Ensure document has an 'id' field for deletion logic
                if 'id' not in doc:
                    # For identities collection, use public_key as id
                    if options.collection == 'identities' and 'public_key' in doc:
                        doc['id'] = doc['public_key']
                    # For configurations collection, use environment as id
                    elif options.collection == 'configurations' and 'environment' in doc:
                        doc['id'] = doc['environment']
                    # Fallback to _id
                    elif '_id' in doc:
                        doc['id'] = str(doc['_id'])
                    else:
                        # Generate a placeholder (should not happen)
                        doc['id'] = 'unknown'

            return documents
        except Exception as e:
            logger.error(f"Error getting documents to delete: {e}")
            return []

    def delete_documents(self, collection_name: str, document_ids: List[str]) -> int:
        """Delete documents by their IDs."""
        if not self.provider:
            # Mock deletion for testing
            logger.info(f"Mock deleted {len(document_ids)} documents from {collection_name}")
            return len(document_ids)

        try:
            # Map collection names to provider attributes
            if collection_name == 'configurations':
                collection = self.provider.config_collection
            else:
                collection = getattr(self.provider, f'{collection_name}_collection')
            if collection is None:
                logger.error(f"Collection '{collection_name}' not found")
                return 0

            # Determine field to use for deletion based on collection type
            if collection_name == 'identities':
                field_name = 'public_key'
            elif collection_name == 'configurations':
                field_name = 'environment'
            else:
                field_name = 'id'

            result = collection.delete_many({
                field_name: {"$in": document_ids}
            })

            deleted_count = result.deleted_count
            logger.info(f"Successfully deleted {deleted_count} documents")
            return deleted_count
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return 0

    def cleanup_collection(self, options: CleanupOptions) -> bool:
        """Clean up documents from a collection."""
        try:
            # Get collection statistics
            stats = self.get_collection_stats(options.collection)
            total_docs = stats.get('document_count', 0)

            # Get documents to delete
            documents_to_delete = self.get_documents_to_delete(options)

            if not documents_to_delete:
                print("No documents found matching the criteria.")
                return True

            print(f"\n=== Cleanup Report ===")
            print(f"Collection: {options.collection}")
            print(f"Total documents: {total_docs}")
            print(f"Documents to delete: {len(documents_to_delete)}")
            print(f"Strategy: {'NEWEST' if options.newest_first else 'OLDEST'}")

            if options.dry_run:
                print(f"\n[DRY RUN] Would delete {len(documents_to_delete)} documents")
                return True

            # Show preview
            print(f"\n=== Documents to be deleted ===")
            for i, doc in enumerate(documents_to_delete[:5]):
                if options.collection == 'identities':
                    timestamp = doc.get('created_at', 'Unknown')
                    doc_id = doc.get('public_key', 'Unknown')
                    role = 'IDENTITY'
                    content = f"config_overrides: {len(doc.get('config_overrides', {}))}, prompt_overrides: {len(doc.get('prompt_overrides', {}))}"
                elif options.collection == 'configurations':
                    timestamp = 'N/A'
                    doc_id = doc.get('environment', 'Unknown')
                    role = 'CONFIG'
                    content = f"system: {len(doc.get('system', {}))}, llm: {len(doc.get('llm', {}))}"
                else:
                    timestamp = doc.get('timestamp', 'Unknown')
                    doc_id = doc.get('id', 'Unknown')
                    role = doc.get('role', 'Unknown')
                    content = str(doc.get('content', ''))[:50] + '...' if len(str(doc.get('content', ''))) > 50 else str(doc.get('content', ''))
                print(f"{i+1}. {timestamp} | {role} | {doc_id} | {content}")

            if len(documents_to_delete) > 5:
                print(f"... and {len(documents_to_delete) - 5} more documents")

            # Confirmation
            if not options.force:
                response = input(f"\nDelete {len(documents_to_delete)} documents? (yes/no): ").lower().strip()
                if response not in ['yes', 'y']:
                    print("Cleanup cancelled.")
                    return False

            # Perform deletion
            document_ids = [doc['id'] for doc in documents_to_delete]
            deleted_count = self.delete_documents(options.collection, document_ids)

            print(f"\n=== Cleanup Complete ===")
            print(f"Successfully deleted {deleted_count} documents")

            return deleted_count > 0
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return False

    def export_collection(self, options: ExportOptions) -> bool:
        """Export collection data to file."""
        try:
            # Map collection names to provider attributes
            if options.collection == 'configurations':
                collection = self.provider.config_collection
            else:
                collection = getattr(self.provider, f'{options.collection}_collection')
            if collection is None:
                logger.error(f"Collection '{options.collection}' not found")
                return False

            query = options.filter_query or {}
            cursor = collection.find(query)

            if options.limit:
                cursor = cursor.limit(options.limit)

            documents = list(cursor)

            # Convert ObjectId to string
            for doc in documents:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])

            # Save to file
            output_path = Path(options.output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if options.format == 'json':
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(documents, f, indent=2, default=str)
            elif options.format == 'csv':
                import csv
                if documents:
                    with open(output_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=documents[0].keys())
                        writer.writeheader()
                        writer.writerows(documents)

            print(f"Exported {len(documents)} documents to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error during export: {e}")
            return False

    def analyze_collection(self, collection_name: str) -> Dict[str, Any]:
        """Analyze collection data patterns."""
        try:
            # Map collection names to provider attributes
            if collection_name == 'configurations':
                collection = self.provider.config_collection
            else:
                collection = getattr(self.provider, f'{collection_name}_collection')
            if collection is None:
                return {}

            # Basic stats
            total_docs = collection.count_documents({})

            # Role distribution
            pipeline = [
                {"$group": {"_id": "$role", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            role_distribution = list(collection.aggregate(pipeline))

            # Time range
            oldest = collection.find().sort("timestamp", 1).limit(1)
            newest = collection.find().sort("timestamp", -1).limit(1)

            oldest_doc = list(oldest)[0] if oldest else None
            newest_doc = list(newest)[0] if newest else None

            # Session analysis
            pipeline = [
                {"$group": {"_id": "$session_id", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            top_sessions = list(collection.aggregate(pipeline))

            return {
                'collection_name': collection_name,
                'total_documents': total_docs,
                'role_distribution': role_distribution,
                'time_range': {
                    'oldest': oldest_doc.get('timestamp') if oldest_doc else None,
                    'newest': newest_doc.get('timestamp') if newest_doc else None
                },
                'top_sessions': top_sessions
            }
        except Exception as e:
            logger.error(f"Error analyzing collection: {e}")
            return {}


    def load_config_template(self) -> dict:
        """Load configuration template from config.example.yml."""
        config_file = self.project_root / "config.example.yml"
        
        if not config_file.exists():
            logger.error(f"Configuration template not found: {config_file}")
            print(f"✗ Error: Configuration template file not found: {config_file}")
            raise FileNotFoundError(f"Configuration template not found: {config_file}")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"Successfully loaded configuration template from: {config_file}")
            print(f"✓ Successfully loaded configuration template: {config_file}")
            return config
        except Exception as e:
            logger.error(f"Error loading configuration template: {e}")
            print(f"✗ Failed to load configuration template: {e}")
            raise

    def build_configuration_document(self, environment: str) -> dict:
        """Build configuration document based on config.example.yml.
        
        Note: In the new context architecture (v2), CORE_IDENTITY is defined
        directly in code (nexus/services/context/prompts.py). The config only
        contains runtime settings and the friends_profile field for user personalization.
        """
        print("\nStarting to build configuration document...")
        print("-" * 60)
        
        # Load configuration template from YAML file
        config_template = self.load_config_template()
        
        # Display what sections are being loaded
        print("✓ Configuration template contains the following sections:")
        for section_name in config_template.keys():
            if section_name != 'environment':
                section_data = config_template[section_name]
                if isinstance(section_data, dict):
                    print(f"  • {section_name}: {len(section_data)} items")
                else:
                    print(f"  • {section_name}: {type(section_data).__name__}")
        
        # Add environment identifier
        config_template["environment"] = environment
        
        print(f"\n✓ Configuration document build completed (environment: {environment})")
        print("Note: CORE_IDENTITY is now defined in code (nexus/services/context/prompts.py)")
        print("      Config only contains runtime settings and friends_profile.\n")
        return config_template

    def _display_configuration_summary(self, stored_config: dict) -> None:
        """Display a dynamic summary of the stored configuration."""
        print("\nVerification results:")
        print("-" * 60)
        print(f"  ✓ Environment: {stored_config.get('environment', 'unknown')}")
        
        # Display all top-level sections dynamically
        for section_name, section_data in stored_config.items():
            if section_name == 'environment':
                continue  # Already displayed above
                
            if section_name == 'llm':
                # Special handling for LLM section
                llm_config = section_data
                if isinstance(llm_config, dict):
                    catalog = llm_config.get('catalog', {})
                    providers = llm_config.get('providers', {})
                    print(f"  ✓ LLM Catalog: {len(catalog)} models")
                    print(f"  ✓ LLM Providers: {len(providers)} providers")
                    
                    # Show model details
                    for model_key, model_config in catalog.items():
                        if isinstance(model_config, dict):
                            aliases = model_config.get('aliases', [])
                            print(f"    • {model_key}: {', '.join(aliases) if aliases else 'No aliases'}")
            
            elif section_name == 'user_defaults':
                # Special handling for user_defaults section
                user_defaults = section_data
                if isinstance(user_defaults, dict):
                    print(f"  ✓ User Defaults:")
                    
                    for subsection_name, subsection_data in user_defaults.items():
                        if subsection_name == 'config':
                            if isinstance(subsection_data, dict):
                                print(f"    - config: {len(subsection_data)} items")
                                for key, value in subsection_data.items():
                                    print(f"      • {key}: {value}")
                        elif subsection_name == 'prompts':
                            if isinstance(subsection_data, dict):
                                print(f"    - prompts: {len(subsection_data)} modules")
                                for key, prompt_obj in subsection_data.items():
                                    if isinstance(prompt_obj, dict):
                                        content_len = len(prompt_obj.get('content', ''))
                                        editable = prompt_obj.get('editable', False)
                                        description = prompt_obj.get('description', '')
                                        print(f"      • {key}: {content_len} characters (editable={editable})")
                                        if description:
                                            print(f"        Description: {description}")
                        else:
                            if isinstance(subsection_data, dict):
                                print(f"    - {subsection_name}: {len(subsection_data)} items")
                            else:
                                print(f"    - {subsection_name}: {subsection_data}")
            
            elif section_name == 'ui':
                # Special handling for UI section
                ui_config = section_data
                if isinstance(ui_config, dict):
                    print(f"  ✓ UI Configuration:")
                    for key, value in ui_config.items():
                        if isinstance(value, list):
                            print(f"    - {key}: {len(value)} items")
                        elif isinstance(value, dict):
                            print(f"    - {key}: {len(value)} items")
                        else:
                            print(f"    - {key}: {value}")
            
            elif isinstance(section_data, dict):
                # Generic handling for other dictionary sections
                print(f"  ✓ {section_name}: {len(section_data)} items")
                # Show first few keys as examples
                keys = list(section_data.keys())[:3]
                for key in keys:
                    value = section_data[key]
                    if isinstance(value, (str, int, float, bool)):
                        print(f"    • {key}: {value}")
                    else:
                        print(f"    • {key}: {type(value).__name__}")
                if len(section_data) > 3:
                    print(f"    ... and {len(section_data) - 3} more items")
            
            else:
                # Simple values
                print(f"  ✓ {section_name}: {section_data}")
        
        # Special note about CORE_IDENTITY if prompts section exists
        if 'user_defaults' in stored_config and isinstance(stored_config['user_defaults'], dict):
            prompts = stored_config['user_defaults'].get('prompts', {})
            if isinstance(prompts, dict) and 'friends_profile' in prompts:
                print("\n  ℹ️  Note: CORE_IDENTITY is defined in code, not in config")
        
        print("-" * 60)
        print("\n✓ Initialization completed!")
        print(f"{'='*60}\n")

    def init_configurations(self, options: InitConfigOptions) -> bool:
        """Initialize configurations collection."""
        print(f"\n{'='*60}")
        print(f"NEXUS Configuration Initialization")
        print(f"Target Environment: {options.environment}")
        print(f"{'='*60}\n")
        
        if not self.client:
            logger.error("No database connection available")
            print("✗ Error: No database connection available")
            return False
        
        # Map environment to database name
        env_to_db = {
            'development': 'NEXUS_DB_DEV',
            'production': 'NEXUS_DB_PROD'
        }
        
        target_db = env_to_db.get(options.environment)
        if not target_db:
            logger.error(f"Unknown environment: {options.environment}")
            print(f"✗ Error: Unknown environment: {options.environment}")
            return False
        
        # Switch to target database if different from current
        if self.current_db != target_db:
            print(f"Switching to target database: {target_db}")
            if not self.switch_database(target_db):
                logger.error(f"Failed to switch to database: {target_db}")
                print(f"✗ Error: Unable to switch to database: {target_db}")
                return False
        
        print(f"Target Database: {self.current_db}")
        
        # Build configuration document (no longer reads prompt files)
        config_doc = self.build_configuration_document(options.environment)
        
        # Write to database (idempotent operation)
        try:
            print(f"\n{'='*60}")
            print("Starting to write to database...")
            print("-" * 60)
            
            database = self.client[self.current_db]
            configurations_collection = database['configurations']
            
            result = configurations_collection.replace_one(
                {"environment": options.environment},
                config_doc,
                upsert=True
            )
            
            if result.upserted_id:
                print(f"✓ Created new configuration document")
                print(f"  Document ID: {result.upserted_id}")
            else:
                print(f"✓ Updated existing configuration document")
                print(f"  Matched documents: {result.matched_count}")
                print(f"  Modified documents: {result.modified_count}")
            
            print("-" * 60)
            
            # Verify write
            stored_config = configurations_collection.find_one({"environment": options.environment})
            if stored_config:
                self._display_configuration_summary(stored_config)
            else:
                print("✗ Warning: Unable to verify written document")
            
            return True
            
        except Exception as e:
            logger.error(f"Error writing to database: {e}")
            print(f"✗ Failed to write to database: {e}")
            import traceback
            traceback.print_exc()
            return False

    def __del__(self):
        """Cleanup database connection."""
        if self.provider:
            try:
                self.provider.disconnect()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")


class InteractiveInterface:
    """Interactive command-line interface."""

    def __init__(self, manager: DatabaseManager):
        self.manager = manager

    def show_menu(self) -> None:
        """Show the main menu."""
        print("\n" + "="*50)
        print("NEXUS Database Manager")
        print("="*50)
        print(f"Current Database: {self.manager.current_db}")
        print("="*50)
        print("1. List databases")
        print("2. List collections")
        print("3. Show database statistics")
        print("4. Select database")
        print("5. Cleanup collection")
        print("6. Export collection")
        print("7. Analyze collection")
        print("8. Initialize configurations")
        print("9. Exit")
        print("="*50)

    def list_databases_interactive(self) -> None:
        """List databases interactively."""
        databases = self.manager.list_databases()
        print(f"\nAvailable databases ({len(databases)}):")
        for i, db in enumerate(databases, 1):
            print(f"{i}. {db}")

    def list_collections_interactive(self) -> None:
        """List collections interactively."""
        collections = self.manager.list_collections()
        print(f"\nCollections in '{self.manager.current_db}' ({len(collections)}):")
        for i, collection in enumerate(collections, 1):
            stats = self.manager.get_collection_stats(collection)
            count = stats.get('document_count', 0)
            print(f"{i}. {collection} ({count} documents)")

    def show_stats_interactive(self) -> None:
        """Show database statistics interactively."""
        stats = self.manager.get_database_stats()
        print(f"\n=== Database Statistics ===")
        print(f"Database: {stats['database_name']}")
        print(f"Total documents: {stats['total_documents']}")
        print(f"Total storage: {stats['total_storage']} bytes")
        print(f"\nCollections:")
        for collection, coll_stats in stats['collection_stats'].items():
            print(f"  {collection}: {coll_stats['document_count']} documents")

    def select_database_interactive(self) -> None:
        """Select database interactively."""
        databases = self.manager.list_databases()
        print(f"\nAvailable databases:")
        for i, db in enumerate(databases, 1):
            print(f"{i}. {db}")

        try:
            choice = int(input("\nSelect database (number): ")) - 1
            if 0 <= choice < len(databases):
                selected_db = databases[choice]
                if self.manager.switch_database(selected_db):
                    print(f"Switched to database: {selected_db}")
                else:
                    print("Failed to switch database.")
            else:
                print("Invalid choice.")
        except ValueError:
            print("Invalid input.")

    def cleanup_interactive(self) -> None:
        """Interactive cleanup."""
        collections = self.manager.list_collections()
        print(f"\nAvailable collections:")
        for i, collection in enumerate(collections, 1):
            stats = self.manager.get_collection_stats(collection)
            count = stats.get('document_count', 0)
            print(f"{i}. {collection} ({count} documents)")

        try:
            choice = int(input("\nSelect collection to clean (number): ")) - 1
            if 0 <= choice < len(collections):
                collection = collections[choice]

                count = int(input("Number of documents to delete: ") or "100")
                days = input("Delete documents older than how many days? (leave empty for no limit): ")
                role = input("Filter by role (HUMAN/AI/SYSTEM/TOOL)? (leave empty for no filter): ")

                options = CleanupOptions(
                    collection=collection,
                    count=count,
                    days=int(days) if days else None,
                    role=role if role else None,
                    dry_run=True
                )

                # Preview first
                print("\n=== Preview ===")
                self.manager.cleanup_collection(options)

                confirm = input("\nProceed with actual deletion? (yes/no): ").lower().strip()
                if confirm in ['yes', 'y']:
                    options.dry_run = False
                    self.manager.cleanup_collection(options)
                else:
                    print("Cleanup cancelled.")
            else:
                print("Invalid choice.")
        except ValueError:
            print("Invalid input.")

    def init_config_interactive(self) -> None:
        """Interactive configuration initialization."""
        print("\n=== Initialize Configurations ===")
        print("This will create/update the configurations collection with system prompts.")
        print("\nAvailable environments:")
        print("1. development")
        print("2. production")
        
        try:
            choice = input("\nSelect environment (1-2, default: 1): ").strip() or "1"
            environment = "development" if choice == "1" else "production"
            
            confirm = input(f"\nInitialize configurations for '{environment}'? (yes/no): ").lower().strip()
            if confirm in ['yes', 'y']:
                options = InitConfigOptions(environment=environment)
                success = self.manager.init_configurations(options)
                if not success:
                    print("Configuration initialization failed.")
            else:
                print("Operation cancelled.")
        except Exception as e:
            print(f"Error: {e}")

    def run(self) -> None:
        """Run the interactive interface."""
        while True:
            self.show_menu()

            try:
                choice = input("\nSelect option (1-9): ").strip()

                if choice == '1':
                    self.list_databases_interactive()
                elif choice == '2':
                    self.list_collections_interactive()
                elif choice == '3':
                    self.show_stats_interactive()
                elif choice == '4':
                    self.select_database_interactive()
                elif choice == '5':
                    self.cleanup_interactive()
                elif choice == '6':
                    print("Export functionality not implemented in interactive mode.")
                elif choice == '7':
                    print("Analyze functionality not implemented in interactive mode.")
                elif choice == '8':
                    self.init_config_interactive()
                elif choice == '9':
                    print("Goodbye!")
                    break
                else:
                    print("Invalid choice. Please select 1-9.")

                input("\nPress Enter to continue...")

            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                logger.error(f"Error in interactive mode: {e}")
                print(f"Error: {e}")
                input("\nPress Enter to continue...")


def load_config() -> DatabaseConfig:
    """Load database configuration from .env file."""
    try:
        # Load .env file if it exists
        env_file = os.path.join(os.path.dirname(__file__), '..', '.env')
        if os.path.exists(env_file):
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
            except ImportError:
                print("Warning: python-dotenv not available, skipping .env file loading")

        # Get configuration from environment variables
        mongo_uri = os.getenv('MONGO_URI')
        db_name = os.getenv('DATABASE_NAME', 'NEXUS_DB_DEV')

        if not mongo_uri:
            # Provide clear error message
            print("Error: MONGO_URI not found in configuration")
            print("Please set MONGO_URI in your .env file or environment variables")
            print("Example .env file content:")
            print("MONGO_URI=mongodb://localhost:27017")
            print("DATABASE_NAME=NEXUS_DB_DEV")
            sys.exit(1)

        return DatabaseConfig(
            mongo_uri=mongo_uri,
            database_name=db_name
        )
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="NEXUS Database Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/database_manager.py --interactive
  python scripts/database_manager.py --list-dbs
  python scripts/database_manager.py --stats
  python scripts/database_manager.py --cleanup --collection messages --days 30
  python scripts/database_manager.py --export --collection messages --output data.json
  python scripts/database_manager.py --init-config --environment development
        """
    )

    # Mode selection
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Run in interactive mode'
    )

    parser.add_argument(
        '--list-dbs',
        action='store_true',
        help='List all databases'
    )

    parser.add_argument(
        '--list-collections',
        action='store_true',
        help='List collections in current database'
    )

    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show database statistics'
    )

    # Cleanup options
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Run cleanup operation'
    )

    parser.add_argument(
        '--collection',
        type=str,
        help='Collection to operate on'
    )

    parser.add_argument(
        '--count',
        type=int,
        default=100,
        help='Number of documents to delete'
    )

    parser.add_argument(
        '--days',
        type=int,
        help='Delete documents older than this many days'
    )

    parser.add_argument(
        '--role',
        type=str,
        choices=['HUMAN', 'AI', 'SYSTEM', 'TOOL'],
        help='Filter by role'
    )

    parser.add_argument(
        '--session-id',
        type=str,
        help='Filter by session ID'
    )

    parser.add_argument(
        '--newest',
        action='store_true',
        help='Delete newest documents first'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually doing it'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompts'
    )

    # Export options
    parser.add_argument(
        '--export',
        action='store_true',
        help='Export collection data'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='Output file for export'
    )

    parser.add_argument(
        '--format',
        type=str,
        choices=['json', 'csv'],
        default='json',
        help='Export format'
    )

    # Configuration initialization options
    parser.add_argument(
        '--init-config',
        action='store_true',
        help='Initialize configurations collection'
    )

    parser.add_argument(
        '--environment',
        type=str,
        choices=['development', 'production'],
        default='development',
        help='Target environment for configuration initialization'
    )

    # Database selection
    parser.add_argument(
        '--database',
        type=str,
        help='Database to connect to'
    )

    args = parser.parse_args()

    try:
        # Load configuration
        config = load_config()

        # Override database if specified
        if args.database:
            config.database_name = args.database

        # Initialize manager
        manager = DatabaseManager(config)

        # Determine operation mode
        if args.interactive or len(sys.argv) == 1:
            # Default to interactive mode
            interface = InteractiveInterface(manager)
            interface.run()

        elif args.list_dbs:
            databases = manager.list_databases()
            print("Available databases:")
            for db in databases:
                print(f"  {db}")

        elif args.list_collections:
            collections = manager.list_collections()
            print(f"Collections in '{config.database_name}':")
            for collection in collections:
                stats = manager.get_collection_stats(collection)
                count = stats.get('document_count', 0)
                print(f"  {collection} ({count} documents)")

        elif args.stats:
            stats = manager.get_database_stats()
            print(f"Database: {stats['database_name']}")
            print(f"Total documents: {stats['total_documents']}")
            print(f"Total storage: {stats['total_storage']} bytes")
            print(f"\nCollections:")
            for collection, coll_stats in stats['collection_stats'].items():
                print(f"  {collection}: {coll_stats['document_count']} documents")

        elif args.cleanup:
            if not args.collection:
                print("Error: --collection is required for cleanup")
                sys.exit(1)

            options = CleanupOptions(
                collection=args.collection,
                count=args.count,
                days=args.days,
                role=args.role,
                session_id=args.session_id,
                newest_first=args.newest,
                dry_run=args.dry_run,
                force=args.force
            )

            success = manager.cleanup_collection(options)
            sys.exit(0 if success else 1)

        elif args.export:
            if not args.collection or not args.output:
                print("Error: --collection and --output are required for export")
                sys.exit(1)

            options = ExportOptions(
                collection=args.collection,
                output_file=args.output,
                format=args.format
            )

            success = manager.export_collection(options)
            sys.exit(0 if success else 1)

        elif args.init_config:
            options = InitConfigOptions(
                environment=args.environment,
                force=args.force
            )

            success = manager.init_configurations(options)
            sys.exit(0 if success else 1)

        else:
            print("No valid command specified. Use --help for usage information.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nOperation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()