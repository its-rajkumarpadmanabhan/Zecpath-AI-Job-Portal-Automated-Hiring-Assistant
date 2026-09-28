from core.models import Job

class SmartRecommendationService:
    """Computes skill match overlap and suggests high-affinity jobs for candidates."""

    @classmethod
    def get_recommendations_for_skills(cls, candidate_skills: list) -> list:
        cand_set = {s.strip().lower() for s in candidate_skills if isinstance(s, str)}
        open_jobs = Job.objects.filter(status='active').select_related('employer')
        matches = []

        for job in open_jobs:
            req_skills = [s.strip().lower() for s in getattr(job, 'skills_required', '').split(',') if s.strip()]
            if not req_skills:
                continue

            req_set = set(req_skills)
            matched = cand_set.intersection(req_set)
            missing = req_set - cand_set
            
            overlap_pct = round((len(matched) / len(req_set)) * 100, 1)

            if overlap_pct >= 40.0:  # Match threshold
                matches.append({
                    "job_id": job.id,
                    "job_title": job.title,
                    "company": getattr(job, 'company', 'Zecpath Partner'),
                    "location": getattr(job, 'location', 'Remote'),
                    "match_percentage": overlap_pct,
                    "matching_skills": list(matched),
                    "missing_skills_to_acquire": list(missing)
                })

        return sorted(matches, key=lambda x: x['match_percentage'], reverse=True)
