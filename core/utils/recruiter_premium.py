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
