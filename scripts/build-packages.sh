#!/bin/bash
# Build script for all LangHook packages

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Building LangHook packages..."

# Build main package (SDK + server)
echo "Building main package (langhook with SDK and server)..."
cd "$ROOT_DIR"
python -m build --wheel

# Build TypeScript SDK
echo "Building TypeScript SDK..."
cd "$ROOT_DIR/sdk/typescript"
npm i && npm run build

echo "All packages built successfully!"
echo ""
echo "Packages ready for publishing:"
echo "1. Python package: pip install langhook (SDK) or pip install langhook[server] (full server)"
echo "2. TypeScript package: npm install langhook"