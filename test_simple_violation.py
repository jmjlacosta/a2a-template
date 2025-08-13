#!/usr/bin/env python3
"""Test with obvious violations."""

import asyncio
import sys
sys.path.insert(0, '.')

from examples.regulatory_compliance_ai_agent import RegulatoryComplianceAIAgent

async def test():
    agent = RegulatoryComplianceAIAgent()
    
    # Document with VERY obvious violations
    bad_doc = """
    PATIENT DATA: We store all patient SSNs and medical records in plain text files 
    on a public server with no encryption. Patient names and diagnoses are visible 
    to anyone. We have no access controls or audit trails. Anyone can delete or 
    modify patient records without any tracking. We do not use any encryption for 
    data at rest or in transit. Passwords are stored in plain text. We have no 
    user authentication system. Electronic signatures are not validated.
    """
    
    print("Testing with obvious violations:")
    print("-" * 40)
    print(bad_doc)
    print("-" * 40)
    
    response = await agent.process_message(bad_doc)
    print("\nRESULT:")
    print(response)
    
    # Count issues
    lines = response.split('\n')
    issue_count = 0
    for line in lines:
        if 'CRITICAL' in line or 'VIOLATION' in line or 'WARNING' in line:
            issue_count += 1
    
    print(f"\n{'='*40}")
    print(f"Issues detected: {issue_count}")
    if issue_count == 0:
        print("❌ ERROR: No issues detected for obvious violations!")
    else:
        print(f"✅ Correctly detected {issue_count} issues")

if __name__ == "__main__":
    asyncio.run(test())