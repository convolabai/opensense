# LangHook Package Publishing Setup

This document summarizes the package publishing setup implemented for LangHook.

## Requirements (from Issue #107)

The issue requested:
1. publish /langhook folder as pip `langhook[server]`
2. publish /sdk/python folder as pip `langhook`  
3. publish /sdk/typescript as npm `langhook`

## Implementation

### Python Package (`langhook`)

**Location**: `/langhook/` (main directory)

**Structure**:
- **Base package**: `pip install langhook` 
  - Includes the Python SDK components
  - Dependencies: `httpx`, `pydantic`
  - Exports: `LangHookClient`, `LangHookClientConfig`, etc.

- **Server extra**: `pip install langhook[server]`
  - Includes all server dependencies
  - Additional deps: `fastapi`, `uvicorn`, `nats-py`, `redis`, `sqlalchemy`, etc.

**Usage**:
```python
# SDK only
from langhook import LangHookClient, LangHookClientConfig

# Server (when installed with [server] extra)
from langhook.main import main  # Server entry point
```

### TypeScript Package (`langhook`)

**Location**: `/sdk/typescript/`

**Structure**:
- Package name: `langhook` (changed from `langhook-sdk`)
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

- **`scripts/build-packages.sh`**: Builds all packages
- **`scripts/test-packages.py`**: Verifies package functionality

### Publishing Commands

**Python Package**:
```bash
cd /path/to/langhook
python -m build --wheel
twine upload dist/*
```

**TypeScript Package**:
```bash
cd /path/to/langhook/sdk/typescript
npm publish
```

## Package Structure Summary

1. **Main Python Package** (`/langhook/`):
   - Name: `langhook`
   - Base: SDK functionality
   - Extra `[server]`: Full server capabilities
   - Satisfies both Python requirements from the issue

2. **TypeScript Package** (`/sdk/typescript/`):
   - Name: `langhook` (npm)
   - Provides TypeScript/JavaScript SDK
   - Satisfies TypeScript requirement from the issue

## Verification

All requirements have been verified:
- ✅ Python SDK available as base `langhook` package
- ✅ Server functionality available as `langhook[server]`
- ✅ TypeScript SDK available as npm `langhook`
- ✅ All packages build successfully
- ✅ All functionality imports and works correctly