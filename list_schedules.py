import requests
import json

URL = "https://haibot.vercel.app/api/task-schedules"
USER_ID = "3fcd974b-e68e-4e34-b86a-21ecfdab3356"

print(f"Fetching schedules for User ID: {USER_ID}...")
try:
    resp = requests.get(URL, params={"user_id": USER_ID})
    resp.raise_for_status()
    data = resp.json()
    
    schedules = data.get("data", [])
    print(f"\nFound {len(schedules)} schedules:\n")
    
    for s in schedules:
        print(f"ID: {s.get('id')}")
        print(f"Task: {s.get('task', {}).get('name', 'Unknown')}")
        print(f"Time: {s.get('scheduled_time')}")
        print(f"Priority: {s.get('priority')}")
        print(f"Recurring: {s.get('recurring')}")
        print("-" * 40)
        
except Exception as e:
    print(f"Error: {e}")
