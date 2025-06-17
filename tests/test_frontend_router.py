"""Test frontend router configuration with server path."""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


def test_frontend_router_basename_with_server_path():
    """Test that frontend router is configured with correct basename when SERVER_PATH is set."""
    frontend_dir = Path(__file__).parent.parent / "frontend"
    static_dir = Path(__file__).parent.parent / "langhook" / "static"
    
    # Build with SERVER_PATH
    env = os.environ.copy()
    env["SERVER_PATH"] = "/langhook"
    
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=frontend_dir,
        env=env,
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Build failed: {result.stderr}"
    
    # Check that the built JS contains the correct basename
    js_files = list((static_dir / "static" / "js").glob("main.*.js"))
    assert len(js_files) > 0, "No main JS file found"
    
    js_content = js_files[0].read_text()
    assert 'basename:"/langhook"' in js_content, "Router basename not configured correctly"


def test_frontend_router_basename_without_server_path():
    """Test that frontend router works correctly without SERVER_PATH."""
    frontend_dir = Path(__file__).parent.parent / "frontend"
    static_dir = Path(__file__).parent.parent / "langhook" / "static"
    
    # Build without SERVER_PATH
    env = os.environ.copy()
    env.pop("SERVER_PATH", None)
    
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=frontend_dir,
        env=env,
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Build failed: {result.stderr}"
    
    # Check that the built JS contains empty basename
    js_files = list((static_dir / "static" / "js").glob("main.*.js"))
    assert len(js_files) > 0, "No main JS file found"
    
    js_content = js_files[0].read_text()
    assert 'basename:""' in js_content, "Router basename should be empty for default build"


def test_frontend_build_script_sets_react_app_base_path():
    """Test that build script correctly sets REACT_APP_BASE_PATH environment variable."""
    frontend_dir = Path(__file__).parent.parent / "frontend"
    
    # Test with SERVER_PATH
    env = os.environ.copy()
    env["SERVER_PATH"] = "/test/path"
    
    result = subprocess.run(
        ["./build.sh"],
        cwd=frontend_dir,
        env=env,
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Build script failed: {result.stderr}"
    assert "REACT_APP_BASE_PATH set to: /test/path" in result.stdout
    
    # Test without SERVER_PATH
    env.pop("SERVER_PATH", None)
    
    result = subprocess.run(
        ["./build.sh"],
        cwd=frontend_dir,
        env=env,
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Build script failed: {result.stderr}"
    assert "REACT_APP_BASE_PATH set to:" in result.stdout