#!/usr/bin/env python3
"""
Test script for the orchestrator agent with medical text.
"""

import asyncio
import json
import httpx

async def test_orchestrator():
    """Test the orchestrator with medical text."""
    
    # Read the test medical text
    with open('test.txt', 'r') as f:
        medical_text = f.read()
    
    # Prepare the request
    request_data = {
        "message": json.dumps({
            "file_content": medical_text,
            "file_path": "medical_record.txt",
            "request": "Find all information about the patient's cardiac condition, current medications, and provide a clinical summary",
            "focus_areas": ["cardiac", "medications", "diagnosis", "treatment"],
            "document_type": "emergency_department_note"
        })
    }
    
    orchestrator_url = "http://localhost:8006/v1/message"
    
    print("🚀 Sending request to orchestrator...")
    print(f"📋 Request: Analyze cardiac condition and medications")
    print(f"📄 Document length: {len(medical_text)} characters")
    print("-" * 60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(orchestrator_url, json=request_data)
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Response received from orchestrator:")
                print(json.dumps(result, indent=2))
            else:
                print(f"❌ Error: {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"❌ Error calling orchestrator: {e}")

if __name__ == "__main__":
    asyncio.run(test_orchestrator())