import httpx
import asyncio
import uuid

BASE_URL = "http://localhost:8000"

async def test_workflow():
    print("--- Starting API Integration Test ---")
    
    async with httpx.AsyncClient() as client:
        # 1. Submit Idea
        print("\n1. Testing /api/idea/submit...")
        idea_payload = {
            "idea_text": "A subscription-based specialty coffee delivery service for remote workers.",
            "session_id": str(uuid.uuid4())
        }
        try:
            resp = await client.post(f"{BASE_URL}/api/idea/submit", json=idea_payload)
            print(f"Status: {resp.status_code}")
            data = resp.json()
            session_id = data['session_id']
            print(f"Session ID: {session_id}")
            print(f"Clarification Questions: {len(data['questions'])}")
        except Exception as e:
            print(f"Failed Submit: {e}")
            return

        # 2. Submit Clarifications
        print("\n2. Testing /api/idea/clarify...")
        answers = {q['question_id']: "Global market, high income remote workers, $50k budget." for q in data['questions']}
        clarify_payload = {
            "session_id": session_id,
            "answers": answers
        }
        try:
            resp = await client.post(f"{BASE_URL}/api/idea/clarify", json=clarify_payload)
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.json()['message']}")
        except Exception as e:
            print(f"Failed Clarify: {e}")
            return

        # 3. Get Dashboard Data
        print("\n3. Testing /api/dashboard/{id}...")
        try:
            resp = await client.get(f"{BASE_URL}/api/dashboard/{session_id}")
            print(f"Status: {resp.status_code}")
            dashboard = resp.json()
            if dashboard['plan']:
                print("✅ Business Plan Generated Successfully!")
                print(f"Executive Summary snippet: {dashboard['plan']['executive_summary'][:100]}...")
            else:
                print("❌ Business Plan is empty.")
        except Exception as e:
            print(f"Failed Dashboard: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(test_workflow())
    except Exception as e:
        print(f"Server not reachable? {e}")
