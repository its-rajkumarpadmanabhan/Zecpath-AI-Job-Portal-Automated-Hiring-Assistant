import logging

from django.db.models import Avg, Count

from core.models import AIInterviewSession, Application, Job

logger = logging.getLogger(__name__)


def calculate_candidate_composite(app, session):
    """Prevents TypeError crashes caused by null database values during score weighting."""
    raw_ai_score = (
        getattr(session, "overall_score", getattr(session, "ai_score", 0.0)) if session else 0.0
    )
    ai_score = float(raw_ai_score) if raw_ai_score is not None else 0.0

    raw_ats_score = getattr(app, "match_score", getattr(app, "ats_score", 0.0))
    ats_score = float(raw_ats_score) if raw_ats_score is not None else 0.0

    composite = round((ai_score * 0.5) + (ats_score * 0.5), 2)
    return composite


class PremiumInsightsService:
    """Provides high-value algorithmic ranking, AI prediction, and hiring velocity analytics."""

    @classmethod
    def get_candidate_ranking_report(cls, job_id: int, employer_user) -> dict:
        """Ranks candidates using multi-factor composite scores (ATS + AI Evaluation + Status)."""
        job = Job.objects.filter(id=job_id, employer=employer_user).first()
        if not job:
            return {"error": "Job not found or unauthorized access."}

        applications = Application.objects.filter(job=job).select_related("candidate")
        ranked_list = []

        for app in applications:
            raw_ats = getattr(app, "match_score", getattr(app, "ats_score", 0.0))
            ats_score = float(raw_ats) if raw_ats is not None else 0.0

            # Retrieve AI interview session if available
            session = (
                AIInterviewSession.objects.filter(application=app).order_by("-started_at").first()
            )
            raw_ai = (
                getattr(session, "overall_score", getattr(session, "ai_score", None))
                if session
                else None
            )
            ai_score = float(raw_ai) if raw_ai is not None else round(ats_score * 0.9, 1)

            # Defensive Composite Ranking calculation
            composite_rank = calculate_candidate_composite(app, session)

            # Hiring probability / Success Prediction
            if composite_rank >= 85.0:
                prediction = "High Probability Hire"
                fit_tier = "Top Match"
            elif composite_rank >= 70.0:
                prediction = "Moderate Probability Hire"
                fit_tier = "Strong Candidate"
            else:
                prediction = "Low Probability Hire"
                fit_tier = "Potential Review"

            candidate_name = getattr(app.candidate, "name", "") or getattr(
                app.candidate, "username", "Candidate"
            )

            ranked_list.append(
                {
                    "application_id": app.id,
                    "candidate_id": app.candidate.id,
                    "candidate_name": candidate_name,
                    "candidate_email": app.candidate.email,
                    "ats_score": ats_score,
                    "ai_interview_score": ai_score,
                    "composite_rank_score": composite_rank,
                    "success_prediction": prediction,
                    "fit_tier": fit_tier,
                    "application_status": app.status,
                }
            )

        # Descending by composite ranking score
        ranked_list.sort(key=lambda item: item["composite_rank_score"], reverse=True)

        return {
            "job_id": job.id,
            "job_title": job.title,
            "total_evaluated_candidates": len(ranked_list),
            "rankings": ranked_list,
        }

    @classmethod
    def get_hiring_efficiency_metrics(cls, employer_user) -> dict:
        """Computes velocity and efficiency metrics across recruiter listings."""
        jobs = Job.objects.filter(employer=employer_user)
        total_jobs = jobs.count()

        total_applications = Application.objects.filter(job__in=jobs).count()
        total_selected = Application.objects.filter(job__in=jobs, status="selected").count()

        # Compute average ATS qualification score
        avg_ats = (
            Application.objects.filter(job__in=jobs).aggregate(Avg("ats_score"))["ats_score__avg"]
            or 0.0
        )

        efficiency_ratio = (
            round((total_selected / total_applications * 100), 2) if total_applications > 0 else 0.0
        )

        return {
            "recruiter_metrics": {
                "active_job_campaigns": total_jobs,
                "total_candidate_pipeline": total_applications,
                "successful_hires": total_selected,
                "average_candidate_quality_ats": round(float(avg_ats), 2),
                "hiring_conversion_efficiency_pct": efficiency_ratio,
                "estimated_hours_saved_by_ai": round(
                    total_applications * 1.5, 1
                ),  # 1.5 hrs saved per candidate
            }
        }
