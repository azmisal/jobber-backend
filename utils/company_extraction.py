import re
from typing import Optional, Tuple


def _clean_company(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    # Strip trailing punctuation
    s = s.rstrip(".,;:\"'\n\t")
    return s


def extract_company_name_from_jd(jd_text: str) -> Tuple[Optional[str], float]:
    """Best-effort company extraction.

    Returns (companyName, confidence 0..1).

    Heuristics:
    - "at {Company}" / "At {Company}" near start of sentences
    - "Company:" / "Employer:" patterns
    - "for {Company}" (often includes role context)
    - "We are a" / "Join us" are too ambiguous => low confidence
    """

    text = (jd_text or "").strip()
    if not text:
        return None, 0.0

    # Normalize whitespace for regex
    compact = re.sub(r"\s+", " ", text)

    patterns = [
        # e.g. "Software Engineer at Acme Corp"
        (r"\bat\s+([A-Z][A-Za-z0-9&.,\- ]{1,80})", 0.8),
        # e.g. "Company: Acme Corp"
        (r"\b(?:Company|Employer)\s*[:\-]\s*([A-Z][A-Za-z0-9&.,\- ]{1,80})", 0.9),
        # e.g. "for Acme Corp"
        (r"\bfor\s+([A-Z][A-Za-z0-9&.,\- ]{1,80})", 0.55),
    ]

    for pattern, conf in patterns:
        m = re.search(pattern, compact)
        if m:
            company = _clean_company(m.group(1))
            # Reject obvious non-company captures
            if company and len(company) >= 2:
                # Avoid capturing role words
                if company.lower() in {"we", "you", "the", "our", "your"}:
                    continue
                return company, conf

    return None, 0.0

