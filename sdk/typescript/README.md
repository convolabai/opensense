# LangHook TypeScript SDK

A TypeScript/JavaScript client library for connecting to LangHook servers.

## Installation

```bash
npm install
```

## Quick Start

```typescript
import { LangHookClient, LangHookClientConfig } from 'langhook-sdk';

async function main() {
  // Create client configuration
  const config: LangHookClientConfig = {
    endpoint: 'http://localhost:8000',
    auth: {
      type: 'token',
      value: 'your-auth-token'
    }
  };
  
  // Create client
  const client = new LangHookClient(config);
  
  // Initialize connection
  await client.init();
  
  // Create a subscription
  const subscription = await client.createSubscription(
    'Notify me when PR 1374 is approved'
  );
  
  // Set up event listener
  const eventHandler = (event) => {
    console.log(`Got event: ${event.publisher}/${event.action}`);
  };
  
  // Start listening for events
  const stopListening = client.listen(
    subscription.id.toString(),
    eventHandler,
    { intervalSeconds: 15 }
  );
  
  // ... do other work ...
  
  // Stop listening
  stopListening();
  
  // Clean up
  await client.deleteSubscription(subscription.id.toString());
}

main().catch(console.error);
```

## API Reference

### LangHookClient

#### Constructor
- `new LangHookClient(config: LangHookClientConfig)`

#### Methods
- `async init(): Promise<void>` - Validate connection and authentication
- `async listSubscriptions(): Promise<Subscription[]>` - List all subscriptions
- `async createSubscription(nlSentence: string): Promise<Subscription>` - Create subscription from natural language
- `async deleteSubscription(subscriptionId: string): Promise<void>` - Delete a subscription
- `listen(subscriptionId: string, handler: Function, options?: ListenOptions): () => void` - Listen for events via polling
- `async testSubscription(subscriptionId: string, mockEvent: CanonicalEvent): Promise<MatchResult>` - Test subscription
- `async ingestRawEvent(publisher: string, payload: Record<string, any>): Promise<IngestResult>` - Ingest raw event

### Configuration

```typescript
import { LangHookClientConfig } from 'langhook-sdk';

// Token authentication
const config: LangHookClientConfig = {
  endpoint: 'https://api.langhook.dev',
  auth: {
    type: 'token',
    value: 'sk-1234'
  }
};

// Basic authentication  
const config: LangHookClientConfig = {
  endpoint: 'https://api.langhook.dev',
  auth: {
    type: 'basic',
    value: 'username:password'
  }
};

// No authentication
const config: LangHookClientConfig = {
  endpoint: 'http://localhost:8000'
};
```

## Building

```bash
npm run build
```

## Testing

```bash
npm test
```

## Example

See `example.ts` for a complete usage example.