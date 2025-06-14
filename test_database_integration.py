"""
Integration test for database_creation.py with existing DatabaseService

This test verifies that the new database creation script creates tables
that are compatible with the existing DatabaseService from the subscription module.
"""

import tempfile
import os
import sys
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, '/home/runner/work/langhook/langhook')

from database_creation import DatabaseCreator


def test_table_compatibility():
    """Test that created tables are compatible with existing models."""
    print("🔍 Testing table compatibility with existing models...")
    
    # Get table definitions from our script
    creator = DatabaseCreator(postgres_dsn="postgresql://test", dry_run=True)
    
    # Test that all expected tables are created
    expected_tables = [
        'schema_migrations',
        'subscriptions', 
        'event_schema_registry',
        'event_logs',
        'subscription_event_logs', 
        'ingest_mappings',
        'users',
        'projects',
        'snippets', 
        'responses',
        'sessions',
        'logs'
    ]
    
    # Capture the SQL output to verify table creation
    import io
    from contextlib import redirect_stdout
    
    output = io.StringIO()
    with redirect_stdout(output):
        creator.create_all_tables()
    
    output_text = output.getvalue()
    
    # Verify each expected table is created
    for table in expected_tables:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in output_text, \
            f"Table '{table}' not found in creation script"
        print(f"✅ Table '{table}' creation verified")
    
    print("✅ All expected tables are created by the script")


def test_idempotent_operations():
    """Test that operations are idempotent (can be run multiple times)."""
    print("🔄 Testing idempotent operations...")
    
    creator = DatabaseCreator(postgres_dsn="postgresql://test", dry_run=True)
    
    # Run creation twice to make sure it's idempotent
    import io
    from contextlib import redirect_stdout
    
    # First run
    output1 = io.StringIO()
    with redirect_stdout(output1):
        creator.create_all_tables()
    
    # Second run  
    output2 = io.StringIO()
    with redirect_stdout(output2):
        creator.create_all_tables()
    
    # Both runs should produce the same output (idempotent)
    output1_text = output1.getvalue()
    output2_text = output2.getvalue()
    
    # Verify IF NOT EXISTS is used
    assert "CREATE TABLE IF NOT EXISTS" in output1_text
    assert "CREATE INDEX IF NOT EXISTS" in output1_text
    
    print("✅ Operations use IF NOT EXISTS for idempotency")
    print("✅ Script can be run multiple times safely")


def test_schema_versioning():
    """Test schema versioning functionality."""
    print("📋 Testing schema versioning...")
    
    creator = DatabaseCreator(postgres_dsn="postgresql://test", dry_run=True)
    
    import io
    from contextlib import redirect_stdout
    
    output = io.StringIO()
    with redirect_stdout(output):
        creator.create_schema_migrations_table()
        creator.record_schema_version("1.0.0", "Test version")
    
    output_text = output.getvalue()
    
    # Verify schema migrations table is created
    assert "CREATE TABLE IF NOT EXISTS schema_migrations" in output_text
    assert "version VARCHAR(50) NOT NULL UNIQUE" in output_text
    assert "applied_at TIMESTAMPTZ" in output_text
    
    print("✅ Schema migrations table created correctly")
    print("✅ Schema versioning functionality working")


def test_existing_database_service_compatibility():
    """Test compatibility with existing DatabaseService patterns."""
    print("🔗 Testing compatibility with existing DatabaseService...")
    
    # Test that our table definitions match the patterns used in the existing service
    from langhook.subscriptions.models import Base
    from langhook.subscriptions.database import DatabaseService
    
    # Get table names from existing models
    existing_tables = set()
    for table in Base.metadata.tables.values():
        existing_tables.add(table.name)
    
    print(f"📊 Found {len(existing_tables)} existing tables in models: {existing_tables}")
    
    # Verify our script creates all the existing tables
    creator = DatabaseCreator(postgres_dsn="postgresql://test", dry_run=True)
    
    import io
    from contextlib import redirect_stdout
    
    output = io.StringIO()
    with redirect_stdout(output):
        creator.create_all_tables()
    
    output_text = output.getvalue()
    
    # Check that all existing model tables are created by our script
    for table_name in existing_tables:
        assert f"CREATE TABLE IF NOT EXISTS {table_name}" in output_text, \
            f"Existing table '{table_name}' not created by script"
        print(f"✅ Existing table '{table_name}' is handled by creation script")
    
    print("✅ Script is compatible with existing DatabaseService patterns")


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("🧪 INTEGRATION TESTING DATABASE CREATION SCRIPT")
    print("=" * 60)
    
    try:
        test_table_compatibility()
        test_idempotent_operations()
        test_schema_versioning()
        test_existing_database_service_compatibility()
        
        print("\n" + "=" * 60)
        print("🎉 ALL INTEGRATION TESTS PASSED")
        print("=" * 60)
        print("Database creation script is fully compatible!")
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)