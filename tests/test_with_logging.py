#!/usr/bin/env python3
"""
Test orchestrator with detailed logging to see inter-agent communication.
"""

import asyncio
import json
import logging
import uuid
import httpx

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set specific loggers to INFO/DEBUG
logging.getLogger("OrchestratorAgent").setLevel(logging.INFO)
logging.getLogger("utils.a2a_client").setLevel(logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.WARNING)  # Reduce noise from httpx

async def test_orchestrator_with_logging():
    """Test the orchestrator and see what it sends to other agents."""
    
    # Create JSON-RPC request
    request_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())
    
    test_message = """Mrs. Eleanor Richardson, a 68-year-old retired elementary school teacher, presented to the emergency department at 3:47 AM on Tuesday morning with complaints of severe chest pain radiating to her left arm, accompanied by shortness of breath, diaphoresis, and nausea that had begun approximately two hours prior while she was sleeping. Her medical history is significant for type 2 diabetes mellitus diagnosed twelve years ago, currently managed with metformin 1000mg twice daily and glipizide 5mg once daily, hypertension controlled with lisinopril 20mg daily and hydrochlorothiazide 25mg daily, hyperlipidemia treated with atorvastatin 40mg at bedtime, and mild osteoarthritis affecting both knees for which she takes acetaminophen as needed. She underwent a total abdominal hysterectomy in 1998 for uterine fibroids and had her gallbladder removed laparoscopically in 2015 due to symptomatic cholelithiasis. Her family history is notable for coronary artery disease in her father who suffered a myocardial infarction at age 72, her mother who had a stroke at age 81, and a younger brother currently being treated for atrial fibrillation. Mrs. Richardson is a former smoker with a 20-pack-year history, having quit 15 years ago, drinks wine socially approximately twice per month, and denies any illicit drug use. She lives independently in a two-story home with her husband of 45 years, remains physically active by walking her golden retriever twice daily for approximately 30 minutes each time, participates in a weekly water aerobics class at the local YMCA, and maintains an active social life through her church community and a monthly book club. Her current medications also include a daily multivitamin, calcium carbonate 600mg with vitamin D 400 IU twice daily for bone health, and she recently started taking turmeric supplements after reading about their anti-inflammatory properties, though she couldn't recall the exact dosage. She reports excellent medication compliance, checking her blood glucose levels twice daily with readings typically ranging from 110-140 mg/dL fasting and 140-180 mg/dL postprandial, and maintains regular follow-up appointments with her primary care physician every three months, her endocrinologist twice yearly, and her ophthalmologist annually for diabetic retinopathy screening, with her most recent eye exam three months ago showing no evidence of retinopathy. On initial examination, she appeared anxious and uncomfortable, sitting upright on the gurney clutching her chest, with vital signs revealing blood pressure of 165/95 mmHg, heart rate of 110 beats per minute and irregular, respiratory rate of 24 breaths per minute, oxygen saturation of 92% on room air, and temperature of 98.6°F, while physical examination demonstrated jugular venous distension, bilateral basilar crackles on lung auscultation, and trace pedal edema, prompting immediate initiation of cardiac workup including serial troponins, comprehensive metabolic panel, complete blood count, brain natriuretic peptide, electrocardiogram showing ST-segment elevations in leads II, III, and aVF consistent with inferior wall myocardial infarction, and urgent cardiology consultation for probable percutaneous coronary intervention."""
    
    jsonrpc_request = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": message_id,
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": test_message
                    }
                ]
            }
        },
        "id": request_id
    }
    
    orchestrator_url = "http://localhost:8006/"
    
    print("=" * 80)
    print("🚀 TESTING ORCHESTRATOR WITH DETAILED LOGGING")
    print("=" * 80)
    print(f"\n📝 Original Message to Orchestrator:")
    print(f"   {test_message}")
    print("\n" + "=" * 80)
    print("📡 INTER-AGENT COMMUNICATION LOGS:")
    print("=" * 80 + "\n")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            # This will trigger the orchestrator to call other agents
            # Watch the logs to see what it sends!
            response = await client.post(
                orchestrator_url, 
                json=jsonrpc_request,
                headers={"Content-Type": "application/json"}
            )
            
            print("\n" + "=" * 80)
            print("✅ FINAL RESPONSE FROM ORCHESTRATOR:")
            print("=" * 80)
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract text from response
                if "result" in result and "artifacts" in result["result"]:
                    artifacts = result["result"]["artifacts"]
                    if artifacts and len(artifacts) > 0:
                        artifact = artifacts[0]
                        if "parts" in artifact and len(artifact["parts"]) > 0:
                            text = artifact["parts"][0].get("text", "No text")
                            print(f"\n{text[:1000]}..." if len(text) > 1000 else f"\n{text}")
                else:
                    print(json.dumps(result, indent=2)[:500])
            else:
                print(f"❌ Error: {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("\n⚠️  NOTE: This will show detailed logs of what the orchestrator sends to other agents.")
    print("   Watch for lines with '📤 Calling agent' and '📤 Sending JSON-RPC request'\n")
    
    asyncio.run(test_orchestrator_with_logging())