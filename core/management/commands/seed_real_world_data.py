import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import User, Candidate, Employer, Job, Application, AICall
from core.utils.ai_call_engine import trigger_ai_call
from core.utils.automation_engine import evaluate_and_apply_auto_action


class Command(BaseCommand):
    help = "Seeds the Zecpath hiring assistant database with realistic real-world production data."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting database seeding with real-world data..."))

        # 1. Real-world Recruiters / Employers
        employers_data = [
            {
                "email": "sarah.jenkins@nexustech.io",
                "name": "Sarah Jenkins",
                "company_name": "Nexus Cloud Technologies",
                "website": "https://nexustech.io",
                "domain": "Cloud Infrastructure & AI",
                "company_size": "250-500 employees",
            },
            {
                "email": "m.chen@quantumsystems.com",
                "name": "Michael Chen",
                "company_name": "Quantum AI Systems",
                "website": "https://quantumsystems.com",
                "domain": "Artificial Intelligence & Fintech",
                "company_size": "500-1000 employees",
            },
            {
                "email": "e.rodriguez@apexhealth.org",
                "name": "Elena Rodriguez",
                "company_name": "Apex Digital Health",
                "website": "https://apexhealth.org",
                "domain": "Healthcare SaaS",
                "company_size": "100-250 employees",
            }
        ]

        employer_users = []
        for emp_info in employers_data:
            user, created = User.objects.get_or_create(
                email=emp_info["email"],
                defaults={
                    "name": emp_info["name"],
                    "role": "recruiter",
                    "is_active": True,
                    "is_verified": True
                }
            )
            if created:
                user.set_password("ZecpathRecruiter2026!")
                user.save()

            Employer.objects.get_or_create(
                user=user,
                defaults={
                    "company_name": emp_info["company_name"],
                    "website": emp_info["website"],
                    "domain": emp_info["domain"],
                    "company_size": emp_info["company_size"],
                    "is_verified": True
                }
            )
            employer_users.append(user)
            self.stdout.write(f"  [+] Employer: {user.name} ({emp_info['company_name']})")

        # 2. Real-world Job Postings
        jobs_data = [
            {
                "employer": employer_users[0],
                "title": "Senior AI Infrastructure & Backend Engineer",
                "company": "Nexus Cloud Technologies",
                "description": (
                    "We are seeking an experienced Senior AI Infrastructure & Backend Engineer to build high-throughput "
                    "distributed pipelines, real-time AI model orchestrations, and REST/gRPC microservices. You will work with "
                    "Python, Django, FastAPI, Celery, Redis, PostgreSQL, and Kubernetes to handle low-latency candidate AI screening calls."
                ),
                "skills_required": "Python, Django, FastAPI, Celery, Redis, PostgreSQL, Docker, Kubernetes, WebSockets",
                "experience_required": "4-6 years",
                "salary_min": 140000.00,
                "salary_max": 180000.00,
                "location": "San Francisco, CA (Hybrid)",
                "job_type": "full_time",
                "status": "active"
            },
            {
                "employer": employer_users[1],
                "title": "Lead Full-Stack React & Python Developer",
                "company": "Quantum AI Systems",
                "description": (
                    "Join Quantum AI Systems as a Lead Full-Stack Engineer driving frontend and backend architectures. "
                    "Responsible for designing responsive dashboards, building real-time metrics, integrating AI automated "
                    "voice agents, and optimizing database queries for high concurrency."
                ),
                "skills_required": "React, TypeScript, Next.js, Python, Django, REST API, GraphQL, PostgreSQL, TailwindCSS",
                "experience_required": "5+ years",
                "salary_min": 150000.00,
                "salary_max": 195000.00,
                "location": "New York, NY (Remote)",
                "job_type": "full_time",
                "status": "active"
            },
            {
                "employer": employer_users[2],
                "title": "DevOps & Cloud Site Reliability Engineer",
                "company": "Apex Digital Health",
                "description": (
                    "Apex Digital Health is looking for a DevOps/SRE Engineer to maintain 99.99% uptime across multi-region "
                    "AWS infrastructure. Experience with Terraform, CI/CD pipelines, Prometheus monitoring, and container security is required."
                ),
                "skills_required": "AWS, Docker, Kubernetes, Terraform, CI/CD, Python, Linux, Bash, Prometheus, Grafana",
                "experience_required": "3-5 years",
                "salary_min": 130000.00,
                "salary_max": 165000.00,
                "location": "Austin, TX (Remote)",
                "job_type": "remote",
                "status": "active"
            }
        ]

        jobs = []
        for j_info in jobs_data:
            job, _ = Job.objects.get_or_create(
                title=j_info["title"],
                company=j_info["company"],
                employer=j_info["employer"],
                defaults=j_info
            )
            jobs.append(job)
            self.stdout.write(f"  [+] Job Posting: {job.title}")

        # 3. Real-world Candidates
        candidates_data = [
            {
                "email": "alex.rivera@devmail.org",
                "name": "Alex Rivera",
                "skills": "Python, Django, FastAPI, Celery, Redis, PostgreSQL, Docker, Kubernetes, REST API, Git",
                "education": "B.S. in Computer Science - UC Berkeley (2020)",
                "experience": "5 years software engineering experience building scalable backend services and Celery task queues.",
                "expected_salary": 160000.00,
                "ats_scores": [92.5, 88.0, 72.0]
            },
            {
                "email": "priya.sharma@techhub.net",
                "name": "Priya Sharma",
                "skills": "React, TypeScript, Next.js, JavaScript, Python, Django, REST API, HTML5, CSS3, TailwindCSS",
                "education": "M.S. in Software Engineering - Carnegie Mellon University (2021)",
                "experience": "4 years building modern web applications, state management, and real-time candidate pipelines.",
                "expected_salary": 155000.00,
                "ats_scores": [78.0, 94.0, 65.0]
            },
            {
                "email": "david.kowalski@cloudnet.io",
                "name": "David Kowalski",
                "skills": "AWS, Docker, Kubernetes, Terraform, Python, Linux, Bash, CI/CD, Prometheus, Grafana",
                "education": "B.S. in Information Technology - UT Austin (2019)",
                "experience": "6 years managing multi-cloud Kubernetes clusters, automated infrastructure deployments, and site reliability.",
                "expected_salary": 165000.00,
                "ats_scores": [68.0, 70.0, 96.0]
            },
            {
                "email": "jessica.taylor@codestudio.com",
                "name": "Jessica Taylor",
                "skills": "Java, Spring Boot, SQL, Git, Linux, Microservices, JUnit",
                "education": "B.S. in Computer Engineering - Georgia Tech (2022)",
                "experience": "3 years backend Java development and relational database management.",
                "expected_salary": 120000.00,
                "ats_scores": [45.0, 52.0, 58.0]
            }
        ]

        for cand_info in candidates_data:
            user, created = User.objects.get_or_create(
                email=cand_info["email"],
                defaults={
                    "name": cand_info["name"],
                    "role": "candidate",
                    "is_active": True
                }
            )
            if created:
                user.set_password("ZecpathCandidate2026!")
                user.save()

            Candidate.objects.get_or_create(
                user=user,
                defaults={
                    "skills": cand_info["skills"],
                    "education": cand_info["education"],
                    "experience": cand_info["experience"],
                    "expected_salary": cand_info["expected_salary"],
                    "is_deleted": False
                }
            )
            self.stdout.write(f"  [+] Candidate Profile: {user.name} ({user.email})")

            # 4. Create Applications & Evaluate AI Call Eligibility
            for idx, job in enumerate(jobs):
                score = cand_info["ats_scores"][idx]
                app, app_created = Application.objects.get_or_create(
                    candidate=user,
                    job=job,
                    defaults={
                        "status": "applied",
                        "ats_score": score
                    }
                )
                if not app_created:
                    app.ats_score = score
                    app.save()

                # Evaluate auto-shortlist & AI Call Trigger logic
                evaluate_and_apply_auto_action(app)

                # Check if AI Call was created and trigger execution simulation for demonstration
                if hasattr(app, 'ai_call'):
                    ai_call = app.ai_call
                    if ai_call.status == 'queued' and score >= 85.0:
                        ai_call.status = 'completed'
                        ai_call.completed_at = timezone.now() - timedelta(minutes=random.randint(10, 120))
                        ai_call.save()

                    self.stdout.write(
                        f"      -> Application #{app.id} for '{job.title[:30]}...': "
                        f"Score={app.ats_score}%, Status={app.status}, AICall Status={ai_call.status}"
                    )

        self.stdout.write(self.style.SUCCESS("\nSuccessfully seeded real-world production data!"))
