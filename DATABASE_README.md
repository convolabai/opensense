# Database Creation Script

This directory contains the database creation script for LangHook, which ensures all required tables are created on an empty PostgreSQL database.

## Files

- `database_creation.py` - Main database creation script
- `test_database_creation.py` - Unit tests for the database creation functionality
- `test_database_integration.py` - Integration tests to verify compatibility with existing code

## Usage

### Basic Usage

Create all tables in a PostgreSQL database:

```bash
python database_creation.py --postgres-dsn="postgresql://user:pass@localhost:5432/langhook"
```

### Dry Run

See what SQL would be executed without making changes:

```bash
python database_creation.py --dry-run
```

### Verbose Output

Enable verbose logging for troubleshooting:

```bash
python database_creation.py --verbose
```

## Features

### ✅ Idempotent Operations
- Uses `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`
- Safe to run multiple times without errors
- Checks for existing constraints before creating them

### ✅ Schema Versioning
- Creates `schema_migrations` table to track schema version
- Records version `1.0.0` on initial creation
- Supports future schema evolution

### ✅ Complete Table Creation
- **Core LangHook Tables:**
  - `subscriptions` - Natural language subscriptions
  - `event_schema_registry` - Dynamic schema tracking
  - `event_logs` - Canonical event logging
  - `subscription_event_logs` - Subscription-specific event logs
  - `ingest_mappings` - Payload mapping cache

- **Application Tables:**
  - `users` - User management
  - `projects` - Project organization
  - `snippets` - Code/configuration snippets
  - `responses` - API response tracking
  - `sessions` - User session management
  - `logs` - General application logging

### ✅ Performance Optimized
- Creates indexes on frequently queried columns
- Uses appropriate data types (JSONB for JSON data)
- Includes foreign key constraints for data integrity

## Testing

Run the unit tests:

```bash
python test_database_creation.py
```

Run integration tests:

```bash
python test_database_integration.py
```

## Database Schema

### Schema Migrations Table

```sql
CREATE TABLE schema_migrations (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    checksum VARCHAR(64)
);
```

This table tracks schema versions and supports future migrations.

### Example Output

The script provides clear output for both dry-run and actual execution:

```
[DRY RUN] Create subscriptions table:
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    subscriber_id VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    ...
);
------------------------------------------------------------
[DRY RUN] Create index: subscriptions_subscriber_id:
CREATE INDEX IF NOT EXISTS idx_subscriptions_subscriber_id ON subscriptions(subscriber_id);
```

## Error Handling

- Database connection errors are logged and cause immediate exit
- Individual table/index creation errors are logged but don't stop the entire process
- Foreign key constraint failures are logged as warnings (useful for databases with existing data)

## Integration with Existing Code

The script is fully compatible with the existing `DatabaseService` class in `langhook/subscriptions/database.py`. All tables created by this script match the models defined in `langhook/subscriptions/models.py`.