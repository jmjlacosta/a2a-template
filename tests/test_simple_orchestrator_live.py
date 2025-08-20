#!/usr/bin/env python3
"""
Live test script for Simple Orchestrator with detailed logging.
Shows exactly what's being sent to each agent and what comes back.
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import our orchestrator
from examples.pipeline.simple_orchestrator_agent import SimpleOrchestratorAgent

# Test document (Eleanor Richardson)
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


async def test_orchestrator_with_logging():
    """Test the orchestrator with detailed logging of all agent communications."""
    
    print("="*80)
    print("🚀 SIMPLE ORCHESTRATOR LIVE TEST")
    print("="*80)
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📄 Document length: {len(TEST_DOCUMENT)} characters")
    print("="*80)
    
    # Create orchestrator instance
    print("\n📦 Creating SimpleOrchestratorAgent instance...")
    orchestrator = SimpleOrchestratorAgent()
    
    print(f"✅ Agent name: {orchestrator.get_agent_name()}")
    print(f"✅ Streaming enabled: {orchestrator.supports_streaming()}")
    print(f"✅ Number of tools: {len(orchestrator.get_tools())}")
    
    # Test the pipeline execution directly
    print("\n" + "="*80)
    print("🔄 EXECUTING PIPELINE DIRECTLY (without LLM)")
    print("="*80)
    
    try:
        # Call the execute_pipeline method directly to see the actual pipeline logic
        result = await orchestrator.execute_pipeline(TEST_DOCUMENT)
        
        print("\n" + "="*80)
        print("✅ PIPELINE COMPLETE")
        print("="*80)
        print("\n📊 Final Result:")
        print("-"*40)
        
        # Try to parse and pretty-print if it's JSON
        try:
            result_json = json.loads(result)
            print(json.dumps(result_json, indent=2))
        except:
            # If not JSON, just print as-is
            print(result[:2000] + "..." if len(result) > 2000 else result)
        
        print("\n📏 Result length: {} characters".format(len(result)))
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("🏁 TEST COMPLETE")
    print("="*80)


async def test_individual_agent_calls():
    """Test calling agents individually to debug."""
    
    print("\n" + "="*80)
    print("🔍 TESTING INDIVIDUAL AGENT CALLS")
    print("="*80)
    
    orchestrator = SimpleOrchestratorAgent()
    
    # Test 1: Keyword Agent
    print("\n📍 Test 1: Calling Keyword Agent directly")
    print("-"*40)
    
    keyword_message = f"""Generate regex patterns for finding medical information in this document:

{TEST_DOCUMENT[:1000]}

Generate comprehensive patterns for all medical information."""
    
    print(f"📤 Message preview: {keyword_message[:200]}...")
    
    try:
        # Note: This will fail if agents aren't running, but shows what would be sent
        response = await orchestrator.call_other_agent("keyword", keyword_message)
        print(f"📥 Response: {response[:500]}...")
    except Exception as e:
        print(f"⚠️ Could not reach keyword agent: {e}")
        print("   (This is expected if the agent isn't running)")
    
    # Test 2: Direct pattern extraction
    print("\n📍 Test 2: Testing pattern extraction logic")
    print("-"*40)
    
    sample_keyword_response = """
    Found patterns:
    "melanoma|cancer|carcinoma"
    "pembrolizumab|Keytruda|immunotherapy"
    Pattern: Stage [IVX]+
    Pattern: BRAF V600E
    """
    
    patterns = orchestrator._extract_patterns(sample_keyword_response)
    print(f"📋 Extracted {len(patterns)} patterns:")
    for i, pattern in enumerate(patterns[:5], 1):
        print(f"   {i}. {pattern}")


def create_notebook_version():
    """Create a Jupyter notebook version of this test."""
    
    notebook_content = """
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Simple Orchestrator Live Test\\n",
    "This notebook lets you test the simple orchestrator and see exactly what's being sent to each agent."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import sys\\n",
    "from pathlib import Path\\n",
    "import json\\n",
    "import asyncio\\n",
    "from datetime import datetime\\n",
    "\\n",
    "# Add parent directory to path\\n",
    "sys.path.insert(0, str(Path('.').absolute()))\\n",
    "\\n",
    "# Import orchestrator\\n",
    "from examples.pipeline.simple_orchestrator_agent import SimpleOrchestratorAgent"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Test Document"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "TEST_DOCUMENT = '''\\n",
    "PATIENT: Eleanor Richardson\\n",
    "DATE: March 15, 2024\\n",
    "\\n",
    "CHIEF COMPLAINT: Follow-up for melanoma treatment\\n",
    "\\n",
    "HISTORY OF PRESENT ILLNESS:\\n",
    "Ms. Richardson is a 68-year-old female with Stage IIIB melanoma diagnosed in January 2024.\\n",
    "She completed her third cycle of pembrolizumab (Keytruda) on March 1, 2024.\\n",
    "\\n",
    "CURRENT MEDICATIONS:\\n",
    "- Pembrolizumab 200mg IV q3 weeks\\n",
    "- Metformin 1000mg BID\\n",
    "- Lisinopril 10mg daily\\n",
    "'''\\n",
    "\\n",
    "print(f'Document length: {len(TEST_DOCUMENT)} characters')"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Create Orchestrator Instance"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "orchestrator = SimpleOrchestratorAgent()\\n",
    "\\n",
    "print(f'Agent: {orchestrator.get_agent_name()}')\\n",
    "print(f'Streaming: {orchestrator.supports_streaming()}')\\n",
    "print(f'Tools: {len(orchestrator.get_tools())}')"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Test Pipeline Execution"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Run the pipeline\\n",
    "result = await orchestrator.execute_pipeline(TEST_DOCUMENT)\\n",
    "\\n",
    "print('Pipeline complete!')\\n",
    "print(f'Result length: {len(result)} characters')\\n",
    "print('\\\\nFirst 500 characters:')\\n",
    "print(result[:500])"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Test Pattern Extraction"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Test the pattern extraction logic\\n",
    "sample_response = '''\\n",
    "Patterns found:\\n",
    "\\"melanoma|cancer\\"\\n",
    "\\"Stage [IVX]+\\"\\n",
    "Pattern: pembrolizumab\\n",
    "'''\\n",
    "\\n",
    "patterns = orchestrator._extract_patterns(sample_response)\\n",
    "print(f'Extracted {len(patterns)} patterns:')\\n",
    "for p in patterns:\\n",
    "    print(f'  - {p}')"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "name": "python",
   "version": "3.10.0"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
"""
    
    with open("test_simple_orchestrator.ipynb", "w") as f:
        f.write(notebook_content)
    
    print("📓 Created test_simple_orchestrator.ipynb")


if __name__ == "__main__":
    print("\n🔧 Simple Orchestrator Live Test\n")
    print("This script will test the orchestrator and show all agent communications.\n")
    
    # Create notebook version
    create_notebook_version()
    
    # Run tests
    print("Running tests...\n")
    
    # Test the orchestrator
    asyncio.run(test_orchestrator_with_logging())
    
    # Test individual agent calls
    asyncio.run(test_individual_agent_calls())
    
    print("\n✅ All tests complete!")
    print("📓 Also created test_simple_orchestrator.ipynb for Jupyter testing")