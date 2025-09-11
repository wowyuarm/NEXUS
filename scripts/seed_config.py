#!/usr/bin/env python3
"""
NEXUS Configuration Seeding Script

This script seeds the MongoDB database with initial configuration data
for development and production environments.

Usage:
    python scripts/seed_config.py [--env development|production|all] [--file config_file.yml] [--keep-api-keys]

Arguments:
    --env: Target environment(s) to seed (default: all)
    --file: YAML configuration file to use (default: config.example.yml)
    --keep-api-keys: Keep API keys as placeholders (e.g., ${GEMINI_API_KEY}) while substituting other environment variables
    --no-substitute: Keep all environment variable placeholders instead of substituting them

Examples:
    python scripts/seed_config.py
    python scripts/seed_config.py --env development
    python scripts/seed_config.py --env production
    python scripts/seed_config.py --keep-api-keys
    python scripts/seed_config.py --env all --file custom_config.yml
"""

import os
import sys
import argparse
import yaml
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from dotenv import load_dotenv

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_config_file(file_path: str) -> dict:
    """Load configuration from YAML file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print(f"✓ Configuration loaded from {file_path}")
        return config or {}
    except FileNotFoundError:
        print(f"✗ Configuration file not found: {file_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"✗ Error parsing YAML file: {e}")
        sys.exit(1)

def substitute_env_vars(config: dict, keep_api_keys: bool = False) -> dict:
    """Substitute environment variables in configuration."""
    def substitute_recursive(obj):
        if isinstance(obj, dict):
            return {k: substitute_recursive(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [substitute_recursive(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
            var_name = obj[2:-1]
            # Keep API keys as placeholders if requested
            if keep_api_keys and var_name.endswith('_API_KEY'):
                return obj
            return os.getenv(var_name, obj)
        else:
            return obj
    
    return substitute_recursive(config)

def get_mongo_connection() -> MongoClient:
    """Get MongoDB connection using environment variables."""
    # Load environment variables from .env file
    load_dotenv()
    
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        print("✗ MONGO_URI environment variable not set")
        print("Please set MONGO_URI in your .env file or environment")
        sys.exit(1)
    
    try:
        client = MongoClient(mongo_uri)
        # Test connection
        client.admin.command('ping')
        print("✓ Connected to MongoDB successfully")
        return client
    except ConnectionFailure as e:
        print(f"✗ Failed to connect to MongoDB: {e}")
        sys.exit(1)

def create_environment_config(base_config: dict, environment: str) -> dict:
    """Create environment-specific configuration from base config."""
    config = base_config.copy()
    
    if environment == "development":
        # Development-specific settings
        config["system"]["log_level"] = "DEBUG"
        config["llm"]["providers"]["google"]["model"] = "gemini-2.5-flash"
        config["llm"]["temperature"] = 0.7
        config["database"]["db_name"] = "NEXUS_DB_DEV"
    elif environment == "production":
        # Production-specific settings
        config["system"]["log_level"] = "INFO"
        config["llm"]["providers"]["google"]["model"] = "gemini-2.5-flash"
        config["llm"]["temperature"] = 0.7
        config["database"]["db_name"] = "NEXUS_DB_PROD"
    
    return config

def seed_environment_config(client: MongoClient, environment: str, config_data: dict) -> bool:
    """Seed configuration for a specific environment."""
    # Create environment-specific configuration
    env_config = create_environment_config(config_data, environment)
    
    # Use environment-specific database name
    db_name = env_config["database"]["db_name"]
    database = client[db_name]
    config_collection = database.system_configurations
    
    try:
        # Create unique index on environment
        config_collection.create_index([("environment", 1)], unique=True)
        
        # Insert or update configuration
        result = config_collection.update_one(
            {"environment": environment},
            {"$set": {"config_data": env_config}},
            upsert=True
        )
        
        if result.upserted_id:
            print(f"✓ Configuration inserted for {environment} environment in {db_name} (ID: {result.upserted_id})")
        elif result.modified_count > 0:
            print(f"✓ Configuration updated for {environment} environment in {db_name}")
        else:
            print(f"✓ Configuration already exists for {environment} environment in {db_name}")
        
        return True
        
    except OperationFailure as e:
        print(f"✗ Failed to seed configuration for {environment}: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error seeding configuration for {environment}: {e}")
        return False

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Seed NEXUS configuration to MongoDB')
    parser.add_argument('--env', choices=['development', 'production', 'all'], 
                       default='all', help='Target environment(s) to seed')
    parser.add_argument('--file', default='config.example.yml',
                       help='YAML configuration file to use')
    parser.add_argument('--no-substitute', action='store_true',
                       help='Keep environment variable placeholders instead of substituting them')
    parser.add_argument('--keep-api-keys', action='store_true',
                       help='Keep API keys as placeholders (e.g., ${GEMINI_API_KEY}) while substituting other environment variables')
    
    args = parser.parse_args()
    
    print("NEXUS Configuration Seeding Script")
    print("=" * 40)
    
    # Check if configuration file exists
    if not os.path.exists(args.file):
        print(f"✗ Configuration file not found: {args.file}")
        print("Make sure you're running this script from the project root directory")
        sys.exit(1)
    
    # Load and process configuration
    config_data = load_config_file(args.file)
    
    # Only substitute environment variables if not explicitly disabled
    if not args.no_substitute:
        config_data = substitute_env_vars(config_data, keep_api_keys=args.keep_api_keys)
        if args.keep_api_keys:
            print("✓ Environment variables substituted (API keys kept as placeholders)")
        else:
            print("✓ Environment variables substituted")
    else:
        print("✓ Environment variable placeholders preserved")
    
    # Connect to MongoDB
    client = get_mongo_connection()
    
    try:
        # Seed configurations for requested environments
        environments = ['development', 'production'] if args.env == 'all' else [args.env]
        
        print(f"\nEnvironment-specific configurations:")
        for env in environments:
            env_config = create_environment_config(config_data, env)
            print(f"  - {env}: log_level={env_config['system']['log_level']}, model={env_config['llm']['providers']['google']['model']}, db={env_config['database']['db_name']}")
        
        success_count = 0
        for env in environments:
            print(f"\nSeeding configuration for {env} environment...")
            if seed_environment_config(client, env, config_data):
                success_count += 1
        
        print(f"\n" + "=" * 40)
        print(f"Seeding completed: {success_count}/{len(environments)} environments successful")
        
        if success_count == len(environments):
            print("✓ All configurations seeded successfully!")
        else:
            print("✗ Some configurations failed to seed")
            sys.exit(1)
            
    finally:
        client.close()
        print("✓ MongoDB connection closed")

if __name__ == "__main__":
    main()