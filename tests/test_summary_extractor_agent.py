#!/usr/bin/env python3
"""
Test script for summary_extractor_agent
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Make sure we have the API key
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', '')

async def test_summary_extractor():
    """Test the summary extractor agent."""
    
    print("🧪 TESTING SUMMARY EXTRACTOR AGENT")
    print("="*60)
    
    try:
        from utils.a2a_client import A2AAgentClient
        
        test_message = """Extract a structured summary from this medical report:

PATIENT: Sarah Johnson, DOB: 03/12/1975, MRN: 123456

CHIEF COMPLAINT: Shortness of breath and chest pain

HISTORY OF PRESENT ILLNESS:
Patient is a 48-year-old female presenting with a 3-day history of progressive shortness of breath and substernal chest pain. The chest pain is described as sharp, worse with inspiration, and associated with mild cough. She denies fever, chills, or sputum production.

PAST MEDICAL HISTORY:
- Hypertension (diagnosed 2018)
- Type 2 diabetes mellitus (diagnosed 2020)
- Previous myocardial infarction (2019)

CURRENT MEDICATIONS:
- Lisinopril 10mg daily
- Metformin 1000mg twice daily
- Aspirin 81mg daily
- Atorvastatin 40mg daily

PHYSICAL EXAMINATION:
- Vital signs: BP 145/92, HR 98, RR 22, O2 sat 94% on room air
- Heart: Regular rate and rhythm, no murmurs
- Lungs: Decreased breath sounds at right base, dullness to percussion
- Extremities: No edema

DIAGNOSTIC STUDIES:
- Chest X-ray: Right pleural effusion
- EKG: Normal sinus rhythm, no acute changes
- BNP: 450 pg/mL (elevated)

ASSESSMENT AND PLAN:
1. Right pleural effusion - likely cardiac etiology given elevated BNP and history of MI
   - Diuresis with furosemide 40mg daily
   - Echocardiogram to assess cardiac function
   - Follow-up in 1 week

2. Hypertension - poorly controlled
   - Increase lisinopril to 20mg daily

3. Diabetes - continue current regimen

Please extract key clinical findings, diagnoses, treatments, and outcomes from this report."""
        
        async with A2AAgentClient(timeout=60) as client:
            print("Sending test message with medical report...")
            response = await client.call_agent("http://localhost:8013", test_message)
            print(f"✅ Response received: {len(response)} characters")
            print("\nResponse:")
            print("-"*40)
            print(response)
            print("-"*40)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("SUMMARY EXTRACTOR AGENT TEST")
    print("="*60)
    print(f"OpenAI API Key present: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
    print("="*60 + "\n")
    
    asyncio.run(test_summary_extractor())