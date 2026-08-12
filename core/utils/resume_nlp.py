import re

# Predefined Skills Library for Keyword Extraction
SKILLS_LIBRARY = [
    # Programming Languages
    "python", "javascript", "typescript", "java", "c++", "c#", "php", "ruby", "sql", "html", "css",
    # Frameworks & Libraries
    "django", "flask", "fastapi", "react", "node.js", "angular", "vue.js", "express", "bootstrap", "tailwind",
    # Databases & Storage
    "postgresql", "mysql", "mongodb", "sqlite", "redis",
    # Cloud, DevOps & Tools
    "aws", "docker", "kubernetes", "git", "github", "gitlab", "linux", "ci/cd",
    # Management & Soft Skills
    "leadership", "project management", "agile", "scrum", "communication", "teamwork", "problem solving"
]

COMMON_ROLES = [
    "software engineer", "backend engineer", "full stack developer", "frontend developer",
    "python developer", "data scientist", "devops engineer", "head manager", "general manager",
    "product manager", "project manager", "ui/ux designer"
]


def extract_email(text):
    """Extracts email address using regular expression matching."""
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return match.group(0) if match else None


def extract_phone(text):
    """Extracts phone number using standard patterns."""
    match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
    return match.group(0) if match else None


def extract_skills(text):
    """
    Tokenizes text and uses boundary pattern matching against the predefined skills library.
    """
    found_skills = set()
    text_lower = text.lower()

    for skill in SKILLS_LIBRARY:
        # Use regex word boundaries (\b) to prevent partial word matches
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.add(skill.title())

    return sorted(list(found_skills))


def extract_years_of_experience(text):
    """
    Parses years of experience by scanning date ranges (e.g., 2020-2023 or 2018-present)
    and explicit numerical indicators (e.g., '5 years of experience').
    """
    total_years = 0
    text_lower = text.lower()

    # Pattern 1: Explicit statements like "5+ years of experience" or "3 years"
    exp_matches = re.findall(r'(\d+)\+?\s*years?(?:\s+of)?\s+experience', text_lower)
    if exp_matches:
        years = [int(y) for y in exp_matches]
        return max(years)

    # Pattern 2: Scan for year ranges (e.g., 2016-2020, 2020 - 2023)
    year_ranges = re.findall(r'(\b20\d{2}\b)\s*[-–]\s*(\b20\d{2}\b|present|now)', text_lower)
    for start_year, end_year in year_ranges:
        start = int(start_year)
        end = 2026 if end_year in ['present', 'now'] else int(end_year)
        if end >= start:
            total_years += (end - start)

    return total_years if total_years > 0 else 1  # Default fallback estimate


def detect_target_role(text):
    """Detects candidate's primary job role/title based on common industry roles."""
    text_lower = text.lower()
    for role in COMMON_ROLES:
        pattern = r'\b' + re.escape(role) + r'\b'
        if re.search(pattern, text_lower):
            return role.title()
    return "Software Engineer"  # Default generic role fallback


def parse_resume_to_json(cleaned_text):
    """
    Master Pipeline: Converts raw cleaned text into a structured ML-ready Resume JSON Schema.
    """
    extracted_skills = extract_skills(cleaned_text)
    years_exp = extract_years_of_experience(cleaned_text)
    email = extract_email(cleaned_text)
    phone = extract_phone(cleaned_text)
    detected_role = detect_target_role(cleaned_text)

    resume_schema = {
        "contact_info": {
            "email": email,
            "phone": phone
        },
        "professional_summary": {
            "target_role": detected_role,
            "years_of_experience": years_exp
        },
        "extracted_skills": {
            "total_skills_found": len(extracted_skills),
            "skills_list": extracted_skills
        },
        "parsed_raw_length": len(cleaned_text)
    }

    return resume_schema