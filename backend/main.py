"""
AI1X Auditor — FastAPI Backend
"""
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import os

from skills_loader import load_all, load_schema, load_joins, load_domain, load_reports
from sql_generator import generate_sql
from ai_chat import chat
from compare_engine import compare

app = FastAPI(title="AI1X Auditor", version="0.1.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Serve mockups as static files
MOCKUPS_DIR = os.path.join(os.path.dirname(__file__), "..", "mockups")
if os.path.exists(MOCKUPS_DIR):
    app.mount("/ui", StaticFiles(directory=MOCKUPS_DIR, html=True), name="ui")

# ---- Schema APIs ----

@app.get("/api/schema")
def get_schema():
    tables = load_schema()
    summary = []
    for name, t in tables.items():
        summary.append({
            "table_name": name,
            "classification": t.get("classification"),
            "columns_count": len(t.get("columns", {})),
            "row_count": t.get("row_count_approx"),
            "description": t.get("description", "")[:200],
        })
    return {"tables": summary, "total": len(summary)}

@app.get("/api/schema/{table_name}")
def get_table(table_name: str):
    tables = load_schema()
    t = tables.get(table_name)
    if not t:
        return {"error": f"Table '{table_name}' not found"}
    return t

# ---- Joins API ----

@app.get("/api/joins")
def get_joins():
    joins = load_joins()
    return {"joins": list(joins.values()), "total": len(joins)}

# ---- Domain API ----

@app.get("/api/domain")
def get_domain():
    return load_domain()

@app.get("/api/domain/measures")
def get_measures():
    d = load_domain()
    return d.get("measures", {})

@app.get("/api/domain/field-templates")
def get_field_templates():
    d = load_domain()
    return d.get("field_templates", {})

@app.get("/api/domain/cross-field-rules")
def get_cross_field_rules():
    d = load_domain()
    return d.get("standard_cross_field_rules", [])

# ---- Reports APIs ----

@app.get("/api/reports")
def get_reports():
    reports = load_reports()
    summary = []
    for rid, r in reports.items():
        summary.append({
            "report_id": rid,
            "report_name": r.get("report_name"),
            "status": r.get("status"),
            "fields_count": len(r.get("fields", [])),
            "slicers_count": len(r.get("slicers", [])),
        })
    return {"reports": summary}

@app.get("/api/reports/{report_id}")
def get_report(report_id: str):
    reports = load_reports()
    r = reports.get(report_id)
    if not r:
        return {"error": f"Report '{report_id}' not found"}
    return r

# ---- SQL Generation ----

class SQLRequest(BaseModel):
    report_id: str
    slicers: Optional[dict] = None

@app.post("/api/generate-sql")
def api_generate_sql(req: SQLRequest):
    sql = generate_sql(req.report_id, req.slicers)
    return {"sql": sql, "report_id": req.report_id, "slicers": req.slicers}

# ---- AI Chat ----

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
def api_chat(req: ChatRequest):
    response = chat(req.message)
    return {"response": response, "source": "ollama" if "ollama" not in response.lower() else "rule_based"}

# ---- Compare ----

class CompareRequest(BaseModel):
    pbi_csv: str
    sql_csv: str
    composite_key: list
    tolerance: Optional[float] = 0.01

@app.post("/api/compare")
def api_compare(req: CompareRequest):
    result = compare(req.pbi_csv, req.sql_csv, req.composite_key, req.tolerance)
    # Save run history
    _save_run(result, req)
    return result

@app.post("/api/compare/upload")
async def api_compare_upload(
    pbi_file: UploadFile = File(...),
    sql_file: UploadFile = File(...),
):
    pbi_csv = (await pbi_file.read()).decode("utf-8")
    sql_csv = (await sql_file.read()).decode("utf-8")
    result = compare(pbi_csv, sql_csv, ["Measures", "Submission"])
    _save_run(result, None)
    return result

def _save_run(result, req):
    import json, datetime
    runs_dir = os.path.join(os.path.dirname(__file__), "..", "runs")
    os.makedirs(runs_dir, exist_ok=True)
    run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_data = {
        "run_id": run_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "composite_key": req.composite_key if req else ["Measures", "Submission"],
        "tolerance": req.tolerance if req else 0.01,
        "pbi_rows": result["pbi_rows"],
        "sql_rows": result["sql_rows"],
        "matched_rows": result["matched_rows"],
        "mismatched_rows": result["mismatched_rows"],
        "match_rate": result["match_rate"],
        "cell_mismatches": result["cell_mismatches"],
        "mismatches": result["mismatches"],
    }
    with open(os.path.join(runs_dir, f"{run_id}.json"), "w") as f:
        json.dump(run_data, f, indent=2)

@app.get("/api/runs")
def get_runs():
    import json, glob
    runs_dir = os.path.join(os.path.dirname(__file__), "..", "runs")
    if not os.path.exists(runs_dir):
        return {"runs": []}
    files = sorted(glob.glob(os.path.join(runs_dir, "*.json")), reverse=True)
    runs = []
    for f in files[:50]:
        with open(f) as fh:
            runs.append(json.load(fh))
    return {"runs": runs}

# ---- Health ----

@app.get("/api/health")
def health():
    data = load_all()
    return {
        "status": "ok",
        "schema_tables": len(data["schema"]),
        "joins": len(data["joins"]),
        "reports": len(data["reports"]),
        "hedis_measures": len(data["domain"].get("measures", {})),
        "field_templates": len(data["domain"].get("field_templates", {})),
    }
