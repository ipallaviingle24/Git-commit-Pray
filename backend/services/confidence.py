"""
confidence.py
-------------
Module 6 of the roadmap: the "Missing Information Engine". Decides
HIGH / MEDIUM / LOW confidence and lists exactly what's missing, so the
system never silently guesses -- directly satisfying the problem
statement's "clearly flags missing information rather than guessing".
"""

TREATMENT_FIELDS = ["treatment", "city", "hospital_type", "age",
                     "pre_existing", "room_type", "hospitalisation_days"]


def evaluate_treatment_scenario(scenario: dict, policy: dict, dataset_hit: bool):
    missing = []

    if not dataset_hit:
        missing.append("Treatment not found in the cost dataset (cost estimate unavailable/approximate)")

    if scenario.get("pre_existing") in (None, "", "unknown", "Unknown"):
        missing.append("Whether the condition is pre-existing (affects waiting-period eligibility)")

    if not scenario.get("room_type"):
        missing.append("Room category to be used (affects room-rent limit / proportionate deduction)")

    if policy.get("sum_insured") is None:
        missing.append("Policy sum insured could not be confidently extracted")

    if policy.get("copayment") is None:
        missing.append("Policy co-payment percentage could not be confidently extracted")

    if not policy.get("exclusions"):
        missing.append("Could not confirm whether this treatment is on the exclusions list")

    if scenario.get("pre_existing") in ("Yes", "yes", True) and policy.get("waiting_period", {}).get("pre_existing"):
        missing.append(
            f"Policy specifies a pre-existing waiting period of "
            f"{policy['waiting_period']['pre_existing']} — patient's policy tenure not provided, "
            "so eligibility cannot be confirmed"
        )

    if len(missing) == 0:
        confidence = "High"
    elif len(missing) <= 2:
        confidence = "Medium"
    else:
        confidence = "Low"

    # A pre-existing condition with an unmet/unknown waiting period should
    # never be reported as High confidence, even if other fields are fine.
    if scenario.get("pre_existing") in ("Yes", "yes", True) and confidence == "High":
        confidence = "Medium"

    return {
        "confidence": confidence,
        "missing_information": missing,
    }


def evaluate_policy_answer(evidence_chunks: list, question: str):
    if not evidence_chunks:
        return {
            "confidence": "Low",
            "missing_information": [
                "No relevant clause was found in the uploaded policy for this question."
            ],
        }
    top_score = evidence_chunks[0].get("score", 0)
    if top_score >= 0.25 and len(evidence_chunks) >= 2:
        return {"confidence": "High", "missing_information": []}
    if top_score >= 0.12:
        return {"confidence": "Medium",
                 "missing_information": ["Only partial/ambiguous clause matches were found; consider rephrasing."]}
    return {"confidence": "Low",
             "missing_information": ["No explicit, closely-matching policy clause was found for this question."]}
