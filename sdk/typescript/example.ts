import { LangHookClient, LangHookClientConfig, AuthConfig } from './dist/index';

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

  try {
    // Initialize connection
    await client.init();
    console.log('✅ Connected to LangHook server');

    // Create a subscription
    const subscription = await client.createSubscription(
      'Notify me when PR 1374 is approved'
    );
    console.log(`✅ Created subscription: ${subscription.id}`);

    // List all subscriptions
    const subscriptions = await client.listSubscriptions();
    console.log(`📋 Found ${subscriptions.length} subscriptions`);

    // Set up event listener
    const eventHandler = (event: any) => {
      console.log(`🎉 Got matching event: ${event.publisher}/${event.action}`);
      console.log(`   Resource: ${JSON.stringify(event.resource)}`);
      console.log(`   Timestamp: ${event.timestamp}`);
    };

    // Start listening for events (with 15 second polling interval)
    const stopListening = client.listen(
      subscription.id.toString(),
      eventHandler,
      { intervalSeconds: 15 }
    );

    console.log('👂 Listening for events... (will run for 30 seconds)');

    // Let it run for a bit
    await new Promise(resolve => setTimeout(resolve, 30000));

    // Stop listening
    stopListening();
    console.log('⏹️  Stopped listening');

    // Ingest a test event
    const result = await client.ingestRawEvent('github', {
      action: 'opened',
      pull_request: {
        number: 1374,
        title: 'Test PR'
      }
    });
    console.log(`📤 Ingested event: ${result.request_id}`);

    // Clean up - delete the subscription
    await client.deleteSubscription(subscription.id.toString());
    console.log('🗑️  Deleted subscription');

  } catch (error) {
    console.error('Error:', error);
  }
}

// Run the example
if (require.main === module) {
  main().catch(console.error);
}

export { main };