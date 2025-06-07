#!/bin/bash
# Initialize LangHook NATS JetStream streams

set -e

# Default values
NATS_URL=${NATS_URL:-"nats://localhost:4222"}
WAIT_TIMEOUT=${WAIT_TIMEOUT:-30}

echo "🚀 Initializing LangHook NATS JetStream streams..."
echo "📡 Using NATS server: $NATS_URL"

# Wait for NATS to be ready
echo "⏳ Waiting for NATS to be ready..."
timeout $WAIT_TIMEOUT bash -c 'until python -c "
import asyncio
import nats

async def check():
    try:
        nc = await nats.connect(\"'$NATS_URL'\")
        js = nc.jetstream()
        await nc.close()
        print(\"NATS is ready\")
    except Exception as e:
        print(f\"NATS not ready: {e}\")
        exit(1)

asyncio.run(check())
"; do
  echo "  ⏳ NATS not ready yet, retrying..."
  sleep 2
done'

echo "✅ NATS is ready!"

# Create streams using the stream manager
echo "📝 Creating LangHook streams..."
python -m langhook.cli.stream_manager --url "$NATS_URL" create

echo "📋 Listing created streams..."
# Commenting out list operation temporarily due to API compatibility issues
# python -m langhook.cli.stream_manager --url "$NATS_URL" list
echo "ℹ️  Stream listing temporarily disabled - streams created successfully"

echo "🎉 LangHook streams initialized successfully!"