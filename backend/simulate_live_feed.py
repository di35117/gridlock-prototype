import time
import requests
import json

WEBHOOK_URL = "http://localhost:8000/api/osint/webhook"

mock_live_feed = [
    {
        "raw_text": "Traffic Advisory: BTP expects a massive political gathering tomorrow evening around 6 PM. Anticipated crowd is roughly 15,000 people.",
        "source": "BTP Official Dispatch API"
    },
    {
        "raw_text": "RCB is 5 runs away from winning! People are absolutely flooding out of pubs heading towards CBD! Crowd looks like 40,000! Absolute chaos.",
        "source": "Twitter/X Enterprise Firehose"
    }
]

print("Starting Autonomous OSINT Feed Simulator...")
print("This script simulates an enterprise social listening tool pushing webhooks to your backend.\n")

for payload in mock_live_feed:
    print(f"Pushing live intel from {payload['source']}...")
    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        print(f"Backend Response: {response.json()['message']}\n")
    except Exception as e:
        print(f"Error connecting to backend: {e}")
    
    # Wait 10 seconds before pushing the next "live" event
    time.sleep(10)

print("Simulation complete.")