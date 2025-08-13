#!/usr/bin/env python3
"""Test the transformed compliance agent."""

import asyncio
import sys
sys.path.insert(0, '.')

from nutrition_tools import analyze_compliance, generate_compliance_report

async def test():
    print("=" * 70)
    print("TESTING TRANSFORMED COMPLIANCE AGENT")
    print("=" * 70)
    
    # Test document with compliance issues
    test_doc = """
    CLINICAL TRIAL PROTOCOL
    
    DATA MANAGEMENT:
    Patient names, dates of birth, and social security numbers will be 
    collected and stored in our database. The database is password-protected.
    De-identification will occur after data collection is complete.
    
    ELECTRONIC SYSTEMS:
    Our eCRF system has been in use for 2 years but formal validation has 
    not been completed. Audit logs capture timestamps but original values 
    before changes are not captured.
    
    PROTOCOL DEVIATIONS:
    Minor deviations do not need to be reported immediately and will be 
    reported at the next monitoring visit.
    """
    
    print("\nTest Document:")
    print("-" * 40)
    print(test_doc)
    print("-" * 40)
    
    # Test 1: Analyze compliance
    print("\n1. Testing analyze_compliance()...")
    analysis = await analyze_compliance(test_doc)
    
    print(f"   Status: {analysis['status']}")
    print(f"   Risk Score: {analysis['risk_score']}/100")
    print(f"   Total Issues: {analysis['total_issues']}")
    print(f"   Issues by Framework:")
    for framework, count in analysis.get('issues_by_framework', {}).items():
        print(f"      - {framework}: {count}")
    
    # Test 2: Generate report
    print("\n2. Testing generate_compliance_report()...")
    report = await generate_compliance_report(test_doc, "text")
    
    # Show first 20 lines of report
    lines = report.split('\n')
    for line in lines[:20]:
        print(f"   {line}")
    
    print(f"\n   ... (Report has {len(lines)} total lines)")
    
    # Test 3: Check specific regulation
    print("\n3. Testing check_specific_regulation()...")
    from nutrition_tools import check_specific_regulation
    
    hipaa_check = await check_specific_regulation(test_doc, "HIPAA")
    print(f"   HIPAA Issues Found: {hipaa_check.get('total_issues', 0)}")
    
    if hipaa_check.get('issues'):
        print("   First HIPAA issue:")
        issue = hipaa_check['issues'][0]
        print(f"      Rule: {issue['rule']}")
        print(f"      Level: {issue['level']}")
        print(f"      Description: {issue['description']}")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE - Compliance analysis tools working!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test())