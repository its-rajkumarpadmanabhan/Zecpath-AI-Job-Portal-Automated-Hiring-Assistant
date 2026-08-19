from core.models import User, Employer, Job

# Recruiter 1
user1 = User.objects.create_user(
    email='sarah.jenkins@acmecorp.com', 
    password='StrongPassword123!', 
    name='Sarah Jenkins', 
    role='recruiter'
)

emp1, _ = Employer.objects.get_or_create(user=user1)
emp1.company_name = 'Acme Corp'
emp1.website = 'https://acmecorp.com'
emp1.domain = 'Technology'
emp1.company_size = '100-500'
emp1.is_verified = True
emp1.save()

Job.objects.create(
    employer=user1, 
    title='Senior Software Engineer', 
    company='Acme Corp', 
    description='Looking for a strong backend engineer to build scalable APIs.', 
    skills_required='Python, Django, AWS', 
    experience_required='5+ years', 
    salary_min=120000, 
    salary_max=150000, 
    location='Remote', 
    job_type='full_time', 
    status='active'
)

Job.objects.create(
    employer=user1, 
    title='DevOps Engineer', 
    company='Acme Corp', 
    description='Seeking a DevOps specialist to handle our infrastructure and deployment pipelines.', 
    skills_required='Docker, Kubernetes, CI/CD', 
    experience_required='3-5 years', 
    salary_min=100000, 
    salary_max=130000, 
    location='New York, NY', 
    job_type='full_time', 
    status='active'
)

# Recruiter 2
user2 = User.objects.create_user(
    email='m.chang@technova.io', 
    password='StrongPassword123!', 
    name='Michael Chang', 
    role='recruiter'
)

emp2, _ = Employer.objects.get_or_create(user=user2)
emp2.company_name = 'TechNova'
emp2.website = 'https://technova.io'
emp2.domain = 'AI/ML'
emp2.company_size = '50-100'
emp2.is_verified = True
emp2.save()

Job.objects.create(
    employer=user2, 
    title='Data Scientist', 
    company='TechNova', 
    description='Looking for a Data Scientist to build predictive models.', 
    skills_required='Python, Pandas, Machine Learning', 
    experience_required='2-4 years', 
    salary_min=110000, 
    salary_max=140000, 
    location='San Francisco, CA', 
    job_type='full_time', 
    status='active'
)

Job.objects.create(
    employer=user2, 
    title='Machine Learning Engineer', 
    company='TechNova', 
    description='Looking for an ML Engineer to deploy models into production.', 
    skills_required='PyTorch, TensorFlow, Python', 
    experience_required='3+ years', 
    salary_min=130000, 
    salary_max=160000, 
    location='Remote', 
    job_type='full_time', 
    status='active'
)

print("Successfully created 2 Recruiters and 4 Jobs!")
