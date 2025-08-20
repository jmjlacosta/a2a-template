#!/usr/bin/env python3
"""
Check if all required dependencies are installed for running the orchestrator tests.
"""

import sys
import importlib
import subprocess
from pathlib import Path

REQUIRED_PACKAGES = [
    ("httpx", "httpx"),
    ("psutil", "psutil"),
    ("google.adk", "google-adk"),
    ("a2a", "a2a"),
    ("uvicorn", "uvicorn"),
    ("starlette", "starlette")
]

def check_package(import_name: str, package_name: str) -> bool:
    """Check if a package is installed."""
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        return False

def main():
    print("="*60)
    print("📦 CHECKING REQUIREMENTS")
    print("="*60)
    print()
    
    missing = []
    installed = []
    
    for import_name, package_name in REQUIRED_PACKAGES:
        if check_package(import_name.split('.')[0], package_name):
            installed.append(package_name)
            print(f"✅ {package_name:20} - Installed")
        else:
            missing.append(package_name)
            print(f"❌ {package_name:20} - Missing")
    
    print()
    print("="*60)
    print("📊 SUMMARY")
    print("="*60)
    
    if missing:
        print(f"\n❌ Missing {len(missing)} packages:")
        for pkg in missing:
            print(f"   • {pkg}")
        
        print("\n📝 To install missing packages, run:")
        print(f"   pip install {' '.join(missing)}")
        
        # Check if requirements.txt exists
        req_file = Path("requirements.txt")
        if req_file.exists():
            print("\n   Or install all requirements:")
            print("   pip install -r requirements.txt")
        
        sys.exit(1)
    else:
        print("\n✅ All required packages are installed!")
        print("\nYou can now run the orchestrator tests:")
        print("   1. ./run_orchestrator_test.sh  (automated)")
        print("   OR")
        print("   2. python launch_all_agents.py (in terminal 1)")
        print("      python test_orchestrators.py (in terminal 2)")
        
        # Check if agent files exist
        print("\n🔍 Checking agent files...")
        agent_dir = Path("examples/pipeline")
        if agent_dir.exists():
            agent_files = list(agent_dir.glob("*_agent.py"))
            print(f"✅ Found {len(agent_files)} agent files")
        else:
            print("❌ Agent directory not found: examples/pipeline/")
            sys.exit(1)

if __name__ == "__main__":
    main()