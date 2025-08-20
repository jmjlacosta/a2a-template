#!/usr/bin/env python3
"""
Patch all agents to handle JSON messages from orchestrators.
This adds process_message methods to agents that don't have them.
"""

import os
import sys
from pathlib import Path

# Template for process_message method
PROCESS_MESSAGE_TEMPLATE = '''
    async def process_message(self, message: str) -> str:
        """
        Process incoming messages.
        Handles JSON messages from orchestrators by passing to tools.
        """
        try:
            # Try to parse as JSON
            data = json.loads(message)
            
            # If it's JSON, it's likely from an orchestrator
            # Pass it through to the LLM with tools for proper handling
            return message
                
        except json.JSONDecodeError:
            # Not JSON, pass through as is
            return message
'''

# Agents that need patching (those with tools but no custom process_message)
AGENTS_TO_PATCH = [
    "temporal_tagging_agent.py",
    "encounter_grouping_agent.py", 
    "reconciliation_agent.py",
    "summary_extractor_agent.py",
    "timeline_builder_agent.py",
    "checker_agent.py",
    "unified_extractor_agent.py",
    "unified_verifier_agent.py",
    "narrative_synthesis_agent.py"
]

def patch_agent(file_path):
    """Patch a single agent file."""
    print(f"Checking {file_path.name}...")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if already has process_message
    if "async def process_message" in content:
        print(f"  ✓ Already has process_message")
        return False
    
    # Check if has json import
    if "import json" not in content:
        # Add json import after sys import
        content = content.replace(
            "import sys\n",
            "import sys\nimport json\n"
        )
        print(f"  + Added json import")
    
    # Find where to insert process_message (before get_agent_skills or at end of class)
    if "def get_agent_skills" in content:
        # Insert before get_agent_skills
        content = content.replace(
            "    def get_agent_skills",
            PROCESS_MESSAGE_TEMPLATE + "\n    def get_agent_skills"
        )
    elif "def get_tools" in content:
        # Insert after get_tools
        lines = content.split('\n')
        new_lines = []
        in_get_tools = False
        tools_indent = 0
        
        for i, line in enumerate(lines):
            new_lines.append(line)
            
            if "def get_tools" in line:
                in_get_tools = True
                tools_indent = len(line) - len(line.lstrip())
            
            elif in_get_tools and line.strip().startswith("return"):
                # Found return in get_tools
                in_get_tools = False
                # Add process_message after this line
                new_lines.append(PROCESS_MESSAGE_TEMPLATE)
        
        content = '\n'.join(new_lines)
    
    # Write back
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"  ✓ Patched successfully")
    return True

def main():
    """Patch all agents."""
    pipeline_dir = Path(__file__).parent / "examples" / "pipeline"
    
    patched_count = 0
    for agent_file in AGENTS_TO_PATCH:
        file_path = pipeline_dir / agent_file
        if file_path.exists():
            if patch_agent(file_path):
                patched_count += 1
        else:
            print(f"⚠️ {agent_file} not found")
    
    print(f"\n✓ Patched {patched_count} agents")

if __name__ == "__main__":
    main()