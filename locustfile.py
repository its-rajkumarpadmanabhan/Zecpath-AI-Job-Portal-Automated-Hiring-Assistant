# locustfile.py
from locust import HttpUser, task, between


class RecruitmentPlatformUser(HttpUser):
    wait_time = between(1, 2)

    @task(3)
    def test_health_stress(self):
        self.client.get("/api/load-test/ping/")

    @task(1)
    def test_public_jobs(self):
        self.client.get("/api/jobs/public/")
