# Policy-to-Patient: Insurance Coverage & Treatment Cost Intelligence

**Track:** Hack Matrix 5.0 — "Policy-to-Patient" problem statement
**Status:** Round 1 working prototype (Phases 1–7 of the roadmap implemented end-to-end)

An AI-powered assistant that lets a user upload a health-insurance policy PDF,
ask coverage questions with exact page/section citations, and estimate the
likely treatment cost, potential insurance coverage, and out-of-pocket
expense for a given treatment scenario — while explicitly flagging missing
information instead of guessing.

## What's implemented (the Round-1 minimum working slice)

```
PDF Upload → PDF Extraction (page-wise) → Chunking → TF-IDF Retrieval (RAG)
→ Question → Answer + Page/Section Citation → Treatment Form
→ Synthetic Cost Dataset lookup → Deterministic Coverage Calculator
→ Out-of-Pocket Estimate → Missing-Information / Confidence Engine
(before vs. after demo)
```

| Module (from the roadmap) | File | Status |
|---|---|---|
| 1. Policy Upload + field extraction | `services/extractor.py` | ✅ regex/keyword based, LLM-swappable |
| 2. Policy RAG (chunk → retrieve → answer) | `services/pdf_parser.py`, `chunker.py`, `retriever.py`, `answer_synthesizer.py` | ✅ TF-IDF cosine-similarity retrieval stands in for FAISS/Chroma |
| 3. Treatment scenario form | `static/index.html` | ✅ 6-field form as recommended |
| 4. Treatment cost dataset | `data/treatment_costs.csv` | ✅ 63 synthetic rows across 26 treatments × 4 cities |
| 5. Coverage calculation engine | `services/calculator.py` | ✅ pure deterministic arithmetic (not LLM) |
| 6. Missing-information engine | `services/confidence.py` | ✅ High/Medium/Low + explicit missing-field list, recalculates live |
| LLM hook (optional) | `services/llm.py` | ✅ pluggable — used automatically if `ANTHROPIC_API_KEY` is set, otherwise the app runs fully offline on rule-based logic |

This is intentionally **not** a finished product — see "What's next" below
for exactly what Phase 2 (the offline final) would add, matching the rule
book's requirement of a demonstrable 30–40% implementation with a clear path
to completion.

## Architecture

```
Browser (static/index.html, vanilla JS)
        │  fetch()
        ▼
Flask backend (app.py)
 ├─ /api/upload   → pdf_parser → chunker → extractor → retriever (per session)
 ├─ /api/ask      → retriever.retrieve() → answer_synthesizer (LLM if available, else rule-based)
 └─ /api/estimate → treatment_costs.csv lookup → calculator → confidence engine
```

Sessions are kept in memory (`SESSIONS` dict in `app.py`) — fine for a demo,
swap for SQLite/Redis before scaling beyond a single-user prototype.

## Running it

```bash
cd backend
pip install -r requirements.txt
python app.py
# open http://localhost:5000
```

A synthetic sample policy is already generated at `backend/data/sample_policy.pdf`
(regenerate any time with `python make_sample_policy.py`) — upload it to try
the whole flow immediately without needing a real policy document.

### Optional: enable real LLM reasoning
```bash
export ANTHROPIC_API_KEY=sk-ant-...
python app.py
```
With the key set, `/api/ask` calls Claude to synthesize the verdict/explanation
strictly from the retrieved evidence chunks (never from outside knowledge);
without it, the same endpoint falls back to the rule-based synthesizer so the
demo works with zero external dependencies / no internet.

## Demo script (matches the roadmap's 3-minute story)

1. Upload `sample_policy.pdf` → see extracted Sum Insured, co-pay, deductible,
   waiting periods, room-rent limit, exclusions.
2. Ask **"Is knee replacement covered?"** → 🟢 Potentially Covered, High
   confidence, citations to pages 2, 4 and 7.
3. Ask **"Is cosmetic surgery covered?"** → 🔴 Likely Not Covered, citing the
   Exclusions clause on page 6.
4. Fill the Treatment Estimator: Knee Replacement / Pune / Private / Age 55 /
   Pre-existing = **Unknown** → Medium confidence, missing-info list shown.
5. Change Pre-existing = **No**, Room = **General** → recalculates instantly
   to High confidence — the before/after "missing information" demo.

## What's next (planned for Round 2 / offline final)

- Swap TF-IDF retrieval for real embeddings + FAISS/ChromaDB for better recall
  on longer, more varied policy documents.
- OCR fallback (pytesseract/pdf2image) for scanned policy pages — the
  extractor already flags `scanned_pages_detected` as a hook for this.
- Sub-limit– and waiting-period–aware calculation (e.g. per-procedure caps
  like the sample policy's "Knee Replacement: ₹1,50,000 per knee").
- Expand the treatment-cost dataset with more cities/treatments or a real
  historical dataset.
- Persistent storage (SQLite) instead of in-memory sessions; basic auth.
- Scenario comparison view ("what changes if I switch hospitals/cities").

## Repo structure

```
backend/
├── app.py                      # Flask routes
├── make_sample_policy.py       # generates data/sample_policy.pdf
├── requirements.txt
├── data/
│   ├── treatment_costs.csv     # Module 4 synthetic dataset
│   └── sample_policy.pdf
├── services/
│   ├── pdf_parser.py           # Module 2 Step A
│   ├── chunker.py              # Module 2 Step B
│   ├── extractor.py            # Module 1
│   ├── retriever.py            # Module 2 Steps C/D
│   ├── answer_synthesizer.py   # Evidence-panel answer construction
│   ├── calculator.py           # Module 5
│   ├── confidence.py           # Module 6
│   └── llm.py                  # optional Claude API hook
└── static/
    └── index.html              # frontend (upload, chat, estimator)
```
