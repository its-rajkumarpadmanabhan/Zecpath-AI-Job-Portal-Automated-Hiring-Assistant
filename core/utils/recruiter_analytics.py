import logging

from django.core.cache import cache
from django.db.models import Avg, Count, Q

from core.models import AIInterviewSession, Application, InterviewSchedule, Job

logger = logging.getLogger(__name__)


class RecruiterAnalyticsEngine:
    """
    Computes hiring funnel metrics, job-level performance, conversion ratios,
    and role-based analytics with Redis caching.
    """

    CACHE_TIMEOUT = 60 * 15  # Cache for 15 minutes

    @classmethod
    def get_overall_funnel_metrics(cls, employer_id: int = None) -> dict:
        """
        Calculates the complete recruitment funnel:
        Applied -> Shortlisted -> Interviewed -> Selected.
        """
        cache_key = f"recruiter_funnel_metrics_{employer_id or 'all'}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

        app_qs = Application.objects.all()
        if employer_id:
            app_qs = app_qs.filter(job__employer_id=employer_id)

        # 1. Pipeline Stages Count
        total_applied = app_qs.count()
        total_shortlisted = app_qs.filter(
            status__in=[
                "shortlisted",
                "interview_scheduled",
                "interviewed",
                "selected",
                "offered",
                "hired",
            ]
        ).count()
        total_interviewed = app_qs.filter(
            status__in=["interviewed", "selected", "offered", "hired"]
        ).count()
        total_selected = app_qs.filter(status__in=["selected", "offered", "hired"]).count()

        # 2. Conversion Ratios
        shortlist_ratio = (
            round((total_shortlisted / total_applied * 100), 2) if total_applied > 0 else 0.0
        )
        interview_ratio = (
            round((total_interviewed / total_shortlisted * 100), 2)
            if total_shortlisted > 0
            else 0.0
        )
        selection_ratio = (
            round((total_selected / total_interviewed * 100), 2) if total_interviewed > 0 else 0.0
        )
        overall_conversion = (
            round((total_selected / total_applied * 100), 2) if total_applied > 0 else 0.0
        )

        funnel_data = {
            "stages": {
                "applied": total_applied,
                "shortlisted": total_shortlisted,
                "interviewed": total_interviewed,
                "selected": total_selected,
            },
            "conversion_ratios": {
                "applied_to_shortlisted_pct": shortlist_ratio,
                "shortlisted_to_interviewed_pct": interview_ratio,
                "interviewed_to_selected_pct": selection_ratio,
                "overall_success_pct": overall_conversion,
            },
        }

        cache.set(cache_key, funnel_data, cls.CACHE_TIMEOUT)
        return funnel_data

    @classmethod
    def get_job_performance_metrics(cls, employer_id: int = None) -> list:
        """
        Calculates job-wise performance and candidate progression metrics.
        """
        job_qs = Job.objects.all()
        if employer_id:
            job_qs = job_qs.filter(employer_id=employer_id)

        # Query tuning using annotate & conditional Count
        jobs_annotated = job_qs.annotate(
            total_applications=Count("applications"),
            shortlisted_count=Count(
                "applications",
                filter=Q(
                    applications__status__in=[
                        "shortlisted",
                        "interview_scheduled",
                        "interviewed",
                        "selected",
                        "offered",
                        "hired",
                    ]
                ),
            ),
            interviewed_count=Count(
                "applications",
                filter=Q(applications__status__in=["interviewed", "selected", "offered", "hired"]),
            ),
            selected_count=Count(
                "applications", filter=Q(applications__status__in=["selected", "offered", "hired"])
            ),
            avg_ats_score=Avg("applications__ats_score"),
        ).values(
            "id",
            "title",
            "company",
            "total_applications",
            "shortlisted_count",
            "interviewed_count",
            "selected_count",
            "avg_ats_score",
        )

        results = []
        for item in jobs_annotated:
            total = item["total_applications"]
            selected = item["selected_count"]
            conversion = round((selected / total * 100), 2) if total > 0 else 0.0

            results.append(
                {
                    "job_id": item["id"],
                    "job_title": item["title"],
                    "company": item["company"],
                    "total_applications": total,
                    "shortlisted": item["shortlisted_count"],
                    "interviewed": item["interviewed_count"],
                    "selected": selected,
                    "conversion_rate_pct": conversion,
                    "avg_ats_score": round(item["avg_ats_score"] or 0.0, 2),
                }
            )

        return results
