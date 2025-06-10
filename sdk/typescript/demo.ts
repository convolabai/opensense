import { LangHookClient, LangHookClientConfig, CanonicalEvent } from './src/client';

async function demoSdkUsage() {
  console.log('🚀 LangHook TypeScript SDK Demo');
  console.log('='.repeat(50));

  // Create client with the exact configuration from the issue
  const client = new LangHookClient({
    endpoint: 'http://localhost:8000', // Would be "https://api.langhook.dev" in production
    auth: {
      type: 'token',
      value: 'sk-1234' // Example token
    }
  });

  try {
    // Initialize connection (as specified in the issue)
    console.log('1. Initializing connection...');
    await client.init();
    console.log('   ✅ Connected to LangHook server');

    // Create subscription with the exact example from the issue
    console.log('\n2. Creating subscription...');
    const subscription = await client.createSubscription('Notify me when PR 1374 is approved');
    console.log(`   ✅ Created subscription: ${subscription.id}`);
    console.log(`   📝 Description: ${subscription.description}`);
    console.log(`   🎯 Pattern: ${subscription.pattern}`);

    // Demonstrate listen() method as specified
    console.log('\n3. Setting up event listener...');
    
    const eventHandler = (event: CanonicalEvent) => {
      console.log('   🎉 Got matching event!');
      console.log(`      Publisher: ${event.publisher}`);
      console.log(`      Resource: ${JSON.stringify(event.resource)}`);
      console.log(`      Action: ${event.action}`);
      console.log(`      Timestamp: ${event.timestamp}`);
    };

    // Start listening with 15 second intervals (as in the issue example)
    const stopListening = client.listen(
      subscription.id.toString(),
      eventHandler,
      { intervalSeconds: 15 }
    );
    console.log('   ✅ Started listening for events (15 second intervals)');

    // Demonstrate event ingestion
    console.log('\n4. Ingesting test event...');
    const ingestResult = await client.ingestRawEvent('github', {
      action: 'synchronize', // This would trigger the PR subscription
      pull_request: {
        number: 1374,
        title: 'Add new feature',
        state: 'open',
        user: { login: 'developer' }
      },
      repository: { name: 'test-repo' }
    });
    console.log(`   ✅ Ingested event: ${ingestResult.request_id}`);

    // Let it run briefly to show polling
    console.log('\n5. Monitoring for events (10 seconds)...');
    await new Promise(resolve => setTimeout(resolve, 10000));

    // Stop listening
    console.log('\n6. Stopping listener...');
    stopListening();
    console.log('   ✅ Stopped listening');

    // List all subscriptions
    console.log('\n7. Listing all subscriptions...');
    const subscriptions = await client.listSubscriptions();
    console.log(`   📋 Found ${subscriptions.length} subscription(s)`);
    for (const sub of subscriptions) {
      console.log(`      - ID: ${sub.id}, Description: ${sub.description}`);
    }

    // Test subscription functionality
    console.log('\n8. Testing subscription...');
    const testEvent: CanonicalEvent = {
      publisher: 'github',
      resource: { type: 'pull_request', id: 1374 },
      action: 'approved',
      timestamp: '2023-01-01T12:00:00Z',
      payload: { approved_by: 'reviewer' }
    };
    const testResult = await client.testSubscription(subscription.id.toString(), testEvent);
    console.log(`   ✅ Test result: ${testResult.matched} - ${testResult.reason}`);

    // Clean up
    console.log('\n9. Cleaning up...');
    await client.deleteSubscription(subscription.id.toString());
    console.log('   ✅ Deleted subscription');

    console.log('\n🎯 Demo completed successfully!');
    console.log('\nThe LangHook TypeScript SDK provides all the functionality specified in the issue:');
    console.log('✅ init() method for endpoint + optional auth');
    console.log('✅ createSubscription() with natural language');
    console.log('✅ listSubscriptions() to get all subscriptions');
    console.log('✅ deleteSubscription() for cleanup');
    console.log('✅ listen() for polling-based event listening');
    console.log('✅ testSubscription() for testing subscriptions');
    console.log('✅ ingestRawEvent() for event ingestion');

  } catch (error) {
    console.log(`❌ Error: ${error}`);
    console.log('\nNote: This demo requires a running LangHook server.');
    console.log('To run a real demo, start the LangHook server with: langhook');
  }
}

// Run the demo
if (require.main === module) {
  demoSdkUsage().catch(console.error);
}

export { demoSdkUsage };