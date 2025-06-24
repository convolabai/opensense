#!/bin/bash
# Build script for LangHook frontend with optional server path support
cd ./frontend
# Set the build path
export BUILD_PATH="../langhook/static"

# Configure PUBLIC_URL based on SERVER_PATH
if [ -n "$SERVER_PATH" ]; then
    # Remove trailing slash from SERVER_PATH if present and add /static
    SERVER_PATH_CLEAN="${SERVER_PATH%/}"
    export PUBLIC_URL="${SERVER_PATH_CLEAN}/"
    export REACT_APP_BASE_PATH="${SERVER_PATH_CLEAN}"
    echo "Building with SERVER_PATH: $SERVER_PATH"
    echo "PUBLIC_URL set to: $PUBLIC_URL"
    echo "REACT_APP_BASE_PATH set to: $REACT_APP_BASE_PATH"
else
    export PUBLIC_URL="/"
    export REACT_APP_BASE_PATH=""
    echo "Building with default PUBLIC_URL: $PUBLIC_URL"
    echo "REACT_APP_BASE_PATH set to: $REACT_APP_BASE_PATH"
fi

# Build the React app
npx react-scripts build

cd ..