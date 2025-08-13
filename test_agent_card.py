#!/usr/bin/env python3
"""Test agent card endpoint."""

import httpx
import json
import asyncio
import time
import subprocess
import sys

async def test_agent_card():
    # Start the server in background
    print("Starting compliance agent server...")
    process = subprocess.Popen(
        [sys.executable, "nutrition_example.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    print("Waiting for server to start...")
    await asyncio.sleep(3)
    
    try:
        async with httpx.AsyncClient() as client:
            # Test agent card endpoint
            print("\nTesting /.well-known/agent-card.json...")
            try:
                response = await client.get("http://localhost:8003/.well-known/agent-card.json")
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    card = response.json()
                    print(f"Agent Name: {card.get('name')}")
                    print(f"Version: {card.get('version')}")
                    print(f"Description: {card.get('description')[:100]}...")
                    print(f"Skills: {len(card.get('skills', []))}")
                else:
                    print(f"Error: {response.text}")
            except Exception as e:
                print(f"Error accessing agent card: {e}")
            
            # Test alternative endpoint
            print("\nTesting /agent.json...")
            try:
                response = await client.get("http://localhost:8003/agent.json")
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    print("✅ Alternative endpoint works!")
            except Exception as e:
                print(f"Error: {e}")
                
            # Test health endpoint
            print("\nTesting /health...")
            try:
                response = await client.get("http://localhost:8003/health")
                print(f"Status: {response.status_code}")
                print(f"Response: {response.text}")
            except Exception as e:
                print(f"Error: {e}")
                
    finally:
        # Stop the server
        print("\nStopping server...")
        process.terminate()
        process.wait()

if __name__ == "__main__":
    asyncio.run(test_agent_card())