from core.models import User, Candidate

# Candidate 1: Backend / Python Focus (Good match for Sarah Jenkins' jobs)
user1 = User.objects.create_user(
    email='alex.smith@example.com', 
    password='StrongPassword123!', 
    name='Alex Smith', 
    role='candidate'
)

cand1, _ = Candidate.objects.get_or_create(user=user1)
cand1.skills = 'Python, Django, PostgreSQL, AWS, Docker'
cand1.education = 'B.S. in Computer Science, State University'
cand1.experience = '4 years as a Backend Developer'
cand1.expected_salary = 125000
cand1.save()


# Candidate 2: AI / ML Focus (Good match for Michael Chang's jobs)
user2 = User.objects.create_user(
    email='priya.patel@example.com', 
    password='StrongPassword123!', 
    name='Priya Patel', 
    role='candidate'
)

cand2, _ = Candidate.objects.get_or_create(user=user2)
cand2.skills = 'Python, PyTorch, Pandas, Machine Learning, TensorFlow'
cand2.education = 'M.S. in Data Science, Tech Institute'
cand2.experience = '3 years as a Machine Learning Engineer'
cand2.expected_salary = 135000
cand2.save()

print("Successfully created 2 Candidates!")
