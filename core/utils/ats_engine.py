import re

def calculate_skill_match(required_skills_str, candidate_skills_list):
    """
    Calculates skill overlap percentage between job requirements and candidate skills.
    Weight: 50%
    """
    if not required_skills_str or not candidate_skills_list:
        return 0.0

    req_skills = set(s.strip().lower() for s in required_skills_str.split(',') if s.strip())
    cand_skills = set(s.strip().lower() for s in candidate_skills_list)

    if not req_skills:
        return 100.0

    matched = req_skills.intersection(cand_skills)
    overlap_ratio = len(matched) / len(req_skills)
    return round(overlap_ratio * 100, 2)


def calculate_experience_match(required_years, candidate_years):
    """
    Calculates experience match percentage based on required vs candidate years.
    Weight: 30%
    """
    # Safe type casting to int
    try:
        req = int(required_years) if required_years else 0
    except (ValueError, TypeError):
        req = 0

    try:
        cand = int(candidate_years) if candidate_years else 0
    except (ValueError, TypeError):
        cand = 0

    if req <= 0:
        return 100.0

    if cand >= req:
        return 100.0

    return round((cand / req) * 100, 2)


def calculate_role_relevance(job_title, candidate_role):
    """
    Calculates title/role keyword similarity.
    Weight: 20%
    """
    if not job_title or not candidate_role:
        return 50.0  # Neutral score baseline

    job_tokens = set(re.findall(r'\w+', job_title.lower()))
    cand_tokens = set(re.findall(r'\w+', candidate_role.lower()))

    if not job_tokens:
        return 100.0

    overlap = job_tokens.intersection(cand_tokens)
    if overlap:
        return 100.0
    return 30.0


def compute_ats_score(job, parsed_resume_data):
    """
    Master ATS Match Engine: Combines Skills (50%), Experience (30%), and Role Relevance (20%).
    Returns normalized suitability score percentage (0 - 100%).
    """
    # 1. Skill Match Score
    req_skills = getattr(job, 'skills_required', '')
    cand_skills = parsed_resume_data.get('extracted_skills', {}).get('skills_list', [])
    skill_score = calculate_skill_match(req_skills, cand_skills)

    # 2. Experience Score (Safe conversion)
    req_years = getattr(job, 'experience_required', 0)
    cand_years = parsed_resume_data.get('professional_summary', {}).get('years_of_experience', 0)
    exp_score = calculate_experience_match(req_years, cand_years)

    # 3. Role Relevance Score
    job_title = job.title
    cand_role = parsed_resume_data.get('professional_summary', {}).get('target_role', '')
    role_score = calculate_role_relevance(job_title, cand_role)

    # Weighted Calculation
    weighted_score = (skill_score * 0.50) + (exp_score * 0.30) + (role_score * 0.20)
    final_score = round(min(max(weighted_score, 0.0), 100.0), 2)

    return {
        "suitability_score": final_score,
        "breakdown": {
            "skill_match_percentage": skill_score,
            "experience_match_percentage": exp_score,
            "role_relevance_percentage": role_score
        }
    }