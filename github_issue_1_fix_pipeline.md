# Fix Pipeline Definition in Simple Orchestrator - Remove Incorrect Summarize Step

## Problem Statement
The `simple_orchestrator_agent.py` incorrectly includes a "summarize" agent as Step 4 after the chunk agent. This "summarize_agent.py" is NOT part of the official medical document analysis pipeline and should be removed.

## The Correct Pipeline
The official pipeline consists of 12 agents (not 13) in this specific order:

1. **Keyword Agent** - Generates search patterns
2. **Grep Agent** - Searches document using patterns
3. **Chunk Agent** - Extracts context around matches
4. **Temporal Tagging Agent** - Extracts temporal information
5. **Encounter Grouping Agent** - Groups by clinical encounters
6. **Reconciliation Agent** - Reconciles conflicting information
7. **Summary Extractor Agent** - Extracts structured summaries
8. **Timeline Builder Agent** ↔ **Checker Agent** - Builds timeline with verification loop
9. **Unified Extractor Agent** - Extracts all medical entities
10. **Unified Verifier Agent** - Final verification
11. **Narrative Synthesis Agent** - Creates final narrative

## Current Issue
The simple_orchestrator_agent.py currently has:
```python
# Step 1: Keyword
# Step 2: Grep
# Step 3: Chunk
# Step 4: Summarize  ← THIS SHOULD NOT EXIST
# Step 5: Temporal Tagging  ← Should be Step 4
# Step 6: Encounter Grouping  ← Should be Step 5
# ... etc
```

## Important Distinction
- `summarize_agent.py` (Medical Summarizer) - A standalone agent, NOT part of the pipeline
- `summary_extractor_agent.py` (Summary Extractor Agent) - Part of the pipeline, comes after reconciliation

## Tasks

### 1. Remove Step 4 (Summarize Agent)
Delete the entire Step 4 block that calls the summarize agent:
```python
# Step 4: Call Summarize Agent  ← DELETE THIS ENTIRE BLOCK
self.logger.info("\n📍 STEP 4: Calling Summarize Agent")
# ... all code for this step ...
```

### 2. Renumber All Subsequent Steps
- Current Step 5 (Temporal Tagging) becomes Step 4
- Current Step 6 (Encounter Grouping) becomes Step 5
- Current Step 7 (Reconciliation) becomes Step 6
- Current Step 8 (Summary Extractor) becomes Step 7
- Current Step 9 (Timeline Builder) becomes Step 8
- Current Step 10 (Checker) becomes Step 9
- Current Step 11 (Unified Extractor) becomes Step 10
- Current Step 12 (Unified Verifier) becomes Step 11
- Current Step 13 (Narrative Synthesis) becomes Step 12

### 3. Update Agent Description
Change from:
```python
"Calls ALL 13 agents in fixed order: keyword → grep → chunk → summarize → ..."
```
To:
```python
"Calls ALL 12 agents in fixed order: keyword → grep → chunk → temporal_tagging → ..."
```

### 4. Update Execution Statistics
In the final response, change:
```python
"All 13 pipeline stages completed"
```
To:
```python
"All 12 pipeline stages completed"
```

### 5. Update System Instruction
Remove any mention of the summarize agent from the system instruction. The pipeline should go directly from chunk to temporal_tagging.

### 6. Fix Data Flow
Ensure that:
- Chunks from Step 3 (Chunk) are passed to appropriate downstream agents
- Summary Extractor (Step 7) receives reconciled data, not chunk summaries
- The data flow matches the intended pipeline architecture

## Verification Steps
1. Count the steps - should be exactly 12
2. Verify no call to "summarize" agent (only "summary_extractor")
3. Confirm temporal_tagging comes immediately after chunk
4. Test the pipeline end-to-end to ensure data flows correctly

## Why This Matters
- The summarize agent was added incorrectly and disrupts the intended data flow
- It adds unnecessary processing time
- It confuses the distinction between summarization (not in pipeline) and summary extraction (in pipeline)
- The pipeline was designed with specific agent interactions that get broken by this extra step

## Acceptance Criteria
- [ ] Step 4 (Summarize Agent) completely removed
- [ ] All steps renumbered correctly (12 total steps)
- [ ] Agent description updated to show 12 agents
- [ ] System instruction updated
- [ ] Pipeline tested end-to-end successfully
- [ ] No references to "summarize" agent remain (only "summary_extractor")

## Priority
**CRITICAL** - This breaks the intended pipeline architecture and data flow