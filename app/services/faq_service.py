from app.tenants.models import ClinicConfig, FAQItem


def keyword_search(question: str, faqs: list[FAQItem]) -> FAQItem | None:
    """Fast keyword pre-filter before calling GPT. Returns best matching FAQ or None."""
    question_lower = question.lower()
    best_match: FAQItem | None = None
    best_score = 0

    for faq in faqs:
        score = sum(1 for kw in faq.keywords if kw.lower() in question_lower)
        if score > best_score:
            best_score = score
            best_match = faq

    return best_match if best_score >= 1 else None
