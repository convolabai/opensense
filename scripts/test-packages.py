#!/usr/bin/env python3
"""
Test script to verify the LangHook package structure meets the requirements.
"""

import subprocess
import sys
import tempfile
import os


def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return result


def test_base_sdk_installation():
    """Test that base SDK can be installed and used."""
    print("Testing base SDK installation...")
    
    # Test importing SDK components
    result = run_command('python -c "import langhook; print(langhook.__version__); client = langhook.LangHookClient"')
    if result.returncode == 0:
        print("✓ Base SDK import successful")
        print(f"  Version: {result.stdout.strip()}")
    else:
        print(f"✗ Base SDK import failed: {result.stderr}")
        return False
    
    return True


def test_server_installation():
    """Test that server components are available with [server] extra."""
    print("Testing server components...")
    
    # Test that server modules can be imported
    result = run_command('python -c "from langhook.main import main; print(\'Server components available\')"')
    if result.returncode == 0:
        print("✓ Server components accessible")
    else:
        print(f"✗ Server components failed: {result.stderr}")
        return False
    
    return True


def test_typescript_build():
    """Test that TypeScript SDK can be built."""
    print("Testing TypeScript SDK build...")
    
    # Check if TypeScript package builds
    result = run_command('npm run build', cwd='sdk/typescript')
    if result.returncode == 0:
        print("✓ TypeScript SDK builds successfully")
    else:
        print(f"✗ TypeScript SDK build failed: {result.stderr}")
        return False
    
    return True


def main():
    """Run all tests."""
    print("LangHook Package Structure Verification")
    print("=" * 40)
    
    tests = [
        test_base_sdk_installation,
        test_server_installation, 
        test_typescript_build,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            print()
    
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All package requirements met!")
        return 0
    else:
        print("✗ Some requirements not met")
        return 1


if __name__ == "__main__":
    sys.exit(main())