import logging

from core.models import AICandidateReport, AIInterviewSession, Application

logger = logging.getLogger(__name__)


class AICandidateReportGenerator:
    """
    Aggregates multi-round evaluation data: ATS scoring, AI voice screening,
    strengths, risks, and executive summary generation.
    """

    @classmethod
    def generate_report(cls, application_id: int) -> dict:
        try:
            application = Application.objects.select_related("job", "candidate").get(
                id=application_id
            )
        except Application.DoesNotExist:
            raise ValueError(f"Application #{application_id} not found.")

        # 1. Gather ATS Resume Evaluation Data
        ats_score = getattr(application, "ats_score", 85.0) or 85.0

        # 2. Gather AI Interview Scores & Q&A Responses
        session = (
            AIInterviewSession.objects.filter(application=application)
            .order_by("-started_at")
            .first()
        )

        ai_interview_score = session.ai_score if session and session.ai_score is not None else 80.0

        # 3. Calculate Composite Score (40% ATS + 60% AI Interview)
        composite_score = round((ats_score * 0.40) + (ai_interview_score * 0.60), 2)

        # 4. Extract Strengths & Risks
        strengths = []
        risks = []

        if ats_score >= 80.0:
            strengths.append(
                f"High resume skill alignment with '{application.job.title}' requirements."
            )
        if ai_interview_score >= 80.0:
            strengths.append(
                "Demonstrated articulate and comprehensive responses during AI technical screening."
            )
        else:
            risks.append(
                "Candidate responses during screening were brief or showed low technical depth."
            )

        if composite_score >= 85.0:
            recommendation = "strong_hire"
        elif composite_score >= 70.0:
            recommendation = "hire"
        elif composite_score >= 50.0:
            recommendation = "neutral"
        else:
            recommendation = "do_not_hire"

        # 5. Generate Executive Summary
        candidate_name = getattr(application.candidate, "username", "Candidate")
        executive_summary = (
            f"{candidate_name} applied for {application.job.title} at {application.job.company}. "
            f"Candidate achieved an ATS resume score of {ats_score}/100 and an AI screening interview score of "
            f"{ai_interview_score}/100, resulting in a composite score of {composite_score}/100. "
            f"Final recommendation: {recommendation.replace('_', ' ').title()}."
        )

        structured_data = {
            "application_id": application.id,
            "candidate": {
                "name": candidate_name,
                "email": getattr(application.candidate, "email", ""),
            },
            "job": {
                "id": application.job.id,
                "title": application.job.title,
                "company": application.job.company,
            },
            "metrics": {
                "ats_score": ats_score,
                "ai_interview_score": ai_interview_score,
                "composite_score": composite_score,
            },
            "recommendation": recommendation,
            "strengths": strengths,
            "risks": risks,
            "executive_summary": executive_summary,
        }

        # 6. Save or Update Report
        report, _ = AICandidateReport.objects.update_or_create(
            application=application,
            defaults={
                "ats_score": ats_score,
                "ai_interview_score": ai_interview_score,
                "composite_score": composite_score,
                "recommendation": recommendation,
                "executive_summary": executive_summary,
                "strengths": strengths,
                "risks": risks,
                "structured_report": structured_data,
            },
        )

        return structured_data
