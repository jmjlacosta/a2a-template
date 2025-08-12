#!/usr/bin/env python3
"""
Test script to verify A2A protocol compliance.
"""

import os
import sys
from base import (
    ComplianceValidator,
    PlatformDetector,
    create_compliant_agent_card
)


def test_compliance():
    """Test A2A compliance features."""
    print("=" * 60)
    print("A2A Protocol Compliance Test")
    print("=" * 60)
    
    # Test platform detection
    print("\n1. Testing Platform Detection...")
    platform = PlatformDetector.detect()
    print(f"   Environment: {platform['environment']}")
    print(f"   Agent URL: {platform['agent_url']}")
    print(f"   HealthUniverse: {platform['is_healthuniverse']}")
    print(f"   Agent ID: {platform['agent_id'] or 'N/A'}")
    
    # Test agent card creation
    print("\n2. Testing AgentCard Creation...")
    agent_card = create_compliant_agent_card(
        name="Test Agent",
        description="A test agent for compliance verification",
        version="1.0.0",
        streaming=True
    )
    
    print(f"   Name: {agent_card.name}")
    print(f"   Description: {agent_card.description}")
    print(f"   Protocol Version: {agent_card.protocol_version}")
    print(f"   URL: {agent_card.url}")
    print(f"   Transport: {agent_card.preferred_transport}")
    print(f"   Provider: {agent_card.provider.organization}")
    
    # Test compliance validation
    print("\n3. Testing Compliance Validation...")
    validator = ComplianceValidator(agent_card, platform['is_healthuniverse'])
    result = validator.validate()
    
    print(f"   {result['summary']}")
    
    if result['errors']:
        print("\n   Errors:")
        for error in result['errors']:
            print(f"   - {error}")
    
    if result['warnings']:
        print("\n   Warnings:")
        for warning in result['warnings']:
            print(f"   - {warning}")
    
    # Test with missing fields
    print("\n4. Testing Validation with Missing Fields...")
    from a2a.types import AgentCard, AgentCapabilities
    
    bad_card = AgentCard(
        name="Bad Agent",
        description="",  # Empty description
        protocol_version="0.2.0",  # Wrong version
        url="",  # Empty URL
        preferred_transport="",  # Empty transport
        version="1.0.0",
        skills=[],
        default_input_modes=[],
        default_output_modes=[],
        capabilities=AgentCapabilities()
    )
    
    validator2 = ComplianceValidator(bad_card, False)
    result2 = validator2.validate()
    
    print(f"   {result2['summary']}")
    print(f"   Found {len(result2['errors'])} errors")
    
    # Final result
    print("\n" + "=" * 60)
    if result['compliant']:
        print("✅ All compliance tests passed!")
    else:
        print("❌ Some compliance tests failed")
        sys.exit(1)
    
    return result['compliant']


if __name__ == "__main__":
    # Set test environment variables
    os.environ["AGENT_ORG"] = "Test Organization"
    os.environ["AGENT_ORG_URL"] = "https://test.example.com"
    os.environ["AGENT_VERSION"] = "1.0.0-test"
    
    # Run tests
    success = test_compliance()
    sys.exit(0 if success else 1)