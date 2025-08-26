#!/usr/bin/env python3
"""
Switch between local and production agent configurations.

Usage:
    python switch_config.py local    # Use local development URLs
    python switch_config.py prod     # Use HealthUniverse production URLs
"""

import sys
import json
import shutil
from pathlib import Path

def switch_to_local():
    """Switch to local development configuration."""
    config = {
        "agents": {
            "orchestrator": {"url": "http://localhost:8008"},
            "keyword": {"url": "http://localhost:8101"},
            "grep": {"url": "http://localhost:8102"},
            "chunk": {"url": "http://localhost:8103"},
            "summarize": {"url": "http://localhost:8104"}
        }
    }
    
    config_path = Path("config/agents.json")
    config_path.write_text(json.dumps(config, indent=2))
    print("✅ Switched to LOCAL configuration")
    print("   Orchestrator: http://localhost:8008")
    print("   Keyword:      http://localhost:8101")
    print("   Grep:         http://localhost:8102")
    print("   Chunk:        http://localhost:8103")
    print("   Summarize:    http://localhost:8104")

def switch_to_production():
    """Switch to production configuration."""
    config = {
        "agents": {
            "orchestrator": {"url": "https://apps.healthuniverse.com/omj-cuu-rdv"},
            "keyword": {"url": "https://apps.healthuniverse.com/uad-nmu-ifv"},
            "grep": {"url": "https://apps.healthuniverse.com/tfi-zlr-ygy"},
            "chunk": {"url": "https://apps.healthuniverse.com/mgd-hyk-cbr"},
            "summarize": {"url": "https://apps.healthuniverse.com/ehc-xve-thr"}
        }
    }
    
    config_path = Path("config/agents.json")
    # Backup current config
    backup_path = Path("config/agents.json.backup")
    if config_path.exists():
        shutil.copy(config_path, backup_path)
        print(f"📦 Backed up current config to {backup_path}")
    
    config_path.write_text(json.dumps(config, indent=2))
    print("✅ Switched to PRODUCTION configuration")
    print("   Cancer Summarization - Simple Orchestrator: https://apps.healthuniverse.com/omj-cuu-rdv")
    print("   CS Pipeline - Keyword Generator:            https://apps.healthuniverse.com/uad-nmu-ifv")
    print("   CS Pipeline - Grep:                         https://apps.healthuniverse.com/tfi-zlr-ygy")
    print("   CS Pipeline - Chunker:                      https://apps.healthuniverse.com/mgd-hyk-cbr")
    print("   CS Pipeline - Summarization:                https://apps.healthuniverse.com/ehc-xve-thr")

def show_current():
    """Show current configuration."""
    config_path = Path("config/agents.json")
    if not config_path.exists():
        print("❌ No config file found at config/agents.json")
        return
    
    config = json.loads(config_path.read_text())
    
    # Detect if local or production
    first_url = list(config["agents"].values())[0]["url"]
    is_local = "localhost" in first_url
    
    print(f"📍 Current configuration: {'LOCAL' if is_local else 'PRODUCTION'}")
    print("   Agents:")
    for name, info in config["agents"].items():
        print(f"     {name:12} → {info['url']}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_current()
        print("\nUsage:")
        print("  python switch_config.py local  # Switch to local URLs")
        print("  python switch_config.py prod   # Switch to production URLs")
        sys.exit(0)
    
    command = sys.argv[1].lower()
    
    if command in ("local", "dev"):
        switch_to_local()
    elif command in ("prod", "production"):
        switch_to_production()
    elif command in ("show", "current"):
        show_current()
    else:
        print(f"❌ Unknown command: {command}")
        print("   Use 'local' or 'prod'")
        sys.exit(1)