import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class AnswerScoringEngine:
    """
    Evaluates candidate transcript text against job requirements and question context.
    Applies multi-factor scoring: Keyword Matching, Relevance, and Completeness.[cite: 2]
    """

    # Scoring Weights (Total = 1.0)[cite: 2]
    WEIGHT_KEYWORDS = 0.35
    WEIGHT_RELEVANCE = 0.40
    WEIGHT_COMPLETENESS = 0.25

    @classmethod
    def evaluate_answer(cls, answer_text: str, required_skills: str, question_category: str = 'experience') -> dict:
        if not answer_text or not answer_text.strip():
            return {
                "keyword_score": 0.0,
                "relevance_score": 0.0,
                "completeness_score": 0.0,
                "final_score": 0.0,
                "annotations": {"notes": "No response provided.", "matched_keywords": []}
            }

        text_lower = answer_text.lower()
        words = text_lower.split()

        # 1. Keyword Matching Score (0 - 100)[cite: 2]
        skill_list = [s.strip().lower() for s in required_skills.split(',') if s.strip()] if required_skills else []
        matched_keywords = [skill for skill in skill_list if skill in text_lower]
        keyword_score = (len(matched_keywords) / len(skill_list) * 100) if skill_list else 80.0
        keyword_score = min(keyword_score, 100.0)

        # 2. Completeness Score (0 - 100 based on detail/length)[cite: 2]
        word_count = len(words)
        if word_count < 5:
            completeness_score = 30.0
        elif word_count < 15:
            completeness_score = 65.0
        elif word_count < 30:
            completeness_score = 85.0
        else:
            completeness_score = 100.0

        # 3. Relevance Score (0 - 100)[cite: 2]
        # Evaluates presence of technical terminology and contextual depth
        relevance_score = 75.0
        if matched_keywords:
            relevance_score += min(len(matched_keywords) * 10.0, 25.0)
        if word_count >= 12:
            relevance_score = min(relevance_score + 5.0, 100.0)

        # 4. Normalized Weighted Score Scaling[cite: 2]
        final_score = round(
            (keyword_score * cls.WEIGHT_KEYWORDS) +
            (relevance_score * cls.WEIGHT_RELEVANCE) +
            (completeness_score * cls.WEIGHT_COMPLETENESS),
            2
        )

        annotations = {
            "matched_keywords": matched_keywords,
            "word_count": word_count,
            "category": question_category,
            "summary": f"Candidate demonstrated {len(matched_keywords)} relevant competencies with a response length of {word_count} words."
        }

        return {
            "keyword_score": round(keyword_score, 2),
            "relevance_score": round(relevance_score, 2),
            "completeness_score": round(completeness_score, 2),
            "final_score": final_score,
            "annotations": annotations
        }
