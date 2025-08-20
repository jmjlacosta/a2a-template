#!/usr/bin/env python3
"""
Test script for both orchestrator implementations.
Tests the LLM-powered orchestrator and the simple sequential orchestrator.

Usage:
1. First, launch all agents: python launch_all_agents.py
2. Then run this test: python test_orchestrators.py
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any
import httpx
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.a2a_client import A2AAgentClient

# Test document - Eleanor Richardson medical record
TEST_DOCUMENT = """
PATIENT: Eleanor Richardson
DATE: March 15, 2024

CHIEF COMPLAINT: Follow-up for melanoma treatment

HISTORY OF PRESENT ILLNESS:
Ms. Richardson is a 68-year-old female with Stage IIIB melanoma diagnosed in January 2024. 
She completed her third cycle of pembrolizumab (Keytruda) on March 1, 2024. She reports 
mild fatigue but no fever, rash, or other immune-related adverse events.

PAST MEDICAL HISTORY:
- Stage IIIB melanoma (January 2024)
- Hypertension (2015)
- Type 2 Diabetes Mellitus (2018)
- Osteoarthritis

CURRENT MEDICATIONS:
- Pembrolizumab 200mg IV every 3 weeks
- Metformin 1000mg PO BID
- Lisinopril 10mg PO daily
- Acetaminophen 500mg PRN for pain

PHYSICAL EXAMINATION:
Vitals: BP 128/76, HR 72, Temp 98.6°F, Weight 145 lbs
Skin: No new lesions, surgical scar well-healed
Lymph nodes: No palpable lymphadenopathy
Cardiovascular: Regular rate and rhythm
Respiratory: Clear to auscultation bilaterally

LABORATORY RESULTS (March 14, 2024):
- WBC: 5.8 K/uL (normal)
- Hemoglobin: 12.5 g/dL
- Platelet count: 186 K/uL
- Creatinine: 0.9 mg/dL
- ALT: 28 U/L
- AST: 31 U/L
- LDH: 189 U/L (normal)

IMAGING:
CT chest/abdomen/pelvis (March 10, 2024): No evidence of metastatic disease. 
Previous sites of disease show continued response to treatment.

ASSESSMENT AND PLAN:
1. Stage IIIB melanoma - Responding well to pembrolizumab. Continue current treatment.
   Next infusion scheduled for March 22, 2024.
2. Monitor for immune-related adverse events
3. Follow-up in 3 weeks with repeat labs
4. Repeat imaging in 12 weeks

Dr. Sarah Mitchell, MD
Oncology Department
"""


class OrchestratorTester:
    """Test harness for orchestrator agents."""
    
    def __init__(self):
        self.client = None
        self.results = {}
        
    async def __aenter__(self):
        self.client = A2AAgentClient(timeout=120.0)
        await self.client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def check_agent_health(self, name: str, port: int) -> bool:
        """Check if an agent is healthy."""
        try:
            url = f"http://localhost:{port}/.well-known/agent-card.json"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5.0)
                if response.status_code == 200:
                    card = response.json()
                    print(f"✅ {name} is healthy")
                    print(f"   Version: {card.get('version', 'unknown')}")
                    print(f"   Skills: {len(card.get('skills', []))}")
                    return True
        except Exception as e:
            print(f"❌ {name} health check failed: {e}")
        return False
    
    async def test_simple_orchestrator(self) -> Dict[str, Any]:
        """Test the simple sequential orchestrator."""
        print("\n" + "="*80)
        print("🧪 TESTING SIMPLE SEQUENTIAL ORCHESTRATOR")
        print("="*80)
        
        start_time = time.time()
        result = {
            "type": "simple_orchestrator",
            "success": False,
            "response": None,
            "error": None,
            "duration": 0
        }
        
        try:
            # Check if orchestrator is running (port 8008 is the actual default)
            if not await self.check_agent_health("Simple Orchestrator", 8008):
                result["error"] = "Simple orchestrator not running on port 8008"
                return result
            
            # Send test document
            print("\n📤 Sending medical document to simple orchestrator...")
            print(f"   Document length: {len(TEST_DOCUMENT)} characters")
            
            response = await self.client.call_agent(
                "http://localhost:8008",
                TEST_DOCUMENT
            )
            
            result["response"] = response
            result["success"] = True
            result["duration"] = time.time() - start_time
            
            # Analyze response
            print("\n📥 Response received!")
            print(f"   Response length: {len(response)} characters")
            print(f"   Duration: {result['duration']:.2f} seconds")
            
            # Show sample of response
            print("\n📄 Response sample (first 500 chars):")
            print("-"*40)
            print(response[:500])
            if len(response) > 500:
                print("...")
            print("-"*40)
            
            # Check for key medical terms in response
            key_terms = ["melanoma", "pembrolizumab", "Eleanor Richardson", "Stage IIIB"]
            found_terms = [term for term in key_terms if term.lower() in response.lower()]
            print(f"\n🔍 Found {len(found_terms)}/{len(key_terms)} key medical terms")
            for term in found_terms:
                print(f"   ✓ {term}")
            
        except Exception as e:
            result["error"] = str(e)
            print(f"\n❌ Error: {e}")
        
        return result
    
    async def test_llm_orchestrator(self) -> Dict[str, Any]:
        """Test the LLM-powered orchestrator."""
        print("\n" + "="*80)
        print("🧪 TESTING LLM-POWERED ORCHESTRATOR")
        print("="*80)
        
        start_time = time.time()
        result = {
            "type": "llm_orchestrator",
            "success": False,
            "response": None,
            "error": None,
            "duration": 0
        }
        
        try:
            # Check if orchestrator is running
            if not await self.check_agent_health("LLM Orchestrator", 8006):
                result["error"] = "LLM orchestrator not running on port 8006"
                return result
            
            # Create a more natural request for the LLM orchestrator
            llm_request = f"""Please analyze this medical document and provide a comprehensive summary 
focusing on the cancer diagnosis, treatment plan, and patient outcomes.

{TEST_DOCUMENT}"""
            
            print("\n📤 Sending medical document to LLM orchestrator...")
            print(f"   Request length: {len(llm_request)} characters")
            
            response = await self.client.call_agent(
                "http://localhost:8006",
                llm_request
            )
            
            result["response"] = response
            result["success"] = True
            result["duration"] = time.time() - start_time
            
            # Analyze response
            print("\n📥 Response received!")
            print(f"   Response length: {len(response)} characters")
            print(f"   Duration: {result['duration']:.2f} seconds")
            
            # Show sample of response
            print("\n📄 Response sample (first 500 chars):")
            print("-"*40)
            print(response[:500])
            if len(response) > 500:
                print("...")
            print("-"*40)
            
            # Check for comprehensive analysis
            analysis_indicators = [
                "diagnosis", "treatment", "pembrolizumab", "Stage IIIB",
                "Eleanor Richardson", "melanoma", "assessment", "plan"
            ]
            found_indicators = [ind for ind in analysis_indicators if ind.lower() in response.lower()]
            print(f"\n🔍 Found {len(found_indicators)}/{len(analysis_indicators)} analysis indicators")
            for indicator in found_indicators:
                print(f"   ✓ {indicator}")
            
        except Exception as e:
            result["error"] = str(e)
            print(f"\n❌ Error: {e}")
        
        return result
    
    def compare_results(self, simple_result: Dict, llm_result: Dict):
        """Compare results from both orchestrators."""
        print("\n" + "="*80)
        print("📊 COMPARISON OF ORCHESTRATORS")
        print("="*80)
        
        # Success rates
        print("\n✅ Success Status:")
        print(f"   Simple Orchestrator: {'✓ Success' if simple_result['success'] else '✗ Failed'}")
        print(f"   LLM Orchestrator:    {'✓ Success' if llm_result['success'] else '✗ Failed'}")
        
        # Performance comparison
        print("\n⏱️  Performance:")
        if simple_result['success']:
            print(f"   Simple Orchestrator: {simple_result['duration']:.2f} seconds")
        if llm_result['success']:
            print(f"   LLM Orchestrator:    {llm_result['duration']:.2f} seconds")
        
        # Response analysis
        print("\n📝 Response Analysis:")
        if simple_result['success'] and simple_result['response']:
            print(f"   Simple Orchestrator response: {len(simple_result['response'])} characters")
        if llm_result['success'] and llm_result['response']:
            print(f"   LLM Orchestrator response:    {len(llm_result['response'])} characters")
        
        # Content quality indicators
        if simple_result['success'] and llm_result['success']:
            print("\n🎯 Content Quality:")
            
            # Check for structured vs narrative
            simple_resp = simple_result['response'] or ""
            llm_resp = llm_result['response'] or ""
            
            # Simple metrics
            simple_lines = simple_resp.count('\n')
            llm_lines = llm_resp.count('\n')
            
            print(f"   Simple Orchestrator: {simple_lines} lines, "
                  f"{'JSON-like' if '{' in simple_resp else 'text'} format")
            print(f"   LLM Orchestrator:    {llm_lines} lines, "
                  f"{'structured' if '1.' in llm_resp or '•' in llm_resp else 'narrative'} format")
        
        # Errors
        if simple_result.get('error') or llm_result.get('error'):
            print("\n⚠️  Errors:")
            if simple_result.get('error'):
                print(f"   Simple Orchestrator: {simple_result['error']}")
            if llm_result.get('error'):
                print(f"   LLM Orchestrator: {llm_result['error']}")
        
        # Summary
        print("\n" + "="*80)
        print("📌 SUMMARY")
        print("="*80)
        
        both_success = simple_result['success'] and llm_result['success']
        if both_success:
            print("✅ Both orchestrators successfully processed the medical document!")
            print("\nKey Differences:")
            print("• Simple Orchestrator: Fast, sequential, predictable pipeline")
            print("• LLM Orchestrator: Intelligent routing, adaptive processing")
        elif simple_result['success']:
            print("⚠️  Only Simple Orchestrator succeeded")
        elif llm_result['success']:
            print("⚠️  Only LLM Orchestrator succeeded")
        else:
            print("❌ Both orchestrators failed - check agent health and logs")


async def main():
    """Main test function."""
    print("\n" + "="*80)
    print("🚀 ORCHESTRATOR COMPARISON TEST")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if agents are running
    print("\n🔍 Checking if required agents are running...")
    print("   (If not, run: python launch_all_agents.py)")
    
    async with OrchestratorTester() as tester:
        # Test both orchestrators
        simple_result = await tester.test_simple_orchestrator()
        await asyncio.sleep(2)  # Brief pause between tests
        llm_result = await tester.test_llm_orchestrator()
        
        # Compare results
        tester.compare_results(simple_result, llm_result)
        
        # Save results to file
        results = {
            "timestamp": datetime.now().isoformat(),
            "simple_orchestrator": simple_result,
            "llm_orchestrator": llm_result
        }
        
        results_file = Path("orchestrator_test_results.json")
        with open(results_file, 'w') as f:
            # Don't save full responses to keep file size manageable
            save_results = results.copy()
            if save_results["simple_orchestrator"]["response"]:
                save_results["simple_orchestrator"]["response_length"] = len(
                    save_results["simple_orchestrator"]["response"]
                )
                save_results["simple_orchestrator"]["response"] = "truncated"
            if save_results["llm_orchestrator"]["response"]:
                save_results["llm_orchestrator"]["response_length"] = len(
                    save_results["llm_orchestrator"]["response"]
                )
                save_results["llm_orchestrator"]["response"] = "truncated"
            
            json.dump(save_results, f, indent=2)
        
        print(f"\n💾 Results saved to: {results_file}")
    
    print("\n✅ Test completed!")


if __name__ == "__main__":
    asyncio.run(main())