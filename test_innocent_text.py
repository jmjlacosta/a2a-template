#!/usr/bin/env python3
"""Test with innocent clinical text."""

import asyncio
import sys
sys.path.insert(0, '.')

from examples.regulatory_compliance_ai_agent import RegulatoryComplianceAIAgent

async def test():
    agent = RegulatoryComplianceAIAgent()
    
    # Completely innocent clinical protocol text
    innocent_doc = """
    CLINICAL TRIAL PROTOCOL: Phase III Diabetes Management Study
    
    1. STUDY OBJECTIVES
    The primary objective is to evaluate the efficacy of the new diabetes 
    management system in improving glycemic control. Secondary objectives include 
    assessing quality of life improvements and treatment adherence.
    
    2. PATIENT MONITORING
    Participants will undergo regular monitoring including:
    - Blood glucose monitoring twice daily
    - HbA1c levels measured every 3 months
    - Blood pressure and vital signs at each visit
    - Continuous glucose monitoring for selected participants
    - Quality control assurance for all laboratory measurements
    
    3. DATA COLLECTION
    Clinical data will be collected using validated instruments. All adverse 
    events will be documented and reported according to protocol. The study 
    coordinator will ensure proper documentation of all clinical assessments.
    
    4. STATISTICAL ANALYSIS
    The primary endpoint will be analyzed using mixed-effects models to account 
    for repeated measures. Sample size calculations indicate 200 participants 
    are needed for 80% power to detect clinically meaningful differences.
    
    5. ETHICAL CONSIDERATIONS
    The study has been approved by the institutional review board. All 
    participants will provide written informed consent before enrollment. 
    Vulnerable populations including pregnant women will be excluded.
    """
    
    print("Testing with innocent clinical text:")
    print("-" * 40)
    print(innocent_doc[:500] + "...")
    print("-" * 40)
    
    response = await agent.process_message(innocent_doc)
    
    # Count issues
    lines = response.split('\n')
    total_issues = 0
    for line in lines:
        if line.startswith("Total Issues Found:"):
            parts = line.split(":")
            if len(parts) > 1:
                try:
                    total_issues = int(parts[1].strip().split()[0])
                except:
                    pass
            break
    
    print(f"\n{'='*40}")
    print(f"Issues detected: {total_issues}")
    if total_issues > 0:
        print(f"❌ ERROR: {total_issues} false positives detected!")
        print("\nFull report:")
        print(response)
    else:
        print("✅ SUCCESS: No false positives!")

if __name__ == "__main__":
    asyncio.run(test())