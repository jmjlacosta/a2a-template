#!/usr/bin/env python3
"""
Standalone test for orchestrators with mock agent responses.
This version doesn't require other agents to be running.
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Test document
TEST_DOCUMENT = """
PATIENT: Eleanor Richardson
DATE: March 15, 2024

CHIEF COMPLAINT: Follow-up for melanoma treatment

HISTORY OF PRESENT ILLNESS:
Ms. Richardson is a 68-year-old female with Stage IIIB melanoma diagnosed in January 2024.
"""


class MockOrchestratorAgent:
    """Mock orchestrator that simulates agent calls without network requests."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.call_log = []
    
    async def call_other_agent(self, agent_name: str, message: str, timeout: float = 30.0) -> str:
        """Mock agent call that logs and returns simulated responses."""
        
        # Log the call
        call_info = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "message_length": len(message),
            "message_preview": message[:200] + "..." if len(message) > 200 else message
        }
        self.call_log.append(call_info)
        
        print(f"\n{'='*60}")
        print(f"📤 CALLING: {agent_name}")
        print(f"{'='*60}")
        print(f"Message ({len(message)} chars):")
        print("-"*40)
        print(message[:500] + "..." if len(message) > 500 else message)
        print("-"*40)
        
        # Simulate responses based on agent type
        if agent_name == "keyword":
            response = """
{
  "patterns": [
    "melanoma|cancer|carcinoma|tumor",
    "Stage [IVX]+|T[0-4]N[0-3]M[0-1]",
    "pembrolizumab|Keytruda|immunotherapy",
    "BRAF V600E|mutation",
    "metastatic|metastasis"
  ],
  "focus_areas": ["diagnosis", "staging", "treatment", "mutations"]
}
"""
            
        elif agent_name == "grep":
            response = json.dumps({
                "matches": [
                    {"line_number": 1, "text": "PATIENT: Eleanor Richardson", "pattern": "patient"},
                    {"line_number": 8, "text": "Stage IIIB melanoma diagnosed", "pattern": "melanoma|cancer"},
                    {"line_number": 8, "text": "Stage IIIB melanoma", "pattern": "Stage [IVX]+"}
                ],
                "total_matches": 3
            })
            
        elif agent_name == "chunk":
            response = """
Context extracted:
Lines 6-10:
HISTORY OF PRESENT ILLNESS:
Ms. Richardson is a 68-year-old female with Stage IIIB melanoma diagnosed in January 2024.
She completed her third cycle of pembrolizumab (Keytruda) on March 1, 2024.
"""
            
        elif agent_name == "summarize":
            response = """
MEDICAL SUMMARY:
- Patient: Eleanor Richardson, 68-year-old female
- Primary Diagnosis: Stage IIIB melanoma (BRAF V600E positive)
- Treatment: Pembrolizumab (Keytruda) immunotherapy, currently on cycle 3
- Response: Showing good response to treatment per imaging
- Key Dates: Diagnosed January 2024, latest treatment March 1, 2024
"""
            
        elif agent_name == "temporal_tagging":
            response = json.dumps({
                "dates_found": [
                    {"date": "2024-03-15", "type": "encounter", "context": "Current visit"},
                    {"date": "2024-01", "type": "diagnosis", "context": "melanoma diagnosed"},
                    {"date": "2024-03-01", "type": "treatment", "context": "pembrolizumab cycle"}
                ]
            })
            
        else:
            response = f"Mock response from {agent_name}"
        
        print(f"\n📥 RESPONSE from {agent_name}:")
        print("-"*40)
        print(response[:500] + "..." if len(response) > 500 else response)
        print("-"*40)
        print(f"Response length: {len(response)} chars")
        
        # Simulate network delay
        await asyncio.sleep(0.5)
        
        return response
    
    def print_call_summary(self):
        """Print summary of all agent calls made."""
        print("\n" + "="*60)
        print("📊 CALL SUMMARY")
        print("="*60)
        print(f"Total calls: {len(self.call_log)}")
        print("\nCall sequence:")
        for i, call in enumerate(self.call_log, 1):
            print(f"{i}. {call['agent']:20} - {call['message_length']:6} chars - {call['timestamp']}")


async def test_simple_pipeline():
    """Test the simple orchestrator pipeline logic."""
    
    print("\n" + "="*80)
    print("🧪 TESTING SIMPLE ORCHESTRATOR PIPELINE (STANDALONE)")
    print("="*80)
    
    # Import and modify the orchestrator to use our mock
    from examples.pipeline.simple_orchestrator_agent import SimpleOrchestratorAgent
    
    # Create orchestrator with mocked agent calls
    orchestrator = SimpleOrchestratorAgent()
    mock_agent = MockOrchestratorAgent()
    
    # Replace the call_other_agent method with our mock
    orchestrator.call_other_agent = mock_agent.call_other_agent
    
    # Run the pipeline
    print("\n🚀 Starting pipeline execution...")
    print("="*80)
    
    try:
        result = await orchestrator.execute_pipeline(TEST_DOCUMENT)
        
        print("\n" + "="*80)
        print("✅ PIPELINE COMPLETE")
        print("="*80)
        print("\nFinal result:")
        print(result[:1000] + "..." if len(result) > 1000 else result)
        
        # Print call summary
        mock_agent.print_call_summary()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Still print what calls were made
        mock_agent.print_call_summary()


async def test_cancer_pipeline():
    """Test the cancer summarization pipeline logic."""
    
    print("\n" + "="*80)
    print("🔬 TESTING CANCER SUMMARIZATION PIPELINE (STANDALONE)")
    print("="*80)
    
    # Import and modify the cancer orchestrator
    from examples.pipeline.cancer_summarization_agent import CancerSummarizationAgent
    
    # Create orchestrator with mocked agent calls
    orchestrator = CancerSummarizationAgent()
    mock_agent = MockOrchestratorAgent()
    
    # Replace the call_other_agent method with our mock
    orchestrator.call_other_agent = mock_agent.call_other_agent
    
    # Add mock responses for additional agents
    async def extended_mock_call(agent_name: str, message: str, timeout: float = 30.0) -> str:
        """Extended mock for cancer pipeline agents."""
        
        # Use base mock for common agents
        if agent_name in ["keyword", "grep", "chunk", "summarize", "temporal_tagging"]:
            return await mock_agent.call_other_agent(agent_name, message, timeout)
        
        # Add responses for cancer pipeline specific agents
        if agent_name == "encounter_grouping":
            return json.dumps({
                "encounters": [
                    {"date": "2024-03-15", "type": "follow-up", "content": "Current visit"},
                    {"date": "2024-01-15", "type": "diagnosis", "content": "Initial diagnosis"}
                ]
            })
        elif agent_name == "reconciliation":
            return "Reconciled data: All temporal conflicts resolved"
        elif agent_name == "summary_extractor":
            return "Structured summary: Stage IIIB melanoma, on immunotherapy"
        elif agent_name == "timeline_builder":
            return "Timeline: Jan 2024 (diagnosis) -> Mar 2024 (cycle 3)"
        elif agent_name == "checker":
            return "No issues found - data is consistent"  # Will pass on first try
        elif agent_name == "unified_extractor":
            return json.dumps({"medications": ["pembrolizumab"], "conditions": ["melanoma"]})
        elif agent_name == "unified_verifier":
            return "Verification complete: All data validated"
        elif agent_name == "narrative_synthesis":
            return "NARRATIVE: Patient with Stage IIIB melanoma responding to immunotherapy..."
        else:
            return f"Mock response from {agent_name}"
    
    orchestrator.call_other_agent = extended_mock_call
    
    print("\n🚀 Starting cancer pipeline execution...")
    print("="*80)
    
    try:
        result = await orchestrator.execute_pipeline(TEST_DOCUMENT)
        
        print("\n" + "="*80)
        print("✅ CANCER PIPELINE COMPLETE")
        print("="*80)
        print("\nFinal result:")
        print(result[:1000] + "..." if len(result) > 1000 else result)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n🔧 Orchestrator Standalone Test")
    print("This tests orchestrators without requiring other agents to be running.\n")
    
    # Test simple orchestrator
    asyncio.run(test_simple_pipeline())
    
    print("\n" + "="*80)
    print("Waiting 2 seconds before next test...")
    print("="*80)
    import time
    time.sleep(2)
    
    # Test cancer orchestrator
    asyncio.run(test_cancer_pipeline())
    
    print("\n✅ All standalone tests complete!")