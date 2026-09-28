"""
llm.py
------
This module is the single place where the app talks to an LLM. If
ANTHROPIC_API_KEY is set in the environment, `ask_llm()` calls the real
Claude API and the routes will prefer its answer. If no key is set (e.g.
running the prototype offline for a demo/judge without internet), every
caller falls back to the deterministic rule-based logic already implemented
in extractor.py / calculator.py / confidence.py, so the app still runs
end-to-end.

This satisfies the rule book's "proposed solution should be compatible
with and scalable using AI & ML" requirement: the AI layer is a pluggable
component, not hard-wired, and the same interface can later call GPT/Gemini/
a self-hosted model instead.
"""
import os
import json
import requests

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"


def llm_available() -> bool:
    return bool(ANTHROPIC_API_KEY)


def ask_llm(system_prompt: str, user_prompt: str, max_tokens: int = 600):
    """Returns the raw text reply, or None if no API key / call fails."""
    if not ANTHROPIC_API_KEY:
        return None
    try:
        resp = requests.post(
            ANTHROPIC_URL,
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": max_tokens,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        parts = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
        return "\n".join(parts).strip() or None
    except Exception:
        return None


def llm_answer_with_citations(question: str, evidence_chunks: list):
    """
    Ask the LLM to answer ONLY from the retrieved evidence chunks and return
    structured JSON with a verdict + citations. Falls back to None (caller
    handles rule-based synthesis) if no key / call fails / bad JSON.
    """
    if not evidence_chunks:
        return None
    evidence_text = "\n\n".join(
        f"[Chunk {c['id']} | Page {c['page']} | Section: {c['section']}]\n{c['text']}"
        for c in evidence_chunks
    )
    system_prompt = (
        "You are an insurance policy assistant. Answer ONLY using the evidence "
        "provided. Never guess. Reply with strict JSON only, no markdown, no "
        "prose outside the JSON, matching this schema: "
        '{"verdict": "Potentially Covered|Likely Not Covered|Unclear", '
        '"explanation": "short plain-English explanation", '
        '"limitations": ["..."], "confidence": "High|Medium|Low", '
        '"missing_information": ["..."]}'
    )
    user_prompt = f"Question: {question}\n\nEvidence:\n{evidence_text}"
    raw = ask_llm(system_prompt, user_prompt)
    if not raw:
        return None
    try:
        cleaned = raw.strip().strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        return json.loads(cleaned)
    except Exception:
        return None
