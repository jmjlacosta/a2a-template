#!/usr/bin/env python3
"""
Test script to verify both orchestrators work properly.
Tests simple sequential orchestrator and LLM-powered orchestrator.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.a2a_client import A2AAgentClient


# Test document - Eleanor Richardson medical record
TEST_DOCUMENT = """Patient: Eleanor Richardson, 72-year-old female
Date: March 15, 2024
Chief Complaint: Follow-up for diabetes management and hypertension

History of Present Illness:
Ms. Richardson returns for her 3-month follow-up. She reports good adherence to her medication regimen. 
Blood glucose logs show fasting levels 110-130 mg/dL. No hypoglycemic episodes.
Occasional mild headaches in the morning, resolved with acetaminophen.

Current Medications:
- Metformin 1000mg PO BID
- Lisinopril 20mg PO daily
- Atorvastatin 40mg PO daily
- Aspirin 81mg PO daily

Vital Signs:
- BP: 142/88 mmHg
- HR: 76 bpm regular
- Temp: 98.4°F
- Weight: 168 lbs (down 3 lbs from last visit)

Physical Examination:
General: Alert, well-appearing
Cardiovascular: Regular rate and rhythm, no murmurs
Lungs: Clear to auscultation bilaterally
Extremities: No edema, pedal pulses intact

Laboratory Results (March 10, 2024):
- HbA1c: 7.2% (improved from 7.8%)
- LDL: 95 mg/dL
- Creatinine: 1.1 mg/dL
- eGFR: 65 mL/min

Assessment and Plan:
1. Type 2 Diabetes Mellitus - Improved control
   - Continue metformin
   - Reinforce dietary modifications
   
2. Hypertension - Not at goal
   - Increase lisinopril to 30mg daily
   - Follow up in 1 month for BP check

3. Hyperlipidemia - At goal
   - Continue atorvastatin

Follow-up: 1 month for BP check, 3 months for diabetes"""


async def test_simple_orchestrator():
    """Test the simple sequential orchestrator."""
    print("\n" + "="*80)
    print("🧪 TESTING SIMPLE ORCHESTRATOR")
    print("="*80)
    
    try:
        # Simple orchestrator on port 8008
        agent_url = "http://localhost:8008"
        
        print(f"📍 Calling simple orchestrator at {agent_url}")
        print(f"📄 Document length: {len(TEST_DOCUMENT)} characters")
        
        start_time = time.time()
        
        async with A2AAgentClient(timeout=120.0) as client:
            # Simple orchestrator expects a direct document
            response = await client.call_agent(
                agent_url,
                TEST_DOCUMENT,
                timeout=120.0
            )
        
        elapsed = time.time() - start_time
        
        print(f"\n✅ Simple orchestrator completed in {elapsed:.2f} seconds")
        print(f"📥 Response length: {len(response)} characters")
        print("\n📋 Response preview:")
        print("-"*40)
        print(response[:500] + "..." if len(response) > 500 else response)
        print("-"*40)
        
        # Check if it mentions all pipeline stages
        stages_mentioned = [
            "keyword" in response.lower() or "pattern" in response.lower(),
            "grep" in response.lower() or "search" in response.lower(),
            "chunk" in response.lower() or "extract" in response.lower(),
            "summarize" in response.lower() or "summary" in response.lower(),
            "temporal" in response.lower(),
            "encounter" in response.lower(),
            "reconcil" in response.lower(),
            "timeline" in response.lower(),
            "checker" in response.lower() or "verif" in response.lower(),
            "narrative" in response.lower()
        ]
        
        stages_complete = sum(stages_mentioned)
        print(f"\n📊 Pipeline stages mentioned: {stages_complete}/10")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Simple orchestrator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_llm_orchestrator():
    """Test the LLM-powered orchestrator."""
    print("\n" + "="*80)
    print("🧪 TESTING LLM ORCHESTRATOR")
    print("="*80)
    
    try:
        # LLM orchestrator on port 8006
        agent_url = "http://localhost:8006"
        
        print(f"📍 Calling LLM orchestrator at {agent_url}")
        print(f"📄 Document length: {len(TEST_DOCUMENT)} characters")
        
        start_time = time.time()
        
        async with A2AAgentClient(timeout=120.0) as client:
            # LLM orchestrator expects a request
            message = f"""Please analyze this medical document and provide a comprehensive summary:

{TEST_DOCUMENT}

Use the full pipeline to extract all medical information."""
            
            response = await client.call_agent(
                agent_url,
                message,
                timeout=120.0
            )
        
        elapsed = time.time() - start_time
        
        print(f"\n✅ LLM orchestrator completed in {elapsed:.2f} seconds")
        print(f"📥 Response length: {len(response)} characters")
        print("\n📋 Response preview:")
        print("-"*40)
        print(response[:500] + "..." if len(response) > 500 else response)
        print("-"*40)
        
        # Check if it mentions coordinating agents
        coordination_indicators = [
            "coordinat" in response.lower(),
            "agent" in response.lower(),
            "pipeline" in response.lower(),
            "understand" in response.lower(),
            "plan" in response.lower(),
            "synthesi" in response.lower()
        ]
        
        indicators_found = sum(coordination_indicators)
        print(f"\n📊 Coordination indicators found: {indicators_found}/6")
        
        return True
        
    except Exception as e:
        print(f"\n❌ LLM orchestrator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all orchestrator tests."""
    print("\n" + "="*80)
    print("🚀 ORCHESTRATOR TEST SUITE")
    print("="*80)
    print("\nThis test will verify both orchestrators are working properly.")
    print("Make sure all agents are running (use launch_all_agents.py)")
    
    # Test simple orchestrator
    simple_success = await test_simple_orchestrator()
    
    # Small delay between tests
    await asyncio.sleep(2)
    
    # Test LLM orchestrator
    llm_success = await test_llm_orchestrator()
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    print(f"Simple Orchestrator: {'✅ PASSED' if simple_success else '❌ FAILED'}")
    print(f"LLM Orchestrator: {'✅ PASSED' if llm_success else '❌ FAILED'}")
    
    if simple_success and llm_success:
        print("\n🎉 All orchestrators working correctly!")
    else:
        print("\n⚠️ Some orchestrators have issues. Check the logs above.")
    
    return simple_success and llm_success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)