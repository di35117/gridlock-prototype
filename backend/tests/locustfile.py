from locust import HttpUser, task, between
import random

class BTPTrafficSimulator(HttpUser):
    # Simulates a new request every 1 to 3 seconds per virtual user
    wait_time = between(1, 3)

    @task(3)  # This task runs 3x more often (simulating high CCTV volume)
    def simulate_cctv_ping(self):
        corridors = ["Mysore Road", "ORR East", "Silk Board", "Hebbal Flyover"]
        payload = {
            "corridor": random.choice(corridors),
            "event_cause": "vehicle_breakdown",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "veh_type": random.choice(["heavy_vehicle", "two_wheeler", "car"])
        }
        # Hitting your CCTV webhook
        self.client.post("/api/cctv/webhook", json=payload)

    @task(1)  # Simulating periodic surge checks
    def simulate_surge_check(self):
        payload = {
            "corridor": "Silk Board",
            "current_hourly_incidents": random.randint(5, 25)
        }
        self.client.post("/api/surge/check", json=payload)
    @task(2) # Runs fairly frequently
    def simulate_compound_conflict_ping(self):
        corridors = ["Mysore Road", "ORR East", "Silk Board", "Hebbal Flyover"]
        causes = ["protest", "vehicle_breakdown", "accident", "construction"]
        
        payload = {
            "corridor": random.choice(corridors),
            "event_cause": random.choice(causes)
        }
        # Hammers the new compound conflict endpoint
        self.client.post("/api/conflict/detect", json=payload)