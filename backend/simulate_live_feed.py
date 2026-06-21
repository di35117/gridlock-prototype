import time
import requests

WEBHOOK_URL = "http://localhost:8000/api/osint/webhook"

# Upgraded Scenarios with Highly Specific Locations & One City-Wide Edge Case
mock_live_feed = [
    {
        "raw_text": "URGENT: Massive sudden protest forming right at Silk Board Junction. People are blocking the main intersection. Traffic on Outer Ring Road is completely paralyzed. Crowd looks like 3000+ people.",
        "source": "Twitter/X Enterprise Firehose"
    },
    {
        "raw_text": "Traffic Advisory: Major waterlogging and a broken down truck reported at Bellandur Gate. Vehicles are barely moving. Expecting 4-hour delays for IT corridor commuters.",
        "source": "BTP Official Dispatch API"
    },
    {
        "raw_text": "Absolute chaos near MG Road Metro Station! Flash mob of about 500 people has spilled onto the main street blocking all traffic towards Trinity Circle.",
        "source": "Dataminr AI Alert"
    },
    {
        "raw_text": "Massive protests planned across the city tomorrow, everyone stay home! Situation is extremely tense globally.",
        "source": "Twitter/X Enterprise Firehose"
    }
]

print("=====================================================")
print("🚀 Starting BTP Event Command - Live Feed Simulator")
print("=====================================================\n")

for payload in mock_live_feed:
    print(f"📡 [INTERCEPT] Push received from {payload['source']}")
    print(f"   RAW TEXT: \"{payload['raw_text']}\"")
    
    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        if response.status_code == 200:
            print(f"✅ [BACKEND] {response.json().get('message')}\n")
        else:
            print(f"❌ [ERROR] Backend rejected the payload: {response.text}\n")
    except Exception as e:
        print(f"❌ [CRITICAL] Failed to connect to Command Center: {e}\n")
    
    # Wait 15 seconds so the UI camera can finish its 3D sweep before the next alert
    print("⏳ Waiting 15 seconds before next OSINT injection...\n")
    time.sleep(15)

print("🏁 All simulated threat feeds deployed.")