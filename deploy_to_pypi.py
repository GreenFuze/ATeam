#!/usr/bin/env python3
"""
Deploy script for publishing ateam to PyPI.

Usage:
    python deploy_to_pypi.py [--repository testpypi]

Environment variables:
    FLIT_USERNAME: PyPI username (default: __token__)
    FLIT_PASSWORD: PyPI API token
"""

import os
import subprocess
import sys
from pathlib import Path


def ensure(condition: bool, msg: str) -> None:
    """Ensure a condition is met, exit with error if not."""
    if not condition:
        print(f"ERROR: {msg}")
        sys.exit(1)


def main() -> None:
    """Main deployment function."""
    print("🚀 Starting ateam deployment...")
    
    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        ensure(False, "pyproject.toml not found. Run from project root.")
    
    # Check if flit is available
    try:
        import flit_core  # noqa
    except ImportError:
        ensure(False, "Flit not installed. Run: pip install flit")
    
    # Get repository from command line args
    repository = "pypi"  # default
    if "--repository" in sys.argv:
        idx = sys.argv.index("--repository")
        if idx + 1 < len(sys.argv):
            repository = sys.argv[idx + 1]
    
    # Validate repository
    if repository not in ["pypi", "testpypi"]:
        ensure(False, f"Invalid repository: {repository}. Use 'pypi' or 'testpypi'")
    
    # Get credentials
    username = os.getenv("FLIT_USERNAME", "__token__")
    password = os.getenv("FLIT_PASSWORD")
    
    ensure(password, "Set FLIT_PASSWORD environment variable to your PyPI API token")
    
    print(f"📦 Building package for {repository}...")
    
    # Build the package
    try:
        subprocess.run([sys.executable, "-m", "flit", "build"], 
                      check=True, capture_output=True, text=True)
        print("✅ Package built successfully")
    except subprocess.CalledProcessError as e:
        ensure(False, f"Build failed: {e.stderr}")
    
    # Verify wheel and metadata
    dist_dir = Path("dist")
    wheels = list(dist_dir.glob("*.whl"))
    sdists = list(dist_dir.glob("*.tar.gz"))
    
    ensure(wheels, "No wheel file found in dist/")
    ensure(sdists, "No source distribution found in dist/")
    
    print(f"📋 Found {len(wheels)} wheel(s) and {len(sdists)} source distribution(s)")
    
    # Show package info
    for wheel in wheels:
        print(f"   Wheel: {wheel.name}")
    for sdist in sdists:
        print(f"   Source: {sdist.name}")
    
    # Confirm before publishing
    if repository == "pypi":
        print("\n⚠️  WARNING: Publishing to PyPI (production)")
        confirm = input("Type 'publish' to confirm: ")
        ensure(confirm == "publish", "Publishing cancelled")
    else:
        print(f"\n📤 Publishing to {repository}...")
    
    # Publish
    try:
        cmd = [sys.executable, "-m", "flit", "publish"]
        if repository == "testpypi":
            cmd.extend(["--repository", "testpypi"])
        
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ Successfully published to {repository}")
        
    except subprocess.CalledProcessError as e:
        ensure(False, f"Publish failed: {e.stderr}")
    
    print(f"🎉 ateam successfully deployed to {repository}!")
    
    if repository == "testpypi":
        print("\nTo install from TestPyPI:")
        print("pip install --index-url https://test.pypi.org/simple/ ateam")
    else:
        print("\nTo install from PyPI:")
        print("pip install ateam")


if __name__ == "__main__":
    main()
