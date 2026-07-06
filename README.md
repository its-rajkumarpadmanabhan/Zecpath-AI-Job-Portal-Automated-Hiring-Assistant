<<<<<<< HEAD
🚀 Zecpath – AI-Powered Job Portal & Automated Hiring Assistant

📌 Internship learning log — documenting my progress as I ramp up on the
Zecpath product and the Python/Django skills needed to build it.


📅 Day 1 — Product & Hiring Domain Understanding 🧠

🎯 Goal: Understand what Zecpath is, who it's for, and how the
end-to-end hiring pipeline works — before writing any code.

✅ What I did:


📖 Studied the full Zecpath PRD (Phases 1–100)
👥 Identified the users: Candidates, Recruiters/Employers, Admin
🧩 Broke the product into core modules: Auth, Job Management, ATS,
AI Screening, Interview & Offer flow
🔄 Mapped the full hiring flow: Application → ATS Screening → AI Call
→ Interview → Shortlisting → Offer
📚 Learned key domain concepts: Job Portal vs. ATS vs. AI-based hiring,
manual vs. automated hiring, with real-world references (Naukri,
LinkedIn, Indeed, Greenhouse)
🏗️ Thought through the system architecture: Frontend, Backend, AI
Services, Database, Cloud & Storage


📦 Deliverables:


📝 Product Understanding Document
🗺️ System flow diagram
📋 List of main system modules



📅 Day 2 — Python & Backend Basics Refresh 🐍

🎯 Goal: Strengthen Python fundamentals and backend/API concepts
needed for Django development.

✅ What I did:


🔁 Revised Python basics: variables, loops, functions
🏛️ Practiced OOP: class, object, inheritance, encapsulation
⚠️ Practiced exception handling
💻 Set up my dev environment: Python, pip, venv, VS Code (+ Python &
Pylance extensions), Postman
🌐 Learned backend & API concepts: what is a server, what is an API,
REST architecture, HTTP methods, request/response cycle, status
codes, JSON structure
📡 Sent test requests to a public API (JSONPlaceholder) using Postman


🛠️ Mini exercises built:

#ScriptConcepts1️⃣1_student_oop.pyClass, object, inheritance, encapsulation2️⃣2_calculator.pyFunctions, loops, exception handling3️⃣3_file_reader.pyFile read/write, exception handling4️⃣4_crud_simulation.pyCRUD simulation on in-memory data5️⃣5_json_read_write.pyJSON read/write, serialization

📦 Deliverables:


🐍 Python mini exercises (this repo!)
📑 REST API concept notes
📸 Working dev environment screenshots



🧭 What's Next

➡️ Moving into Django & Django REST Framework to start building the
actual Zecpath backend: authentication, job management, and the ATS
module. 🏗️


⭐ This repo is a running log — new folders/commits will be added as
each day of the internship progresses.
=======
# Zecpath Backend (Django) — Day 3

Minimal Django project created for Day 3 of the Zecpath internship,
covering Django installation, MVT architecture, and a first working
API endpoint.

## Setup

```bash
python3 -m venv day3_env
source day3_env/bin/activate      # macOS/Linux
day3_env\Scripts\activate         # Windows

pip install -r requirements.txt

python manage.py migrate
python manage.py runserver
```

## Endpoint

| Method | URL | Response |
|---|---|---|
| GET | `/api/` | `{"message": "Hello Zecpath Backend"}` |

Visit http://127.0.0.1:8000/api/ after starting the server, or test it
in Postman/curl:

```bash
curl http://127.0.0.1:8000/api/
```

## Project Structure

```
zecpath_backend/
├── manage.py
├── requirements.txt
├── core/                     # our first Django app
│   ├── views.py              # Home API view
│   ├── urls.py                # app-level routing
│   └── models.py
└── zecpath_backend/           # project config package
    ├── settings.py
    ├── urls.py                 # project-level routing (includes core.urls)
    └── wsgi.py / asgi.py
```

See `Django_Structure_Explanation.md` (in the Day 3 deliverables folder)
for a full breakdown of how these pieces fit together.
>>>>>>> cc03a3f (day 3)
