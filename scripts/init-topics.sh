#!/bin/bash
# Initialize OpenSense Kafka topics

set -e

# Default values
KAFKA_BROKERS=${KAFKA_BROKERS:-"localhost:19092"}
WAIT_TIMEOUT=${WAIT_TIMEOUT:-30}

echo "🚀 Initializing OpenSense Kafka topics..."
echo "📡 Using Kafka brokers: $KAFKA_BROKERS"

# Wait for Kafka to be ready
echo "⏳ Waiting for Kafka to be ready..."
timeout $WAIT_TIMEOUT bash -c 'until python -c "
import asyncio
from aiokafka import AIOKafkaProducer

async def check():
    producer = AIOKafkaProducer(bootstrap_servers=\"'$KAFKA_BROKERS'\".split(\",\"))
    try:
        await producer.start()
        await producer.stop()
        print(\"Kafka is ready\")
    except Exception as e:
        print(f\"Kafka not ready: {e}\")
        exit(1)

asyncio.run(check())
"; do
  echo "  ⏳ Kafka not ready yet, retrying..."
  sleep 2
done'

echo "✅ Kafka is ready!"

# Create topics using the topic manager
echo "📝 Creating OpenSense topics..."
python -m opensense.cli.topic_manager --brokers "$KAFKA_BROKERS" create

echo "📋 Listing created topics..."
python -m opensense.cli.topic_manager --brokers "$KAFKA_BROKERS" list

echo "🎉 OpenSense topics initialized successfully!"