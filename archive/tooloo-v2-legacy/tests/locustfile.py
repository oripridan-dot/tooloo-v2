from locust import HttpUser, task, between

class TooLooUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def health_check(self):
        self.client.get("/v2/introspector/pulse")

    @task(3)
    def submit_mandate(self):
        # Simulate a mandate
        self.client.post("/v2/mandate", json={
            "mandate": "Evaluate system stability",
            "dry_run": True,
            "session_id": "locust-perf-test"
        })
        
    @task(2)
    def check_roadmap(self):
        self.client.get("/v2/roadmap")
