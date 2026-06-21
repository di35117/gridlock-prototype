import time
import requests

# We are hitting /process to force FastAPI to return the exact background error
WEBHOOK_URL = "https://gridlock-prototype-production.up.railway.app/api/osint/process"

mock_live_feed = [
    {
        "raw_text": "URGENT: Massive sudden protest forming right at Silk Board Junction. People are blocking the main intersection. Traffic on Outer Ring Road is completely paralyzed. Crowd looks like 3000+ people.",
        "source": "Twitter/X Enterprise Firehose"
    }
]

print("=====================================================")
print("🚀 BTP Event Command - DIAGNOSTIC MODE")
print("=====================================================\n")

for payload in mock_live_feed:
    print(f"📡 [INTERCEPT] Push received from {payload['source']}")
    
    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        if response.status_code == 200:
            print(f"✅ [SUCCESS] Payload processed perfectly! Check the UI.\n")
        else:
            # THIS WILL PRINT THE EXACT HIDDEN ERROR
            print(f"❌ [CRASH EXPOSED] Status Code {response.status_code}")
            print(f"   Details: {response.text}\n")
    except Exception as e:
        print(f"❌ [CONNECTION ERROR] {e}\n")