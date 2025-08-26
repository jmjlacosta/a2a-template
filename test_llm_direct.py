import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.llm_utils import generate_text

async def test():
    prompt = "Generate a simple JSON object with 'name' and 'age' fields. Return ONLY valid JSON, no markdown."
    print("Testing LLM with prompt:", prompt)
    response = await generate_text(
        prompt=prompt,
        temperature=0.3,
        max_tokens=100
    )
    print("\nLLM Response:")
    print(repr(response))
    print("\nFormatted:")
    print(response)

if __name__ == "__main__":
    asyncio.run(test())