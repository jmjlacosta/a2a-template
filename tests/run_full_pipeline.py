#!/usr/bin/env python3
"""
Script to run the full cancer summarization pipeline by calling each agent sequentially.
This demonstrates the complete pipeline without using an orchestrator.
"""

import asyncio
import json
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.a2a_client import A2AAgentClient

# Test document
TEST_DOCUMENT = """
PATIENT: Eleanor Richardson
DATE: March 15, 2024

CHIEF COMPLAINT: Follow-up for melanoma treatment

HISTORY OF PRESENT ILLNESS:
Ms. Richardson is a 68-year-old female with Stage IIIB melanoma diagnosed in January 2024. 
She completed her third cycle of pembrolizumab (Keytruda) on March 1, 2024. She reports 
mild fatigue but no fever, rash, or other immune-related adverse events.

PAST MEDICAL HISTORY:
- Stage IIIB melanoma (BRAF V600E positive), diagnosed January 2024
- Hypertension, controlled
- Type 2 diabetes mellitus

CURRENT MEDICATIONS:
- Pembrolizumab 200mg IV q3 weeks
- Metformin 1000mg BID
- Lisinopril 10mg daily

PHYSICAL EXAMINATION:
- Vitals: BP 128/76, HR 72, Temp 98.6°F
- Skin: Surgical scar well-healed, no new lesions
- Lymph nodes: No palpable lymphadenopathy

LABORATORY RESULTS (March 10, 2024):
- WBC: 6.8 K/uL (normal)
- Hemoglobin: 12.2 g/dL (slightly low)
- Platelets: 245 K/uL (normal)
- LDH: 210 U/L (normal)
- Liver function tests: Within normal limits

IMAGING:
PET/CT (March 8, 2024): No evidence of disease progression. Previous sites of 
metastatic disease show continued response to treatment.

ASSESSMENT AND PLAN:
1. Stage IIIB melanoma - Responding well to immunotherapy
2. Continue pembrolizumab as scheduled
3. Monitor for immune-related adverse events
4. Repeat imaging in 3 months
5. Follow-up in 3 weeks for next treatment cycle

Dr. Sarah Chen, MD
Oncology Department
"""

# Agent configurations
AGENTS = [
    {"name": "keyword", "port": 8001, "file": "examples/pipeline/keyword_agent.py"},
    {"name": "grep", "port": 8002, "file": "examples/pipeline/grep_agent.py"},
    {"name": "chunk", "port": 8003, "file": "examples/pipeline/chunk_agent.py"},
    {"name": "summarize", "port": 8004, "file": "examples/pipeline/summarize_agent.py"},
    {"name": "temporal_tagging", "port": 8010, "file": "examples/pipeline/temporal_tagging_agent.py"},
    {"name": "encounter_grouping", "port": 8011, "file": "examples/pipeline/encounter_grouping_agent.py"},
    {"name": "reconciliation", "port": 8012, "file": "examples/pipeline/reconciliation_agent_hybrid.py"},
    {"name": "summary_extractor", "port": 8013, "file": "examples/pipeline/summary_extractor_agent.py"},
    {"name": "timeline_builder", "port": 8014, "file": "examples/pipeline/timeline_builder_agent.py"},
    {"name": "checker", "port": 8015, "file": "examples/pipeline/checker_agent.py"},
    {"name": "unified_extractor", "port": 8016, "file": "examples/pipeline/unified_extractor_agent.py"},
    {"name": "unified_verifier", "port": 8017, "file": "examples/pipeline/unified_verifier_agent.py"},
    {"name": "narrative_synthesis", "port": 8018, "file": "examples/pipeline/narrative_synthesis_agent.py"},
]


def start_agents():
    """Start all agents as background processes."""
    print("🚀 Starting all agents...")
    print("="*80)
    
    processes = []
    for agent in AGENTS:
        cmd = f"PORT={agent['port']} python {agent['file']}"
        log_file = f"{agent['name']}.log"
        
        print(f"  Starting {agent['name']:20} on port {agent['port']}... ", end="")
        
        with open(log_file, "w") as log:
            process = subprocess.Popen(
                cmd, 
                shell=True, 
                stdout=log, 
                stderr=log,
                preexec_fn=None
            )
            processes.append((agent['name'], process))
            print(f"✓ (PID: {process.pid})")
    
    print("\n⏳ Waiting 30 seconds for agents to initialize (loading LLM models)...")
    time.sleep(30)
    
    return processes


def stop_agents(processes):
    """Stop all agent processes."""
    print("\n🛑 Stopping all agents...")
    for name, process in processes:
        print(f"  Stopping {name:20}... ", end="")
        process.terminate()
        process.wait(timeout=5)
        print("✓")


async def run_pipeline():
    """Run the full pipeline by calling each agent sequentially."""
    
    print("\n" + "="*80)
    print("🔬 RUNNING FULL CANCER PIPELINE (AGENT BY AGENT)")
    print("="*80)
    
    results = {}
    
    try:
        # Step 1: Keyword Generation
        print("\n📍 STEP 1: Keyword Generation")
        print("-"*40)
        
        keyword_message = f"""Generate comprehensive regex patterns for finding cancer-related information in this medical document:

{TEST_DOCUMENT[:1500]}

Focus on:
- Cancer types, stages, grades
- Oncology treatments (chemotherapy, radiation, surgery)
- Tumor markers and genetic mutations
- Metastasis and progression
- Response to treatment

Generate patterns for all cancer-related medical information."""
        
        async with A2AAgentClient(timeout=600) as client:  # 10 minute timeout
            print(f"Calling keyword agent...")
            keyword_response = await client.call_agent("http://localhost:8001", keyword_message)
            results["keyword"] = keyword_response
            print(f"✓ Received {len(keyword_response)} characters")
        
        # Step 2: Grep Search
        print("\n📍 STEP 2: Pattern Search (Grep)")
        print("-"*40)
        
        # Extract patterns from keyword response (simplified)
        patterns = []
        for line in keyword_response.split('\n'):
            if '"' in line:
                import re
                quoted = re.findall(r'"([^"]*)"', line)
                patterns.extend(quoted)
        
        if not patterns:
            patterns = ["melanoma", "cancer", "stage", "pembrolizumab", "BRAF"]
        
        grep_message = json.dumps({
            "patterns": patterns[:10],
            "document_content": TEST_DOCUMENT,
            "case_sensitive": False
        })
        
        async with A2AAgentClient(timeout=600) as client:  # 10 minute timeout
            print(f"Calling grep agent with {len(patterns[:10])} patterns...")
            grep_response = await client.call_agent("http://localhost:8002", grep_message)
            results["grep"] = grep_response
            print(f"✓ Received {len(grep_response)} characters")
        
        # Step 3: Chunk Extraction
        print("\n📍 STEP 3: Context Extraction (Chunking)")
        print("-"*40)
        
        # Parse grep results
        try:
            grep_data = json.loads(grep_response)
            matches = grep_data.get("matches", [])[:5]  # Limit to 5 matches
        except:
            matches = [{"line_number": 8, "text": "Stage IIIB melanoma"}]
        
        chunks = []
        for i, match in enumerate(matches, 1):
            chunk_message = json.dumps({
                "match_info": match,
                "lines_before": 3,
                "lines_after": 3,
                "document_content": TEST_DOCUMENT
            })
            
            async with A2AAgentClient(timeout=600) as client:  # 10 minute timeout
                print(f"  [{i}/{len(matches)}] Extracting chunk...")
                chunk_response = await client.call_agent("http://localhost:8003", chunk_message)
                chunks.append(chunk_response)
        
        combined_chunks = "\n\n".join(chunks)
        results["chunks"] = combined_chunks
        print(f"✓ Extracted {len(chunks)} chunks")
        
        # Step 4: Temporal Tagging (directly after chunks)
        print("\n📍 STEP 4: Temporal Information Extraction")
        print("-"*40)
        
        temporal_message = f"""Extract all temporal information from this cancer patient data:

{combined_chunks}

Focus on:
- Diagnosis dates
- Treatment dates
- Follow-up appointments
- Progression timelines"""
        
        async with A2AAgentClient(timeout=600) as client:  # 10 minute timeout
            print(f"Calling temporal tagging agent...")
            temporal_response = await client.call_agent("http://localhost:8010", temporal_message)
            results["temporal"] = temporal_response
            print(f"✓ Extracted temporal data")
        
        # Step 5: Encounter Grouping
        print("\n📍 STEP 5: Encounter Grouping")
        print("-"*40)
        
        encounter_message = json.dumps({
            "temporal_data": temporal_response,
            "clinical_content": combined_chunks,
            "focus": "oncology visits"
        })
        
        async with A2AAgentClient(timeout=600) as client:  # 10 minute timeout
            print(f"Calling encounter grouping agent...")
            encounter_response = await client.call_agent("http://localhost:8011", encounter_message)
            results["encounters"] = encounter_response
            print(f"✓ Grouped encounters")
        
        # Step 6: Reconciliation
        print("\n📍 STEP 6: Data Reconciliation")
        print("-"*40)
        
        # Parse encounter response to extract structured data
        # The reconciliation agent expects specific structure
        try:
            # Try to create a structured encounter group from the narrative response
            encounter_group = {
                "encounter_date": "January 2024",  # From the encounter response
                "encounter_type": "diagnosis_and_treatment",
                "primary_content": [
                    {
                        "text": "Ms. Richardson is a 68-year-old female with Stage IIIB melanoma diagnosed.",
                        "is_carry_forward": False
                    },
                    {
                        "text": "She completed her third cycle of pembrolizumab (Keytruda) on March 1, 2024.",
                        "is_carry_forward": False
                    }
                ],
                "referenced_content": []
            }
            
            # The reconciliation agent expects the message to be about reconciling a single encounter group
            reconciliation_message = f"""Please reconcile the following clinical information:
            
Encounter Date: January 2024 - March 2024
Clinical Content:
{combined_chunks}

Temporal Information:
{temporal_response}

Encounter Information:
{encounter_response}

Please identify any conflicting information, duplicates, or carry-forward notes and reconcile them."""
            
        except Exception as e:
            print(f"Warning: Could not parse encounter data, using raw format: {e}")
            reconciliation_message = f"Reconcile this data:\n{encounter_response}\n\nTemporal: {temporal_response}"
        
        async with A2AAgentClient(timeout=600) as client:  # 10 minute timeout
            print(f"Calling reconciliation agent...")
            reconciled = await client.call_agent("http://localhost:8012", reconciliation_message)
            results["reconciled"] = reconciled
            print(f"✓ Reconciled data")
        
        # Step 7: Summary Extraction
        print("\n📍 STEP 7: Summary Extraction")
        print("-"*40)
        
        summary_extract_message = json.dumps({
            "reconciled_data": reconciled,
            "focus": "cancer diagnosis, staging, treatment",
            "extract": "structured summary"
        })
        
        async with A2AAgentClient(timeout=600) as client:  # 10 minute timeout
            print(f"Calling summary extractor agent...")
            extracted_summary = await client.call_agent("http://localhost:8013", summary_extract_message)
            results["extracted_summary"] = extracted_summary
            print(f"✓ Extracted structured summary")
        
        # Step 8: Timeline Building (using JSON format)
        print("\n📍 STEP 8: Timeline Construction")
        print("-"*40)
        
        # Create structured JSON message for timeline builder
        timeline_data = {
            "action": "build_timeline",
            "summary": extracted_summary,
            "temporal_data": temporal_response,
            "encounters": encounter_response,
            "reconciled_data": reconciled,
            "instructions": "Build a chronological timeline of this cancer patient's journey"
        }
        
        timeline_message = json.dumps(timeline_data)
        
        async with A2AAgentClient(timeout=600) as client:  # 10 minute timeout
            print(f"Calling timeline builder agent with JSON data...")
            timeline = await client.call_agent("http://localhost:8014", timeline_message)
            results["timeline"] = timeline
            print(f"✓ Built timeline")
        
        # Step 9: Checker (with retry loop)
        print("\n📍 STEP 9: Quality Check")
        print("-"*40)
        
        checked_summary = extracted_summary
        for attempt in range(1, 4):
            print(f"  Attempt {attempt}/3...")
            
            checker_message = json.dumps({
                "summary": checked_summary,
                "timeline": timeline,
                "original_data": reconciled,
                "check_for": "accuracy, completeness"
            })
            
            async with A2AAgentClient(timeout=600) as client:  # 10 minute timeout
                checker_response = await client.call_agent("http://localhost:8015", checker_message)
                
            # Check if issues found
            if not any(word in checker_response.lower() for word in ["issue", "error", "incorrect", "missing"]):
                print(f"  ✓ No issues found")
                break
            else:
                print(f"  ⚠️ Issues found, fixing...")
                if attempt < 3:
                    # Fix with summary extractor
                    fix_message = json.dumps({
                        "original_data": reconciled,
                        "checker_feedback": checker_response,
                        "instruction": "Fix the issues"
                    })
                    async with A2AAgentClient(timeout=600) as client:  # 10 minute timeout
                        checked_summary = await client.call_agent("http://localhost:8013", fix_message)
        
        results["checked_summary"] = checked_summary
        
        # Step 10: Unified Extraction (using JSON format)
        print("\n📍 STEP 10: Unified Medical Entity Extraction")
        print("-"*40)
        
        # Create structured JSON message for unified extractor
        unified_data_request = {
            "action": "extract_entities",
            "summary": checked_summary,
            "timeline": timeline,
            "reconciled_data": reconciled,
            "entity_types": ["medications", "procedures", "diagnoses", "lab_results", "vital_signs"],
            "instructions": "Extract all medical entities from this clinical data"
        }
        
        unified_message = json.dumps(unified_data_request)
        
        async with A2AAgentClient(timeout=600) as client:  # 10 minute timeout
            print(f"Calling unified extractor agent with JSON data...")
            unified_data = await client.call_agent("http://localhost:8016", unified_message)
            results["unified"] = unified_data
            print(f"✓ Extracted entities")
        
        # Step 11: Unified Verification
        print("\n📍 STEP 11: Final Verification")
        print("-"*40)
        
        verify_message = json.dumps({
            "extracted_data": unified_data,
            "original_summary": checked_summary,
            "timeline": timeline,
            "verify": "completeness, accuracy"
        })
        
        async with A2AAgentClient(timeout=600) as client:  # 10 minute timeout
            print(f"Calling unified verifier agent...")
            verified = await client.call_agent("http://localhost:8017", verify_message)
            results["verified"] = verified
            print(f"✓ Verification complete")
        
        # Step 12: Narrative Synthesis
        print("\n📍 STEP 12: Final Narrative Synthesis")
        print("-"*40)
        
        narrative_message = json.dumps({
            "verified_data": verified,
            "summary": checked_summary,
            "timeline": timeline,
            "synthesize": "comprehensive cancer patient narrative"
        })
        
        async with A2AAgentClient(timeout=600) as client:  # 10 minute timeout
            print(f"Calling narrative synthesis agent...")
            final_narrative = await client.call_agent("http://localhost:8018", narrative_message)
            results["narrative"] = final_narrative
            print(f"✓ Narrative complete")
        
        # Final output
        print("\n" + "="*80)
        print("✅ PIPELINE COMPLETE")
        print("="*80)
        print("\n📊 FINAL NARRATIVE:")
        print("-"*40)
        print(final_narrative[:2000] + "..." if len(final_narrative) > 2000 else final_narrative)
        
        return results
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return results


async def main():
    """Main function to run the full pipeline."""
    
    # Start all agents
    processes = start_agents()
    
    try:
        # Run the pipeline
        results = await run_pipeline()
        
        # Save results
        with open("pipeline_results.json", "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to pipeline_results.json")
        
    finally:
        # Stop all agents
        stop_agents(processes)


if __name__ == "__main__":
    print("\n🔬 FULL CANCER PIPELINE TEST")
    print("This will start all 12 agents and call them sequentially.\n")
    
    asyncio.run(main())