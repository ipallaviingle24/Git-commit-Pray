"""
app.py
------
Flask backend for "Policy-to-Patient: Insurance Coverage & Treatment Cost
Intelligence". Implements the Round-1 minimum working slice from the
roadmap:

    PDF Upload -> PDF Extraction -> Chunking+Retrieval (RAG) -> Question
    -> Answer + Page Citation -> Treatment Form -> Synthetic Cost Dataset
    -> Deterministic Coverage Calculation -> OOP Estimate
    -> Missing-Information Engine (before/after)

Run with:  python app.py   (serves on http://localhost:5000)
"""
import os
import uuid
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory

from services.pdf_parser import extract_pages
from services.chunker import chunk_pages
from services.extractor import extract_policy_fields
from services.retriever import PolicyRetriever
from services.answer_synthesizer import synthesize_answer
from services.calculator import calculate_coverage
from services.confidence import evaluate_treatment_scenario
from services import llm as llm_service

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
STATIC_DIR = os.path.join(BASE_DIR, "static")
DATA_PATH = os.path.join(BASE_DIR, "data", "treatment_costs.csv")

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")

# ---- In-memory session store (fine for a hackathon prototype; swap for
#      SQLite/Redis for anything beyond a demo) --------------------------
SESSIONS = {}
COST_DF = pd.read_csv(DATA_PATH)


@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/api/status")
def status():
    return jsonify({
        "ok": True,
        "llm_enabled": llm_service.llm_available(),
        "treatments_in_dataset": sorted(COST_DF["treatment"].unique().tolist()),
        "cities_in_dataset": sorted(COST_DF["city"].unique().tolist()),
    })


# ---------------------------------------------------------------- Module 1
@app.route("/api/upload", methods=["POST"])
def upload_policy():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Field name must be 'file'."}), 400
    f = request.files["file"]
    if not f.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported in this prototype."}), 400

    session_id = str(uuid.uuid4())
    save_path = os.path.join(UPLOAD_DIR, f"{session_id}.pdf")
    f.save(save_path)

    pages = extract_pages(save_path)
    full_text = "\n".join(p["text"] for p in pages)
    chunks = chunk_pages(pages)
    retriever = PolicyRetriever(chunks)
    policy_fields = extract_policy_fields(full_text)

    scanned_pages = [p["page"] for p in pages if p["is_scanned"]]

    SESSIONS[session_id] = {
        "filename": f.filename,
        "pages": pages,
        "chunks": chunks,
        "retriever": retriever,
        "policy_fields": policy_fields,
    }

    return jsonify({
        "session_id": session_id,
        "filename": f.filename,
        "num_pages": len(pages),
        "num_chunks": len(chunks),
        "scanned_pages_detected": scanned_pages,
        "policy_fields": policy_fields,
    })


@app.route("/api/policy/<session_id>")
def get_policy(session_id):
    session = SESSIONS.get(session_id)
    if not session:
        return jsonify({"error": "Unknown session_id. Upload a policy first."}), 404
    return jsonify({
        "filename": session["filename"],
        "num_pages": len(session["pages"]),
        "policy_fields": session["policy_fields"],
    })


# ---------------------------------------------------------------- Module 2
@app.route("/api/ask", methods=["POST"])
def ask_question():
    body = request.get_json(force=True)
    session_id = body.get("session_id")
    question = (body.get("question") or "").strip()

    session = SESSIONS.get(session_id)
    if not session:
        return jsonify({"error": "Unknown session_id. Upload a policy first."}), 404
    if not question:
        return jsonify({"error": "question is required"}), 400

    evidence = session["retriever"].retrieve(question, top_k=4)
    answer = synthesize_answer(question, evidence)
    return jsonify(answer)


# ---------------------------------------------------------------- Modules 4-6
@app.route("/api/estimate", methods=["POST"])
def estimate_cost():
    body = request.get_json(force=True)
    session_id = body.get("session_id")
    session = SESSIONS.get(session_id)
    if not session:
        return jsonify({"error": "Unknown session_id. Upload a policy first."}), 404

    treatment = (body.get("treatment") or "").strip()
    city = (body.get("city") or "").strip()
    hospital_type = (body.get("hospital_type") or "Private").strip()
    age = body.get("age")
    pre_existing = body.get("pre_existing")  # "Yes" | "No" | "Unknown"
    room_type = (body.get("room_type") or "").strip()
    hospitalisation_days = body.get("hospitalisation_days")
    override_cost = body.get("treatment_cost")  # optional manual override

    # ---- Module 4: dataset lookup ----
    match = COST_DF[
        (COST_DF["treatment"].str.lower() == treatment.lower())
        & (COST_DF["city"].str.lower() == city.lower())
        & (COST_DF["hospital_type"].str.lower() == hospital_type.lower())
    ]
    dataset_hit = not match.empty
    if not dataset_hit:
        # relax city filter, then relax hospital_type filter
        match = COST_DF[COST_DF["treatment"].str.lower() == treatment.lower()]
        dataset_hit = not match.empty

    if dataset_hit:
        row = match.iloc[0]
        cost_range = {"min": float(row.min_cost), "max": float(row.max_cost)}
        typical_cost = float(row.typical_cost)
    else:
        cost_range = None
        typical_cost = None

    treatment_cost = float(override_cost) if override_cost else (typical_cost or 0)

    # ---- Module 5: deterministic coverage calculator ----
    room_rent_breach = False
    room_limit_text = (session["policy_fields"].get("room_rent_limit") or "").lower()
    if room_type and "private" in room_type.lower() and ("general" in room_limit_text or "%" in room_limit_text):
        # naive heuristic: if policy caps room rent and the patient chose a
        # non-"general"/private room, flag a possible proportionate deduction
        room_rent_breach = True

    calc = calculate_coverage(treatment_cost, session["policy_fields"], room_rent_breach=room_rent_breach)

    # ---- Module 6: confidence + missing-information engine ----
    scenario = {
        "treatment": treatment, "city": city, "hospital_type": hospital_type,
        "age": age, "pre_existing": pre_existing, "room_type": room_type,
        "hospitalisation_days": hospitalisation_days,
    }
    conf = evaluate_treatment_scenario(scenario, session["policy_fields"], dataset_hit)

    return jsonify({
        "scenario": scenario,
        "dataset_hit": dataset_hit,
        "estimated_treatment_cost_range": cost_range,
        "typical_treatment_cost": typical_cost,
        "treatment_cost_used": treatment_cost,
        "calculation": calc,
        "confidence": conf["confidence"],
        "missing_information": conf["missing_information"],
        "disclaimer": "This is an estimate for informational purposes only, not a guarantee of claim settlement.",
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
