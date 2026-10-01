import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import AICall, Application, Candidate, Employer, Job, User
from core.utils.automation_engine import evaluate_and_apply_auto_action


class Command(BaseCommand):
    help = "Seeds the Zecpath hiring assistant database with login.txt credentials and realistic production data."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting database seeding aligned with login.txt..."))
        global_password = "StrongPassword123!"

        # 0. Superuser / Admin
        admin_user, admin_created = User.objects.get_or_create(
            email="admin@zecpath.com",
            defaults={
                "name": "System Admin",
                "role": "recruiter",
                "is_active": True,
                "is_verified": True,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        admin_user.set_password(global_password)
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.is_active = True
        admin_user.is_verified = True
        admin_user.save()
        self.stdout.write(f"  [+] Superuser: {admin_user.email} (Password: {global_password})")

        # 1. Recruiters & Employers from login.txt
        recruiters_data = [
            {
                "email": "sarah.jenkins@acmecorp.com",
                "name": "Sarah Jenkins",
                "company_name": "Acme Corp",
                "website": "https://acmecorp.com",
                "domain": "Enterprise Cloud & DevOps",
                "company_size": "250-500 employees",
                "jobs": [
                    {
                        "title": "Senior Software Engineer",
                        "company": "Acme Corp",
                        "description": (
                            "Acme Corp is seeking a Senior Software Engineer to design and implement "
                            "high-performance web applications, scalable REST APIs, and microservices using Python, Django, and AWS."
                        ),
                        "skills_required": "Python, Django, AWS, PostgreSQL, REST API, Docker",
                        "experience_required": "4-6 years",
                        "salary_min": 130000.00,
                        "salary_max": 170000.00,
                        "location": "New York, NY (Hybrid)",
                        "job_type": "full_time",
                        "status": "active",
                    },
                    {
                        "title": "DevOps Engineer",
                        "company": "Acme Corp",
                        "description": (
                            "Looking for a DevOps Engineer to manage CI/CD deployment pipelines, container orchestration "
                            "with Kubernetes, cloud infrastructure automation with Terraform, and site reliability."
                        ),
                        "skills_required": "Docker, Kubernetes, CI/CD, AWS, Terraform, Linux",
                        "experience_required": "3-5 years",
                        "salary_min": 125000.00,
                        "salary_max": 160000.00,
                        "location": "Remote",
                        "job_type": "remote",
                        "status": "active",
                    },
                ],
            },
            {
                "email": "m.chang@technova.io",
                "name": "Michael Chang",
                "company_name": "TechNova",
                "website": "https://technova.io",
                "domain": "Artificial Intelligence & Analytics",
                "company_size": "100-250 employees",
                "jobs": [
                    {
                        "title": "Data Scientist",
                        "company": "TechNova",
                        "description": (
                            "TechNova is looking for a Data Scientist to analyze complex datasets, build predictive models, "
                            "and build end-to-end machine learning pipelines using Python, Pandas, and Scikit-Learn."
                        ),
                        "skills_required": "Python, Pandas, Machine Learning, Scikit-Learn, SQL, Data Visualization",
                        "experience_required": "3-5 years",
                        "salary_min": 135000.00,
                        "salary_max": 175000.00,
                        "location": "San Francisco, CA (Hybrid)",
                        "job_type": "full_time",
                        "status": "active",
                    },
                    {
                        "title": "Machine Learning Engineer",
                        "company": "TechNova",
                        "description": (
                            "Join TechNova as a Machine Learning Engineer to train deep learning architectures, "
                            "fine-tune LLM foundation models, and deploy real-time voice inference engines."
                        ),
                        "skills_required": "PyTorch, TensorFlow, Python, NLP, Deep Learning, Docker, FastAPI",
                        "experience_required": "3-6 years",
                        "salary_min": 145000.00,
                        "salary_max": 190000.00,
                        "location": "Remote",
                        "job_type": "full_time",
                        "status": "active",
                    },
                ],
            },
        ]

        all_jobs = []
        for r_info in recruiters_data:
            user, created = User.objects.get_or_create(
                email=r_info["email"],
                defaults={
                    "name": r_info["name"],
                    "role": "recruiter",
                    "is_active": True,
                    "is_verified": True,
                },
            )
            user.name = r_info["name"]
            user.role = "recruiter"
            user.is_active = True
            user.is_verified = True
            user.set_password(global_password)
            user.save()

            emp, _ = Employer.objects.get_or_create(
                user=user,
                defaults={
                    "company_name": r_info["company_name"],
                    "website": r_info["website"],
                    "domain": r_info["domain"],
                    "company_size": r_info["company_size"],
                    "is_verified": True,
                },
            )
            emp.company_name = r_info["company_name"]
            emp.website = r_info["website"]
            emp.domain = r_info["domain"]
            emp.company_size = r_info["company_size"]
            emp.is_verified = True
            emp.save()

            self.stdout.write(f"  [+] Recruiter: {user.name} ({user.email})")

            for j_info in r_info["jobs"]:
                job, _ = Job.objects.get_or_create(
                    employer=user,
                    title=j_info["title"],
                    defaults=j_info,
                )
                for k, v in j_info.items():
                    setattr(job, k, v)
                job.save()
                all_jobs.append(job)
                self.stdout.write(f"      - Job Posted: {job.title} at {job.company}")

        # 2. Candidates from login.txt
        candidates_data = [
            {
                "email": "alex.smith@example.com",
                "name": "Alex Smith",
                "skills": "Python, Django, PostgreSQL, AWS, Docker, REST API, Git",
                "education": "B.S. in Computer Science - UC Berkeley",
                "experience": "4 years as a Backend Developer building scalable web applications and cloud services.",
                "expected_salary": 145000.00,
                # Scores corresponding to: [Sarah's Senior SE, Sarah's DevOps, Michael's Data Scientist, Michael's ML Eng]
                "ats_scores": [93.0, 85.0, 68.0, 72.0],
            },
            {
                "email": "priya.patel@example.com",
                "name": "Priya Patel",
                "skills": "Python, PyTorch, Pandas, Machine Learning, TensorFlow, Scikit-Learn, Deep Learning, NLP",
                "education": "M.S. in Artificial Intelligence - Carnegie Mellon University",
                "experience": "3 years as a Machine Learning Engineer designing, evaluating, and deploying deep learning pipelines.",
                "expected_salary": 155000.00,
                # Scores corresponding to: [Sarah's Senior SE, Sarah's DevOps, Michael's Data Scientist, Michael's ML Eng]
                "ats_scores": [74.0, 62.0, 95.0, 96.0],
            },
        ]

        for cand_info in candidates_data:
            user, created = User.objects.get_or_create(
                email=cand_info["email"],
                defaults={
                    "name": cand_info["name"],
                    "role": "candidate",
                    "is_active": True,
                    "is_verified": True,
                },
            )
            user.name = cand_info["name"]
            user.role = "candidate"
            user.is_active = True
            user.is_verified = True
            user.set_password(global_password)
            user.save()

            cand, _ = Candidate.objects.get_or_create(
                user=user,
                defaults={
                    "skills": cand_info["skills"],
                    "education": cand_info["education"],
                    "experience": cand_info["experience"],
                    "expected_salary": cand_info["expected_salary"],
                    "is_deleted": False,
                },
            )
            cand.skills = cand_info["skills"]
            cand.education = cand_info["education"]
            cand.experience = cand_info["experience"]
            cand.expected_salary = cand_info["expected_salary"]
            cand.is_deleted = False
            cand.save()

            self.stdout.write(f"  [+] Candidate: {user.name} ({user.email})")

            # 3. Create Applications & Automatic Screening / AI Calls
            for idx, job in enumerate(all_jobs):
                score = cand_info["ats_scores"][idx]
                app, app_created = Application.objects.get_or_create(
                    candidate=user, job=job, defaults={"status": "applied", "ats_score": score}
                )
                app.ats_score = score
                app.save()

                evaluate_and_apply_auto_action(app)

                if hasattr(app, "ai_call"):
                    ai_call = app.ai_call
                    if ai_call.status == "queued" and score >= 85.0:
                        ai_call.status = "completed"
                        ai_call.completed_at = timezone.now() - timedelta(
                            minutes=random.randint(15, 60)
                        )
                        ai_call.save()

                    self.stdout.write(
                        f"      -> Application #{app.id} for '{job.title}': "
                        f"ATS Score={app.ats_score}%, Status={app.status}, AICall Status={ai_call.status}"
                    )

        self.stdout.write(self.style.SUCCESS("\nSuccessfully seeded all users from login.txt with full credentials!"))
