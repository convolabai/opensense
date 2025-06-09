# Event Logging to PostgreSQL

This feature allows LangHook to optionally log all incoming events and their canonical transformation results to PostgreSQL for auditing, analytics, and debugging purposes.

## Configuration

The event logging feature is **disabled by default** and can be enabled using environment variables:

### Environment Variables

- `EVENT_LOGGING_ENABLED`: Set to `true` to enable event logging (default: `false`)
- `POSTGRES_DSN`: PostgreSQL connection string (shared with subscription service)
- `NATS_URL`: NATS server URL (shared with other services)
- `NATS_STREAM_EVENTS`: NATS events stream name (shared with other services)
- `NATS_CONSUMER_GROUP`: NATS consumer group name (shared with other services)

### Docker Compose

To enable event logging in the Docker Compose setup, update the environment variables:

```yaml
environment:
  - EVENT_LOGGING_ENABLED=true  # Enable event logging
  # ... other environment variables
```

### Environment File

You can also configure this in your `.env.subscriptions` file:

```bash
EVENT_LOGGING_ENABLED=true
POSTGRES_DSN=postgresql://langhook:langhook@localhost:5432/langhook
```

## Database Schema

When enabled, the service automatically creates an `event_logs` table with the following structure:

```sql
CREATE TABLE event_logs (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255) NOT NULL,        -- CloudEvent ID
    source VARCHAR(255) NOT NULL,          -- Event source (e.g., 'github', 'stripe')
    subject VARCHAR(255) NOT NULL,         -- NATS subject
    publisher VARCHAR(255) NOT NULL,       -- Canonical publisher
    resource_type VARCHAR(255) NOT NULL,   -- Canonical resource type
    resource_id VARCHAR(255) NOT NULL,     -- Canonical resource ID
    action VARCHAR(255) NOT NULL,          -- Canonical action
    canonical_data JSONB NOT NULL,         -- Full canonical event data
    raw_payload JSONB,                     -- Original raw payload (if available)
    timestamp TIMESTAMPTZ NOT NULL,        -- Event timestamp
    logged_at TIMESTAMPTZ NOT NULL DEFAULT NOW()  -- Log insertion time
);
```

Indexes are automatically created on frequently queried fields for optimal performance.

## How It Works

1. **Event Flow**: Raw events → Ingest → NATS → Map Service → Canonical Events → NATS
2. **Logging**: When enabled, a separate `EventLoggingService` consumes canonical events from NATS
3. **Storage**: Each canonical event is parsed and stored in the `event_logs` table
4. **Performance**: The logging runs asynchronously and doesn't block event processing

## Querying Event Logs

Once enabled, you can query the logged events directly from PostgreSQL:

```sql
-- Find all events from GitHub in the last hour
SELECT event_id, action, resource_type, timestamp 
FROM event_logs 
WHERE publisher = 'github' 
  AND timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;

-- Count events by publisher and action
SELECT publisher, action, COUNT(*) as event_count
FROM event_logs 
WHERE logged_at > NOW() - INTERVAL '1 day'
GROUP BY publisher, action
ORDER BY event_count DESC;

-- Find events for a specific resource
SELECT event_id, action, canonical_data
FROM event_logs 
WHERE publisher = 'github' 
  AND resource_type = 'pull_request' 
  AND resource_id = '123';
```

## Performance Considerations

- **Disk Space**: Each event is stored as JSONB, so monitor disk usage in high-volume environments
- **Database Performance**: The service uses connection pooling and indexes for efficient writes
- **Error Handling**: Database errors are logged but don't block event processing
- **Asynchronous**: Logging runs in a separate consumer and doesn't impact main event flow

## Monitoring

The event logging service provides structured logging for monitoring:

- Service start/stop events
- Successful event logging
- Database connection errors
- Invalid event data warnings

## Security

- Event data is stored as-is, including any sensitive information in payloads
- Consider database encryption and access controls for sensitive environments
- Raw payloads may contain authentication tokens or personal data

## Troubleshooting

### Service Not Starting

Check that:
1. `EVENT_LOGGING_ENABLED=true` is set
2. PostgreSQL connection is available
3. NATS connection is available
4. Database permissions allow table creation

### Events Not Being Logged

Verify:
1. The service started successfully (check logs)
2. Canonical events are being published to NATS
3. No database connection errors in logs
4. The `event_logs` table was created

### Performance Issues

Consider:
1. Database indexing strategy for your query patterns
2. Connection pool settings
3. Disk space and I/O capacity
4. Archiving old event logs