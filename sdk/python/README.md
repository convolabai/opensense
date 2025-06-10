# LangHook Python SDK

A Python client library for connecting to LangHook servers.

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
import asyncio
from sdk.python import LangHookClient, LangHookClientConfig, AuthConfig

async def main():
    # Create client configuration
    config = LangHookClientConfig(
        endpoint="http://localhost:8000",
        auth=AuthConfig(type="token", value="your-auth-token")
    )
    
    # Use client as context manager
    async with LangHookClient(config) as client:
        # Create a subscription
        subscription = await client.create_subscription(
            "Notify me when PR 1374 is approved"
        )
        
        # Set up event listener
        def event_handler(event):
            print(f"Got event: {event.publisher}/{event.action}")
        
        # Start listening for events
        stop_listening = client.listen(
            str(subscription.id), 
            event_handler, 
            {"intervalSeconds": 15}
        )
        
        # ... do other work ...
        
        # Stop listening
        stop_listening()
        
        # Clean up
        await client.delete_subscription(str(subscription.id))

asyncio.run(main())
```

## API Reference

### LangHookClient

#### Constructor
- `LangHookClient(config: LangHookClientConfig)`

#### Methods
- `async init() -> None` - Validate connection and authentication
- `async list_subscriptions() -> List[Subscription]` - List all subscriptions
- `async create_subscription(nl_sentence: str) -> Subscription` - Create subscription from natural language
- `async delete_subscription(subscription_id: str) -> None` - Delete a subscription
- `listen(subscription_id: str, handler: Callable, options: Dict) -> Callable` - Listen for events via polling
- `async test_subscription(subscription_id: str, mock_event: CanonicalEvent) -> MatchResult` - Test subscription
- `async ingest_raw_event(publisher: str, payload: Dict) -> IngestResult` - Ingest raw event

### Configuration

```python
from sdk.python import LangHookClientConfig, AuthConfig

# Token authentication
config = LangHookClientConfig(
    endpoint="https://api.langhook.dev",
    auth=AuthConfig(type="token", value="sk-1234")
)

# Basic authentication  
config = LangHookClientConfig(
    endpoint="https://api.langhook.dev",
    auth=AuthConfig(type="basic", value="username:password")
)

# No authentication
config = LangHookClientConfig(endpoint="http://localhost:8000")
```

## Testing

```bash
python -m pytest sdk/python/tests/ -v
```

## Example

See `example.py` for a complete usage example.