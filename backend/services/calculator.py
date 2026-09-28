"""
calculator.py
-------------
Module 5 of the roadmap: "This should not be entirely handled by the LLM.
Use normal code for calculations." Pure deterministic arithmetic -- no LLM
involved, so numbers are always reproducible and auditable.

Formula (matches the roadmap's worked example):
    eligible_amount = treatment_cost - deductible
    after_copay      = eligible_amount * (1 - copay_pct)
    potential_cover   = min(after_copay, sum_insured, room_rent_cap_effect)
    out_of_pocket     = treatment_cost - potential_cover
"""


def parse_percent(copay_str):
    if not copay_str:
        return 0.0
    try:
        return float(str(copay_str).replace("%", "").strip()) / 100.0
    except ValueError:
        return 0.0


def calculate_coverage(treatment_cost: float, policy: dict, room_rent_breach: bool = False):
    deductible = policy.get("deductible") or 0
    copay_pct = parse_percent(policy.get("copayment"))
    sum_insured = policy.get("sum_insured")

    eligible = max(treatment_cost - deductible, 0)
    after_copay = eligible * (1 - copay_pct)

    # Simple room-rent proportionate deduction if the user's chosen room
    # breaches the policy's room-rent limit (common real-world clause).
    room_rent_penalty_pct = 0.10 if room_rent_breach else 0.0
    after_room_rent = after_copay * (1 - room_rent_penalty_pct)

    potential_cover = after_room_rent
    capped_by_sum_insured = False
    if sum_insured is not None and potential_cover > sum_insured:
        potential_cover = sum_insured
        capped_by_sum_insured = True

    potential_cover = round(max(potential_cover, 0), 2)
    out_of_pocket = round(max(treatment_cost - potential_cover, 0), 2)

    return {
        "treatment_cost": treatment_cost,
        "deductible_applied": deductible,
        "copay_pct_applied": copay_pct * 100,
        "room_rent_penalty_applied_pct": room_rent_penalty_pct * 100,
        "capped_by_sum_insured": capped_by_sum_insured,
        "potential_coverage": potential_cover,
        "estimated_out_of_pocket": out_of_pocket,
        "breakdown_steps": [
            f"Eligible amount = ₹{treatment_cost:,.0f} - ₹{deductible:,.0f} (deductible) = ₹{eligible:,.0f}",
            f"After {copay_pct*100:.0f}% co-payment = ₹{eligible:,.0f} × {(1-copay_pct)*100:.0f}% = ₹{after_copay:,.0f}",
            (f"Room-rent limit breached -> extra {room_rent_penalty_pct*100:.0f}% proportionate deduction = ₹{after_room_rent:,.0f}"
             if room_rent_breach else "No room-rent limit breach assumed"),
            (f"Capped at sum insured ₹{sum_insured:,.0f}" if capped_by_sum_insured
             else "Not capped by sum insured"),
            f"Potential coverage ≈ ₹{potential_cover:,.0f}",
            f"Estimated out-of-pocket ≈ ₹{out_of_pocket:,.0f}",
        ],
    }
