"""
answer_synthesizer.py
----------------------
Turns retrieved evidence chunks into the rich "Evidence panel" style answer
from the roadmap (verdict, why, evidence, limitations, confidence, missing
info). Tries the LLM (services/llm.py) first for the natural-language verdict
& limitations; if unavailable, falls back to a rule-based synthesis so the
prototype fully works offline.
"""

import re

from services import llm as llm_service
from services.confidence import evaluate_policy_answer

NEGATIVE_WORDS = [
    "excluded",
    "not covered",
    "will not be covered",
    "does not cover",
    "shall not",
]

POSITIVE_WORDS = [
    "covered",
    "payable",
    "admissible",
    "eligible",
    "reimburse",
]

LIMIT_KEYWORDS = {
    "co-payment": r"co-?payment[^.]{0,180}\.?",
    "room rent": r"room\s*rent[^.]{0,220}\.?",
    "waiting period": r"waiting\s*period[^.]{0,220}\.?",
    "sub-limit": r"sub[- ]?limit[^.]{0,220}\.?",
}


def _normalise_pdf_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _rule_based_verdict(evidence_chunks):
    # An "Exclusions" clause that mentions the topic takes priority over
    # generic "covered" language found elsewhere in the policy.
    for c in evidence_chunks:
        if "exclusion" in c["section"].lower() and any(
            w in c["text"].lower() for w in NEGATIVE_WORDS
        ):
            return {
                "verdict": "Likely Not Covered",
                "emoji": "🔴",
                "explanation": (
                    "This appears to fall under the policy's exclusions clause, "
                    "which lists items the insurer will not pay for."
                ),
                "limitations": [],
            }

    combined = " ".join(c["text"].lower() for c in evidence_chunks)

    neg_hits = sum(1 for w in NEGATIVE_WORDS if w in combined)
    pos_hits = sum(1 for w in POSITIVE_WORDS if w in combined)

    if neg_hits > pos_hits and neg_hits > 0:
        verdict = "Likely Not Covered"
        emoji = "🔴"
        explanation = (
            "The retrieved policy clauses suggest this may fall under "
            "an exclusion or restriction."
        )

    elif pos_hits > 0:
        verdict = "Potentially Covered"
        emoji = "🟢"
        explanation = (
            "The retrieved policy clauses indicate this is generally within "
            "covered hospitalisation/procedure terms, subject to the "
            "limitations below."
        )

    else:
        verdict = "Unclear"
        emoji = "🟡"
        explanation = (
            "The retrieved clauses reference this topic but don't clearly "
            "state coverage either way."
        )

    limitations = []

    for label, pattern in LIMIT_KEYWORDS.items():
        for c in evidence_chunks:
            clean_text = _normalise_pdf_text(c["text"])

            m = re.search(
                pattern,
                clean_text,
                re.IGNORECASE
            )

            if m:
                clause = m.group(0).strip()

                if clause not in limitations:
                    limitations.append(clause)

                break

    return {
        "verdict": verdict,
        "emoji": emoji,
        "explanation": explanation,
        "limitations": limitations,
    }


def synthesize_answer(question: str, evidence_chunks: list):
    conf = evaluate_policy_answer(evidence_chunks, question)

    llm_result = llm_service.llm_answer_with_citations(
        question,
        evidence_chunks
    )

    if llm_result:
        verdict = llm_result.get("verdict", "Unclear")

        emoji = {
            "Potentially Covered": "🟢",
            "Likely Not Covered": "🔴",
        }.get(verdict, "🟡")

        return {
            "question": question,
            "verdict": verdict,
            "emoji": emoji,
            "explanation": llm_result.get("explanation", ""),
            "limitations": llm_result.get("limitations", []),
            "confidence": llm_result.get(
                "confidence",
                conf["confidence"]
            ),
            "missing_information": llm_result.get(
                "missing_information",
                conf["missing_information"]
            ),
            "evidence": evidence_chunks,
            "source": "llm",
        }

    rb = (
        _rule_based_verdict(evidence_chunks)
        if evidence_chunks
        else {
            "verdict": "Unclear",
            "emoji": "🟡",
            "explanation": (
                "No matching clause was found in the uploaded "
                "policy for this question."
            ),
            "limitations": [],
        }
    )

    return {
        "question": question,
        **rb,
        "confidence": conf["confidence"],
        "missing_information": conf["missing_information"],
        "evidence": evidence_chunks,
        "source": "rule-based",
    }