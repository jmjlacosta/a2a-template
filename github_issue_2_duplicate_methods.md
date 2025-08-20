# Complete Audit of All Agents for Duplicate Method Definitions

## Problem Statement
While fixing agent communication issues, we discovered that some agents had duplicate `process_message` methods which caused Python to use the wrong implementation. We need a comprehensive audit to ensure no agent has duplicate methods that could cause confusion or runtime errors.

## Background
During debugging, we found that grep_agent.py, chunk_agent.py, and summarize_agent.py each had TWO `process_message` methods:
1. One with actual JSON handling logic
2. One that just returned "Handled by tool execution"

Python was using the second one, breaking agent-to-agent communication. This has been fixed for these three agents, but we need to verify all agents are clean.

## Current Status
Initial check shows each agent now has exactly ONE `process_message` method:
```bash
cancer_summarization_agent.py: 1 process_message
checker_agent.py: 1 process_message
chunk_agent.py: 1 process_message (fixed)
encounter_grouping_agent.py: 1 process_message
grep_agent.py: 1 process_message (fixed)
keyword_agent.py: 1 process_message
narrative_synthesis_agent.py: 1 process_message
orchestrator_agent.py: 1 process_message
reconciliation_agent.py: 1 process_message
simple_orchestrator_agent.py: 1 process_message
summarize_agent.py: 1 process_message (fixed)
summary_extractor_agent.py: 1 process_message
temporal_tagging_agent.py: 1 process_message
timeline_builder_agent.py: 1 process_message
unified_extractor_agent.py: 1 process_message
unified_verifier_agent.py: 1 process_message
```

## Tasks

### 1. Check for Other Duplicate Methods
Beyond `process_message`, check all agents for:
- Duplicate `get_tools()` methods
- Duplicate `get_system_instruction()` methods
- Duplicate `get_agent_name()` methods
- Duplicate `get_agent_description()` methods
- Duplicate `get_agent_skills()` methods
- Duplicate `supports_streaming()` methods
- Any other method defined more than once

### 2. Verify Tool Registrations
Check that no agent:
- Imports the same tool multiple times
- Registers the same tool function twice
- Has conflicting tool imports (e.g., both TOOLS and TOOLS_FIXED)

### 3. Check for Import Conflicts
Verify no agent has:
- Duplicate imports of the same module
- Conflicting imports (e.g., `from tools import X` and `from tools.fixed import X`)
- Circular import dependencies

### 4. Validate Method Signatures
Ensure all overridden methods have correct signatures:
- `async def process_message(self, message: str) -> str`
- `def get_tools(self) -> List`
- `def get_system_instruction(self) -> str`
- etc.

### 5. Document Findings
Create a report showing:
- Any duplicate methods found
- Any import conflicts discovered
- Any signature mismatches
- Recommendations for fixes

## Testing Approach

### Script to Check for Duplicates
```python
import ast
import os
from collections import defaultdict

def check_duplicates(filepath):
    with open(filepath, 'r') as f:
        tree = ast.parse(f.read())
    
    methods = defaultdict(list)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            methods[node.name].append(node.lineno)
    
    duplicates = {name: lines for name, lines in methods.items() if len(lines) > 1}
    return duplicates

# Check all agents
for agent_file in os.listdir('examples/pipeline'):
    if agent_file.endswith('_agent.py'):
        duplicates = check_duplicates(f'examples/pipeline/{agent_file}')
        if duplicates:
            print(f"{agent_file}: {duplicates}")
```

## Expected Outcome
- Confirmation that no agent has duplicate method definitions
- List of any issues found with recommendations
- Guidelines to prevent future duplications

## Prevention Measures
1. Add a pre-commit hook to check for duplicate methods
2. Include duplicate checking in CI/CD pipeline
3. Document the single-method-definition rule in developer guidelines

## Acceptance Criteria
- [ ] All 16 agents checked for duplicate methods
- [ ] Tool registrations verified
- [ ] Import conflicts checked
- [ ] Method signatures validated
- [ ] Report created with findings
- [ ] Prevention measures documented

## Priority
**HIGH** - Duplicate methods cause silent failures that are hard to debug