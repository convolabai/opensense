#!/bin/bash
# Build script for LangHook frontend with optional server path support

# Set the build path
export BUILD_PATH="../langhook/static"

# Configure PUBLIC_URL based on SERVER_PATH
if [ -n "$SERVER_PATH" ]; then
    # Remove trailing slash from SERVER_PATH if present and add /static
    SERVER_PATH_CLEAN="${SERVER_PATH%/}"
    export PUBLIC_URL="${SERVER_PATH_CLEAN}/static"
    echo "Building with SERVER_PATH: $SERVER_PATH"
    echo "PUBLIC_URL set to: $PUBLIC_URL"
else
    export PUBLIC_URL="/static"
    echo "Building with default PUBLIC_URL: $PUBLIC_URL"
fi

# Build the React app
react-scripts build