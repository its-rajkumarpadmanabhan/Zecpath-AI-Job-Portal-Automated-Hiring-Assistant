# Authentication & Authorization Architecture

## 1. Token-Based Authentication Flow (JWT)

[ Client ] ---> POST /api/auth/login/ (email, password)
             <--- 200 OK (access_token, refresh_token)

[ Client ] ---> GET /api/profile/candidate/ 
             Headers: Authorization: Bearer <access_token>
             <--- 200 OK (candidate profile data)

## 2. Role-Based Access Control (RBAC) Architecture

- User (Base Model)
  └── Candidate Profile (Role: Candidate) ---> Upload Resume, View Jobs
  └── Employer Profile (Role: Recruiter) ---> Create Jobs, View Candidates