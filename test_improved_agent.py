#!/usr/bin/env python3
"""Test script for the improved regulatory compliance agent."""

import asyncio
import sys
import logging

sys.path.insert(0, '.')

from examples.regulatory_compliance_ai_agent import RegulatoryComplianceAIAgent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

async def test_agent():
    """Test the improved regulatory compliance agent."""
    print("=" * 80)
    print("TESTING IMPROVED REGULATORY COMPLIANCE AGENT")
    print("=" * 80)
    
    # Initialize the agent
    agent = RegulatoryComplianceAIAgent()
    
    # Test document with various compliance issues
    test_document = """
    CLINICAL TRIAL PROTOCOL: Phase III COVID-19 Vaccine Study
    
    1. PATIENT DATA MANAGEMENT
    We will collect patient names, dates of birth, medical record numbers, 
    and social security numbers for all participants. This data will be 
    stored in our Excel spreadsheet on a shared drive.
    
    2. DATA SECURITY
    Our system uses industry-standard security practices. We follow 
    best practices for data protection and have password protection 
    on all files.
    
    3. INFORMED CONSENT PROCESS
    All participants will sign our standard consent form before enrollment.
    The form includes information about the study and mentions that 
    participation is voluntary.
    
    4. ELECTRONIC RECORDS SYSTEM
    Study data is captured in our eCRF system. We maintain records of 
    all data entries. System validation is planned for next quarter.
    
    5. AUDIT TRAIL
    Our system tracks changes to data with timestamps showing when 
    changes were made.
    
    6. SAFETY MONITORING
    A Data Safety Monitoring Board will review safety data quarterly.
    Stopping rules: Study will be halted if serious adverse events 
    exceed 10% of participants.
    
    7. INVESTIGATIONAL PRODUCT
    Study drug will be stored at room temperature. Dispensing will be 
    logged in the pharmacy records.
    
    8. PROTOCOL COMPLIANCE
    All sites must follow the protocol. Any deviations should be 
    documented and reported within 30 days.
    
    9. VULNERABLE POPULATIONS
    The study will include pregnant women and children ages 12-17.
    Special protections will be implemented as needed.
    
    10. FDA REPORTING
    Serious adverse events will be reported to FDA within appropriate 
    timelines. Annual reports will be submitted as required.
    """
    
    print("\nTest Document Preview (first 500 chars):")
    print("-" * 40)
    print(test_document[:500] + "...")
    print("-" * 40)
    
    print("\nRunning compliance analysis...")
    print("This may take a moment as the LLM analyzes each finding...\n")
    
    # Process the document
    try:
        response = await agent.process_message(test_document)
        
        print("\n" + "=" * 80)
        print("COMPLIANCE ANALYSIS RESULTS")
        print("=" * 80)
        print(response)
        
        # Check if critical issues were found
        if "CRITICAL" in response:
            print("\n⚠️  CRITICAL COMPLIANCE ISSUES DETECTED!")
        elif "VIOLATION" in response:
            print("\n⚠️  COMPLIANCE VIOLATIONS DETECTED")
        elif "WARNING" in response:
            print("\n⚠️  COMPLIANCE WARNINGS IDENTIFIED")
        else:
            print("\n✅ Document appears compliant")
            
    except Exception as e:
        print(f"\n❌ Error during analysis: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_agent())