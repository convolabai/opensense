#!/bin/bash
# Build script for all LangHook packages

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Building LangHook packages..."

# Build SDK package
echo "Building SDK package (langhook)..."
cd "$ROOT_DIR"
python -m build --wheel

# Build server package
echo "Building server package (langhook[server])..."
cd "$ROOT_DIR/server"
python -m build --wheel

# Build TypeScript SDK
echo "Building TypeScript SDK..."
cd "$ROOT_DIR/sdk/typescript"
npm run build

echo "All packages built successfully!"
echo ""
echo "Packages ready for publishing:"
echo "1. Python SDK package: pip install langhook"
echo "2. Python server package: pip install langhook[server] (from root) or pip install server package directly"
echo "3. TypeScript package: npm install langhook"