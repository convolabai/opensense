# Server Path Configuration for Reverse Proxy Deployments

LangHook server supports deployment behind reverse proxies (like nginx) with path-based routing through the `SERVER_PATH` environment variable.

## Configuration

Set the `SERVER_PATH` environment variable to the path prefix where your LangHook server will be accessed:

```bash
# For serving at https://example.com/langhook/
export SERVER_PATH=/langhook

# Or in your .env file
SERVER_PATH=/langhook
```

## Frontend Build

When building the frontend with a custom server path, make sure to set the `SERVER_PATH` environment variable before building:

```bash
cd frontend
SERVER_PATH=/langhook npm run build
```

This ensures that all static asset references in the frontend (JavaScript, CSS, images) are correctly prefixed with the server path.

## Nginx Configuration Example

Here's an example nginx configuration for serving LangHook at a subpath:

**How it works:**
- Nginx receives requests at `/langhook/*` (e.g., `/langhook/health/`)
- The `proxy_pass` directive with trailing slash automatically strips the `/langhook` prefix
- FastAPI receives the request without the prefix (e.g., `/health/`)
- FastAPI's `root_path="/langhook"` tells it that its public base URL is `/langhook` for URL generation

```nginx
server {
    listen 80;
    server_name example.com;

    # Serve LangHook at /langhook
    location /langhook/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Testing

You can test the configuration by:

1. Setting the `SERVER_PATH` environment variable
2. Starting the server: `uvicorn langhook.app:app --host 0.0.0.0 --port 8000`
3. Accessing the API at `http://localhost:8000/langhook/health/`
4. Accessing the console at `http://localhost:8000/langhook/console`

## API Endpoints

All API endpoints automatically work with the configured server path:

- Health: `{SERVER_PATH}/health/`
- Ingest: `{SERVER_PATH}/ingest/{source}`  
- Console: `{SERVER_PATH}/console`
- Demo: `{SERVER_PATH}/demo`
- Docs: `{SERVER_PATH}/docs` (when debug enabled)

The server automatically handles URL routing and static asset serving for the configured path.