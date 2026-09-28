"""
extractor.py
------------
Module 1 of the roadmap: turn the raw policy text into a structured JSON of
key fields (sum insured, room-rent limit, co-payment, deductible, waiting
periods, exclusions).

The roadmap says: "don't hard-code extraction for every insurance policy...
use the LLM to identify these fields." For this offline prototype (no network
access in this environment) we implement a *generalised, regex + keyword*
extractor that plays the same role. `services/llm.py` exposes a hook
(`llm_extract_fields`) so that when an ANTHROPIC_API_KEY is available this
step can be swapped for an actual LLM call with no other code changes --
this is the "compatible with / scalable using AI & ML" requirement from the
rule book.
"""
import re


def _find_amount(text, patterns):
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            raw = m.group(1).replace(",", "")
            try:
                return float(raw)
            except ValueError:
                continue
    return None


def _find_percent(text, patterns):
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return f"{m.group(1)}%"
    return None


def extract_policy_fields(full_text: str) -> dict:
    text = full_text

    sum_insured = _find_amount(text, [
        r"sum\s+insured[^₹\d]{0,20}(?:rs\.?|inr|₹)?\s*([\d,]{4,})",
        r"(?:rs\.?|inr|₹)\s*([\d,]{4,})\s*(?:sum\s+insured)",
    ])

    deductible = _find_amount(text, [
        r"deductible[^₹\d]{0,20}(?:rs\.?|inr|₹)?\s*([\d,]{3,})",
    ])

    room_rent = None
    m = re.search(r"room\s*rent[^\n.]{0,140}\.?", text, re.IGNORECASE)
    if m:
        room_rent = m.group(0).strip()

    copay = _find_percent(text, [
        r"co-?payment[^%\d]{0,20}(\d{1,2})\s*%",
        r"(\d{1,2})\s*%[^\n]{0,20}co-?pay",
    ])

    waiting_general = None
    m = re.search(r"(?:initial|general)?\s*waiting\s*period[^\n]{0,60}?(\d+)\s*(day|days|month|months)",
                   text, re.IGNORECASE)
    if m:
        waiting_general = f"{m.group(1)} {m.group(2)}"

    waiting_pre_existing = None
    m = re.search(r"pre[- ]existing[^\n]{0,80}?(\d+)\s*(month|months|year|years)",
                   text, re.IGNORECASE)
    if m:
        waiting_pre_existing = f"{m.group(1)} {m.group(2)}"

    # Exclusions: only trigger on a standalone "Exclusions" HEADING line (not
    # on the word appearing mid-sentence elsewhere, e.g. "...subject to the
    # exclusions stated herein"), then grab bullet-like lines after it.
    exclusions = []
    heading_match = re.search(r"^[ \t]*exclusions?[ \t]*:?[ \t]*$", text, re.IGNORECASE | re.MULTILINE)
    if heading_match:
        block = text[heading_match.end():heading_match.end() + 2000]
        for line in block.split("\n"):
            line = line.strip(" -•\t")
            if not line:
                continue
            # stop once we hit what looks like the next section heading
            if len(line.split()) <= 6 and line.istitle() and not line[0] in "-•":
                break
            if 3 <= len(line) <= 160 and not re.match(r"^(page|section)\b", line, re.IGNORECASE):
                exclusions.append(line)
            if len(exclusions) >= 10:
                break

    return {
        "sum_insured": sum_insured,
        "room_rent_limit": room_rent,
        "copayment": copay,
        "deductible": deductible,
        "waiting_period": {
            "general": waiting_general,
            "pre_existing": waiting_pre_existing,
        },
        "exclusions": exclusions,
        "extraction_method": "rule-based (regex/keyword) — swap in services/llm.py for LLM-based extraction",
    }
