#!/usr/bin/env python3
"""
Minimal pipeline test to verify the fixed agents work together.
Tests only the critical path agents.
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

ASSESSMENT AND PLAN:
1. Stage IIIB melanoma - Responding well to immunotherapy
2. Continue pembrolizumab as scheduled
3. Monitor for immune-related adverse events
4. Follow-up in 3 weeks for next treatment cycle
"""

# Minimal agent set - just the essentials
AGENTS = [
    {"name": "keyword", "port": 8001, "file": "examples/pipeline/keyword_agent.py"},
    {"name": "temporal_tagging", "port": 8010, "file": "examples/pipeline/temporal_tagging_agent.py"},
    {"name": "timeline_builder", "port": 8014, "file": "examples/pipeline/timeline_builder_agent.py"},
    {"name": "narrative_synthesis", "port": 8018, "file": "examples/pipeline/narrative_synthesis_agent.py"},
]


def start_agents():
    """Start all agents as background processes."""
    print("🚀 Starting agents...")
    print("=" * 60)
    
    processes = []
    for agent in AGENTS:
        cmd = f"PORT={agent['port']} python {agent['file']}"
        
        print(f"  Starting {agent['name']:20} on port {agent['port']}... ", end="", flush=True)
        
        process = subprocess.Popen(
            cmd, 
            shell=True, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processes.append((agent['name'], process, agent['port']))
        print(f"✓ (PID: {process.pid})")
    
    print("\n⏳ Waiting 10 seconds for agents to initialize...")
    time.sleep(10)
    
    return processes


def stop_agents(processes):
    """Stop all agent processes."""
    print("\n🛑 Stopping all agents...")
    for name, process, _ in processes:
        print(f"  Stopping {name:20}... ", end="", flush=True)
        process.terminate()
        try:
            process.wait(timeout=5)
            print("✓")
        except subprocess.TimeoutExpired:
            process.kill()
            print("✓ (force killed)")


async def run_minimal_pipeline():
    """Run a minimal pipeline test."""
    
    print("\n" + "=" * 60)
    print("🔬 RUNNING MINIMAL PIPELINE TEST")
    print("=" * 60)
    
    results = {}
    
    try:
        # Step 1: Keyword Generation
        print("\n📍 STEP 1: Keyword Generation")
        print("-" * 40)
        
        keyword_message = f"""Generate comprehensive regex patterns for finding medical information in this document:

{TEST_DOCUMENT[:500]}

Focus on: diagnoses, treatments, dates, medications, stages"""
        
        async with A2AAgentClient(timeout=60) as client:
            print(f"Calling keyword agent...")
            keyword_response = await client.call_agent("http://localhost:8001", keyword_message)
            results["keyword"] = keyword_response
            print(f"✓ Received {len(keyword_response)} characters")
            print(f"Preview: {keyword_response[:200]}...")
        
        # Step 2: Temporal Tagging
        print("\n📍 STEP 2: Temporal Information Extraction")
        print("-" * 40)
        
        temporal_message = f"""Extract all temporal information from this medical document:

{TEST_DOCUMENT}

Identify:
- Diagnosis dates
- Treatment dates
- Follow-up appointments
- All temporal references"""
        
        async with A2AAgentClient(timeout=60) as client:
            print(f"Calling temporal tagging agent...")
            temporal_response = await client.call_agent("http://localhost:8010", temporal_message)
            results["temporal"] = temporal_response
            print(f"✓ Extracted temporal data")
            print(f"Preview: {temporal_response[:200]}...")
        
        # Step 3: Timeline Building
        print("\n📍 STEP 3: Timeline Construction")
        print("-" * 40)
        
        # Create a simple timeline data structure
        timeline_events = [
            {
                "date": "January 2024",
                "summary": "Stage IIIB melanoma diagnosed, BRAF V600E positive",
                "verified": True,
                "source_documents": ["test_doc"],
                "source_pages": [1]
            },
            {
                "date": "March 1, 2024",
                "summary": "Completed third cycle of pembrolizumab (Keytruda)",
                "verified": True,
                "source_documents": ["test_doc"],
                "source_pages": [1]
            },
            {
                "date": "March 15, 2024",
                "summary": "Follow-up visit, responding well to immunotherapy",
                "verified": True,
                "source_documents": ["test_doc"],
                "source_pages": [1]
            }
        ]
        
        timeline_message = json.dumps({
            "facts": timeline_events,
            "verification_mode": "standard",
            "max_retries": 3,
            "instructions": "Build a chronological timeline of this cancer patient's journey"
        })
        
        async with A2AAgentClient(timeout=60) as client:
            print(f"Calling timeline builder agent...")
            timeline = await client.call_agent("http://localhost:8014", timeline_message)
            results["timeline"] = timeline
            print(f"✓ Built timeline")
            print(f"Preview: {timeline[:200]}...")
        
        # Step 4: Narrative Synthesis
        print("\n📍 STEP 4: Final Narrative Synthesis")
        print("-" * 40)
        
        narrative_message = json.dumps({
            "timeline_events": timeline_events,
            "diagnosis_treatment_data": {
                "diagnosis": "Stage IIIB melanoma, BRAF V600E positive",
                "treatment": "Pembrolizumab 200mg IV q3 weeks"
            },
            "patient_headline": "68-year-old female with Stage IIIB melanoma",
            "synthesize": "comprehensive cancer patient narrative"
        })
        
        async with A2AAgentClient(timeout=60) as client:
            print(f"Calling narrative synthesis agent...")
            final_narrative = await client.call_agent("http://localhost:8018", narrative_message)
            results["narrative"] = final_narrative
            print(f"✓ Narrative complete")
        
        # Final output
        print("\n" + "=" * 60)
        print("✅ PIPELINE COMPLETE")
        print("=" * 60)
        print("\n📊 FINAL NARRATIVE:")
        print("-" * 40)
        print(final_narrative[:1000] + "..." if len(final_narrative) > 1000 else final_narrative)
        
        return results
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return results


async def main():
    """Main function to run the minimal pipeline test."""
    
    # Start all agents
    processes = start_agents()
    
    try:
        # Run the pipeline
        results = await run_minimal_pipeline()
        
        # Save results
        with open("minimal_pipeline_results.json", "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to minimal_pipeline_results.json")
        
    finally:
        # Stop all agents
        stop_agents(processes)


if __name__ == "__main__":
    print("\n🔬 MINIMAL PIPELINE TEST")
    print("This tests only the essential agents with fixed tools.\n")
    
    asyncio.run(main())