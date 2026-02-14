
import httpx
import asyncio
import json

async def test():
    async with httpx.AsyncClient(timeout=60) as client:
        # Test Text Endpoint
        print("Testing Text Verification...")
        try:
            response = await client.post(
                "http://localhost:8000/api/verify/text",
                json={"text": "Drinking bleach cures COVID-19."}
            )
            print(json.dumps(response.json(), indent=2))
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
