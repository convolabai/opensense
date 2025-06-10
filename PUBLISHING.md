# LangHook Package Publishing Setup

This document summarizes the package publishing setup implemented for LangHook.

## Requirements (from Issue #113)

The issue requested:
1. Refactor server components into a `/server` folder
2. Split pyproject.toml between server and client
3. Publish as `langhook` (SDK) and `langhook[server]` (with server components)
4. Continue to publish `/sdk/typescript` as npm `langhook`

## Implementation

### Python Package Structure

**Root Package (`langhook`)**: SDK-only
- **Location**: `/` (root directory)
- **Structure**: Contains only the Python SDK components
- **Dependencies**: `httpx`, `pydantic`
- **Exports**: `LangHookClient`, `LangHookClientConfig`, etc.

**Server Package**: Server components
- **Location**: `/server/` directory  
- **Structure**: Contains all server components including:
  - `/server/langhook/` - Server application modules
  - `/server/tests/` - Server tests
  - `/server/frontend/` - Web interface
  - `/server/schemas/` - JSON schemas
  - `/server/mappings/` - Data mappings
  - `/server/prompts/` - LLM prompts
- **Dependencies**: Includes SDK dependencies plus FastAPI, uvicorn, etc.

**Server Extra**: `pip install langhook[server]`
- Installs SDK + server dependencies
- Allows running server via `langhook` command

### TypeScript Package (`langhook`)

**Location**: `/sdk/typescript/`

**Structure**:
- Package name: `langhook` 
- Exports TypeScript/JavaScript SDK for LangHook
- Built with TypeScript, outputs to `dist/`

**Usage**:
```bash
npm install langhook
```

```typescript
import { LangHookClient, LangHookClientConfig } from 'langhook';
```

## Build and Publishing

### Build Scripts

- **`scripts/build-packages.sh`**: Builds all packages (SDK, server, TypeScript)
- **`scripts/test-packages.py`**: Verifies package functionality

### Publishing Commands

**Python SDK Package**:
```bash
cd /path/to/langhook
python -m build --wheel
twine upload dist/*
```

**Python Server Package**:
```bash
cd /path/to/langhook/server
python -m build --wheel
twine upload dist/*
```

**TypeScript Package**:
```bash
cd /path/to/langhook/sdk/typescript
npm publish
```

## Package Structure Summary

1. **SDK Package** (`/`):
   - Name: `langhook`
   - Contains: Python SDK only
   - Usage: `pip install langhook`

2. **Server Extra** (root with `[server]`):
   - Name: `langhook[server]`
   - Contains: SDK + server dependencies
   - Usage: `pip install langhook[server]`

3. **TypeScript Package** (`/sdk/typescript/`):
   - Name: `langhook` (npm)
   - Contains: TypeScript/JavaScript SDK
   - Usage: `npm install langhook`

## Usage Examples

**SDK Only**:
```python
from langhook import LangHookClient, LangHookClientConfig
```

**Server (when installed with [server] extra)**:
```python
from server.langhook.main import main  # Server entry point
# or run via command line:
# langhook
```

## Verification

All requirements have been verified:
- ✅ Python SDK available as base `langhook` package
- ✅ Server functionality available as `langhook[server]`
- ✅ Server components properly isolated in `/server` directory
- ✅ Separate pyproject.toml files for SDK and server
- ✅ TypeScript SDK available as npm `langhook`
- ✅ All packages build successfully
- ✅ All functionality imports and works correctly