"""
AI1X Auditor — FastAPI Backend
"""
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import os, requests

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

from fastapi.responses import RedirectResponse

@app.get("/")
def root():
    return RedirectResponse(url="/ui/05-home-loaded.html")

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

# ---- Report Edit ----

class ReportEditRequest(BaseModel):
    report_id: str
    updates: dict

@app.post("/api/reports/{report_id}/edit")
def api_report_edit(report_id: str, req: ReportEditRequest):
    import yaml
    from pathlib import Path
    reports = load_reports()
    r = reports.get(report_id)
    if not r:
        return {"error": f"Report '{report_id}' not found"}
    for k, v in req.updates.items():
        r[k] = v
    filepath = Path(__file__).parent.parent / "skills" / "reports" / f"{report_id}.yaml"
    with open(filepath, "w") as f:
        yaml.dump(r, f, default_flow_style=False, sort_keys=False)
    return {"status": "saved", "report_id": report_id}

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

# ---- Model Configuration ----

class ModelRequest(BaseModel):
    provider: str = "ollama"
    model: str = ""
    api_key: str = ""
    url: str = ""

# In-memory model config
_model_config = {
    "provider": "ollama",
    "model": "llama3.2-vision",
    "url": "http://localhost:11434",
    "api_key": "",
}

@app.get("/api/model")
def get_model():
    config = dict(_model_config)
    # List available Ollama models
    available = []
    if config["provider"] == "ollama":
        try:
            r = requests.get(f"{config['url']}/api/tags", timeout=5)
            if r.status_code == 200:
                available = [m["name"] for m in r.json().get("models", [])]
        except Exception:
            pass
    config["available"] = available
    return config

@app.post("/api/model")
def set_model(req: ModelRequest):
    _model_config["provider"] = req.provider
    if req.model:
        _model_config["model"] = req.model
    if req.api_key:
        _model_config["api_key"] = req.api_key
    if req.provider == "ollama":
        _model_config["url"] = req.url or "http://localhost:11434"
    elif req.provider == "openai":
        _model_config["url"] = "https://api.openai.com/v1"
    elif req.provider == "anthropic":
        _model_config["url"] = "https://api.anthropic.com/v1"

    # Update ai_chat module
    import ai_chat
    if req.provider == "ollama":
        ai_chat.OLLAMA_URL = f"{_model_config['url']}/api/generate"
        ai_chat.MODEL = _model_config["model"]

    return {"status": "ok", "provider": _model_config["provider"], "model": _model_config["model"]}

# ---- Schema Edit ----

class SchemaEditRequest(BaseModel):
    table_name: str
    column_name: Optional[str] = None
    updates: dict

@app.post("/api/schema/edit")
def api_schema_edit(req: SchemaEditRequest):
    import yaml
    from pathlib import Path

    tables = load_schema()
    t = tables.get(req.table_name)
    if not t:
        return {"error": f"Table '{req.table_name}' not found"}

    if req.column_name:
        cols = t.get("columns", {})
        if req.column_name not in cols:
            return {"error": f"Column '{req.column_name}' not found in {req.table_name}"}
        for k, v in req.updates.items():
            cols[req.column_name][k] = v
        # Also update column_mappings cache
        mappings_path = Path(__file__).parent.parent / "skills" / "domain" / "column_mappings.yaml"
        if mappings_path.exists():
            mappings = yaml.safe_load(open(mappings_path)) or {}
            if req.column_name not in mappings:
                mappings[req.column_name] = {}
            for k, v in req.updates.items():
                if k not in ("data_type", "nullable", "pk"):
                    mappings[req.column_name][k] = v
            with open(mappings_path, "w") as f:
                yaml.dump(mappings, f, default_flow_style=False, sort_keys=False)
    else:
        for k, v in req.updates.items():
            t[k] = v

    # Save table YAML
    skills_dir = Path(__file__).parent.parent / "skills" / "schema"
    # Find which file contains this table
    for p in skills_dir.glob("*.yaml"):
        if p.name.startswith("_"):
            continue
        docs = list(yaml.safe_load_all(open(p)))
        for i, d in enumerate(docs):
            if isinstance(d, dict) and d.get("table_name") == req.table_name:
                if len(docs) == 1:
                    with open(p, "w") as f:
                        yaml.dump(t, f, default_flow_style=False, sort_keys=False)
                else:
                    docs[i] = t
                    with open(p, "w") as f:
                        for di, doc in enumerate(docs):
                            if di > 0:
                                f.write("---\n")
                            yaml.dump(doc, f, default_flow_style=False, sort_keys=False)
                target = req.column_name or "table"
                return {"status": "saved", "table": req.table_name, "target": target, "updates": req.updates}

    return {"error": "Could not find YAML file for table"}

# ---- Validate Report ----

@app.get("/api/validate/{report_id}")
def api_validate(report_id: str):
    data = load_all()
    report = data["reports"].get(report_id)
    if not report:
        return {"error": f"Report '{report_id}' not found"}

    domain = data["domain"]
    templates = domain.get("field_templates", {})
    std_slicers = domain.get("standard_slicers", [])
    results = []

    # Check template_refs exist
    missing_refs = [f["display_name"] for f in report.get("fields", [])
                    if f.get("template_ref") and f["template_ref"] not in templates]
    if missing_refs:
        results.append({"check": "template_refs", "status": "error", "msg": f"Missing templates: {', '.join(missing_refs)}"})
    else:
        results.append({"check": "template_refs", "status": "pass", "msg": f"All {len(report.get('fields',[]))} template_refs valid"})

    # Check group_by has all non-aggregate fields
    fields = report.get("fields", [])
    non_agg = [f["display_name"] for f in fields if not f.get("is_aggregate") and not templates.get(f.get("template_ref",""),{}).get("is_aggregate")]
    gb = report.get("group_by") or report.get("aggregation_levels", [{}])[0].get("group_by", []) if report.get("aggregation_levels") else []
    if isinstance(gb, list) and non_agg:
        results.append({"check": "group_by", "status": "pass", "msg": f"group_by defined with {len(gb)} columns"})
    else:
        results.append({"check": "group_by", "status": "warning", "msg": "group_by not explicitly defined"})

    # Check slicers
    report_slicers = [s["name"] for s in report.get("slicers", [])]
    slicer_names = [s["name"] for s in std_slicers]
    missing_slicers = [s for s in slicer_names if s not in report_slicers]
    if missing_slicers:
        results.append({"check": "slicers", "status": "error", "msg": f"Missing standard slicers: {', '.join(missing_slicers)}"})
    else:
        results.append({"check": "slicers", "status": "pass", "msg": f"All {len(slicer_names)} standard slicers present"})

    # Check composite_key
    ck = report.get("composite_key", [])
    field_names = [f["display_name"] for f in fields]
    bad_ck = [k for k in ck if k not in field_names]
    if bad_ck:
        results.append({"check": "composite_key", "status": "error", "msg": f"Key columns not in fields: {', '.join(bad_ck)}"})
    elif ck:
        results.append({"check": "composite_key", "status": "pass", "msg": f"Composite key: {' + '.join(ck)}"})
    else:
        results.append({"check": "composite_key", "status": "warning", "msg": "No composite_key defined"})

    # Check fixed_filters
    ff = report.get("fixed_filters", [])
    if any("isRau" in f or "isRaw" in f for f in ff):
        results.append({"check": "fixed_filters", "status": "pass", "msg": f"{len(ff)} fixed filters defined"})
    else:
        results.append({"check": "fixed_filters", "status": "warning", "msg": "Missing isRau=0 filter"})

    passed = sum(1 for r in results if r["status"] == "pass")
    errors = sum(1 for r in results if r["status"] == "error")
    warnings = sum(1 for r in results if r["status"] == "warning")
    return {"report_id": report_id, "results": results, "passed": passed, "errors": errors, "warnings": warnings}

# ---- HEDIS Domain Query ----

@app.post("/api/hedis")
def api_hedis(req: ChatRequest):
    import yaml
    from pathlib import Path
    spec_path = Path(__file__).parent.parent / "skills" / "domain" / "hedis_technical_spec.yaml"
    if not spec_path.exists():
        return {"response": "HEDIS technical spec not found."}

    spec = yaml.safe_load(open(spec_path))
    q = req.message.lower()
    measures = spec.get("measure_catalog", {})
    response_lines = []

    if "invert" in q:
        response_lines.append("Inverted measures (lower rate = better, numerator = Non Compliant):\n")
        for code, m in measures.items():
            inv = m.get("inverse") or m.get("ncqa_inverted")
            subs = m.get("sub_measures", {})
            for sc, sinfo in subs.items():
                si = sinfo if isinstance(sinfo, dict) else {}
                if si.get("inverse") or si.get("ncqa_inverted") or inv:
                    name = si.get("name", sinfo) if isinstance(sinfo, dict) else sinfo
                    response_lines.append(f"  {sc}  {name}")

    elif "measure type" in q or "entity" in q or "count" in q:
        types = spec.get("measure_types", {})
        for t, info in types.items():
            response_lines.append(f"  {t}: count {info.get('count_column','')} — {info.get('description','')}")
            response_lines.append(f"    Examples: {', '.join(info.get('examples',[]))}")

    elif "exclusion" in q:
        excls = spec.get("required_exclusions", {})
        for name, info in excls.items():
            response_lines.append(f"  {name}: {info.get('description','')} — applies to: {info.get('applies_to','all')}")

    elif "slicer" in q:
        slicers = spec.get("standard_slicers", {})
        for group, items in slicers.items():
            response_lines.append(f"\n  {group.upper()}:")
            for s in items:
                response_lines.append(f"    {s['name']} → {s.get('column','')}")

    elif "report type" in q:
        rts = spec.get("report_types", {})
        for rt, info in rts.items():
            response_lines.append(f"  {rt}: {info.get('description','')}")
            response_lines.append(f"    Columns: {', '.join(info.get('typical_columns',[])[0:6])}...")

    else:
        # Search measures by code
        found = False
        for code, m in measures.items():
            if code.lower() in q:
                found = True
                response_lines.append(f"  {code} — {m['name']}")
                response_lines.append(f"  Type: {m['measure_type']} | Ages: {m.get('ages','')} | Products: {', '.join(m.get('product_lines',[]))}")
                response_lines.append(f"  Denominator: {m.get('denominator','')}")
                response_lines.append(f"  Numerator: {m.get('numerator','')}")
                response_lines.append(f"  Exclusions: {', '.join(m.get('required_exclusions',[]))}")
                response_lines.append(f"  Star: {'Yes' if m.get('star_rated') else 'No'} | Inverse: {'Yes' if m.get('inverse') else 'No'}")
                subs = m.get("sub_measures", {})
                if len(subs) > 1:
                    response_lines.append(f"  Sub-measures: {', '.join(subs.keys())}")
        if not found:
            response_lines.append("Try asking about: measures (e.g., 'CBP'), inversions, exclusions, slicers, measure types, report types")

    return {"response": "\n".join(response_lines)}

# ---- Plan ----

@app.post("/api/plan")
def api_plan(req: ChatRequest):
    q = req.message.lower()
    data = load_all()
    domain = data["domain"]
    templates = list(domain.get("field_templates", {}).keys())
    report_types = list(domain.get("report_types", {}).keys())

    # Detect report type
    rtype = "MeasureList"
    if "idss" in q: rtype = "IDSSHierarchy"
    elif "provider" in q: rtype = "ProviderDetail"
    elif "gap" in q: rtype = "GapsInCare"

    type_info = domain.get("report_types", {}).get(rtype, {})
    typical_cols = type_info.get("typical_columns", [])

    steps = [
        f"Identify fields for {rtype} report from HEDIS spec → {', '.join(typical_cols[:5])}...",
        f"Map fields to field_templates ({len(templates)} available)",
        f"Set group_by: {type_info.get('typical_group_by', [])}",
        f"Set composite_key: {type_info.get('typical_group_by', [])[:2]}",
        "Add 11 standard slicers + any report-specific ones",
        "Add fixed_filters: isRau=0, isUtilization=0, RN=1",
        "Add cross-field validations (Compliant <= Denominator, etc.)",
        f"Save as skills/reports/{rtype.lower()}.yaml",
        f"Validate with /validate {rtype.lower()}",
        f"Generate SQL with /sql {rtype.lower()}",
    ]

    return {"report_type": rtype, "steps": steps}

# ---- Schema Discovery from Live DB ----

class DiscoverRequest(BaseModel):
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = "HEDIS_RDW"
    schemas: str = "dbo"

class ListTablesRequest(BaseModel):
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = "HEDIS_RDW"

@app.post("/api/list-objects")
def api_list_objects(req: ListTablesRequest):
    """Step 1: Connect and list all database objects without generating YAMLs."""
    try:
        import pymysql
    except ImportError:
        return {"error": "pymysql not installed"}
    try:
        conn = pymysql.connect(host=req.host, port=req.port, user=req.user,
                               password=req.password, database=req.database)
        cur = conn.cursor()
        cur.execute("""
            SELECT TABLE_NAME, TABLE_TYPE, TABLE_ROWS, TABLE_COMMENT
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s
            ORDER BY TABLE_TYPE, TABLE_NAME
        """, (req.database,))
        objects = []
        from pathlib import Path
        schema_dir = Path(__file__).parent.parent / "skills" / "schema"
        for name, ttype, rows, comment in cur.fetchall():
            cur.execute("SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s", (req.database, name))
            col_count = cur.fetchone()[0]
            has_yaml = (schema_dir / f"{name.lower()}.yaml").exists()
            objects.append({
                "name": name,
                "type": "VIEW" if ttype == "VIEW" else "TABLE",
                "rows": rows or 0,
                "columns": col_count,
                "comment": comment or "",
                "has_yaml": has_yaml,
            })
        conn.close()
        return {"objects": objects, "total": len(objects), "database": req.database}
    except Exception as e:
        return {"error": str(e)}

class GenerateRequest(BaseModel):
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = "HEDIS_RDW"
    schemas: str = "dbo"
    selected_tables: list
    version_names: dict = {}

@app.post("/api/generate-schema")
def api_generate_schema(req: GenerateRequest):
    """Step 2: Generate YAMLs only for selected tables."""
    try:
        import pymysql
    except ImportError:
        return {"error": "pymysql not installed"}
    from schema_enricher import enrich_table
    try:
        conn = pymysql.connect(host=req.host, port=req.port, user=req.user,
                               password=req.password, database=req.database)
        cur = conn.cursor()
        results = []
        stats = {"cache_hits": 0, "ollama_hits": 0, "fallback_hits": 0}

        for tname in req.selected_tables:
            cur.execute("SELECT TABLE_ROWS FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s", (req.database, tname))
            row = cur.fetchone()
            trows = row[0] if row else 0

            cur.execute("""
                SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s
                ORDER BY ORDINAL_POSITION
            """, (req.database, tname))

            raw_columns = {}
            for cname, ctype, nullable, ckey in cur.fetchall():
                raw_columns[cname] = {"data_type": ctype.upper(), "nullable": nullable == "YES", "pk": ckey == "PRI"}

            sample_data = {}
            for cname in list(raw_columns.keys())[:30]:
                try:
                    cur.execute(f"SELECT DISTINCT `{cname}` FROM `{tname}` WHERE `{cname}` IS NOT NULL LIMIT 10")
                    sample_data[cname] = [str(r[0]) for r in cur.fetchall()]
                except Exception:
                    pass

            enriched = enrich_table(tname, raw_columns, row_count=trows, sample_data=sample_data)

            es = enriched.get("enrichment_stats", {})
            stats["cache_hits"] += es.get("cache_hits", 0)
            stats["ollama_hits"] += es.get("ollama_hits", 0)
            stats["fallback_hits"] += es.get("fallback_hits", 0)

            # Save YAML with versioning
            import yaml, glob, shutil, datetime
            from pathlib import Path
            save_data = {k: v for k, v in enriched.items() if k != "enrichment_stats"}
            schema_dir = Path(__file__).parent.parent / "skills" / "schema"
            filepath = schema_dir / f"{tname.lower()}.yaml"

            action = "new"
            if filepath.exists():
                # Use custom version name if provided, otherwise auto-increment
                custom_name = req.version_names.get(tname, "")
                if custom_name and not custom_name.endswith('.yaml'):
                    custom_name += '.yaml'
                if custom_name:
                    backup = schema_dir / custom_name
                else:
                    existing_versions = glob.glob(str(schema_dir / f"{tname.lower()}.v*.yaml"))
                    next_v = len(existing_versions) + 1
                    backup = schema_dir / f"{tname.lower()}.v{next_v}.yaml"
                shutil.copy2(filepath, backup)
                action = "overwrite"

            save_data["version"] = (next_v + 1) if filepath.exists() and 'next_v' in dir() else 1
            save_data["last_updated"] = datetime.datetime.now().isoformat()

            with open(filepath, "w") as f:
                yaml.dump(save_data, f, default_flow_style=False, sort_keys=False)

            results.append({"table": tname, "columns": len(raw_columns), "stats": es, "action": action})

        conn.close()
        return {"results": results, "total": len(results), "enrichment": stats}
    except Exception as e:
        return {"error": str(e)}

# ---- Full Schema Edit (add/remove sections, fields, values) ----

@app.get("/api/schema/{table_name}/versions")
def list_versions(table_name: str):
    import glob, yaml
    from pathlib import Path
    schema_dir = Path(__file__).parent.parent / "skills" / "schema"
    versions = []
    # Current
    current = schema_dir / f"{table_name.lower()}.yaml"
    if current.exists():
        doc = yaml.safe_load(open(current))
        versions.append({
            "file": current.name,
            "version": doc.get("version", "current"),
            "last_updated": doc.get("last_updated", ""),
            "current": True,
        })
    # Previous versions
    for p in sorted(glob.glob(str(schema_dir / f"{table_name.lower()}.v*.yaml"))):
        pp = Path(p)
        doc = yaml.safe_load(open(pp))
        versions.append({
            "file": pp.name,
            "version": doc.get("version", pp.stem.split(".v")[-1]),
            "last_updated": doc.get("last_updated", ""),
            "current": False,
        })
    return {"table": table_name, "versions": versions}

@app.post("/api/schema/{table_name}/restore/{version_file}")
def restore_version(table_name: str, version_file: str):
    import shutil, datetime, glob, yaml
    from pathlib import Path
    schema_dir = Path(__file__).parent.parent / "skills" / "schema"
    source = schema_dir / version_file
    target = schema_dir / f"{table_name.lower()}.yaml"
    if not source.exists():
        return {"error": f"Version file '{version_file}' not found"}
    # Backup current before restoring
    if target.exists():
        existing = glob.glob(str(schema_dir / f"{table_name.lower()}.v*.yaml"))
        next_v = len(existing) + 1
        shutil.copy2(target, schema_dir / f"{table_name.lower()}.v{next_v}.yaml")
    shutil.copy2(source, target)
    # Update timestamp
    doc = yaml.safe_load(open(target))
    doc["last_updated"] = datetime.datetime.now().isoformat()
    with open(target, "w") as f:
        yaml.dump(doc, f, default_flow_style=False, sort_keys=False)
    return {"status": "restored", "from": version_file}

class FullEditRequest(BaseModel):
    table_name: str
    yaml_data: dict

@app.post("/api/schema/save")
def api_schema_save(req: FullEditRequest):
    """Save complete table YAML (for full editor)."""
    import yaml
    from pathlib import Path
    filepath = Path(__file__).parent.parent / "skills" / "schema" / f"{req.table_name.lower()}.yaml"
    with open(filepath, "w") as f:
        yaml.dump(req.yaml_data, f, default_flow_style=False, sort_keys=False)
    return {"status": "saved", "table": req.table_name}

@app.post("/api/discover")
def api_discover(req: DiscoverRequest):
    try:
        import pymysql
    except ImportError:
        return {"error": "pymysql not installed. Run: pip install pymysql"}

    from schema_enricher import enrich_table

    try:
        conn = pymysql.connect(host=req.host, port=req.port, user=req.user,
                               password=req.password, database=req.database)
        cur = conn.cursor()

        # Get tables
        cur.execute("SELECT TABLE_NAME, TABLE_ROWS FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s", (req.database,))
        tables_raw = cur.fetchall()

        enriched_tables = {}
        total_cols = 0
        stats = {"cache_hits": 0, "ollama_hits": 0, "fallback_hits": 0}

        for tname, trows in tables_raw:
            # Get columns
            cur.execute("""
                SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
            """, (req.database, tname))
            cols_raw = cur.fetchall()

            raw_columns = {}
            for cname, ctype, nullable, ckey in cols_raw:
                raw_columns[cname] = {
                    "data_type": ctype.upper(),
                    "nullable": nullable == "YES",
                    "pk": ckey == "PRI",
                }
                total_cols += 1

            # Get sample data (10 distinct values per column)
            sample_data = {}
            for cname in list(raw_columns.keys())[:30]:
                try:
                    cur.execute(f"SELECT DISTINCT `{cname}` FROM `{tname}` WHERE `{cname}` IS NOT NULL LIMIT 10")
                    sample_data[cname] = [str(r[0]) for r in cur.fetchall()]
                except Exception:
                    pass

            # Enrich with cache → Ollama → fallback
            enriched = enrich_table(tname, raw_columns, row_count=trows, sample_data=sample_data)
            enriched_tables[tname] = enriched

            es = enriched.get("enrichment_stats", {})
            stats["cache_hits"] += es.get("cache_hits", 0)
            stats["ollama_hits"] += es.get("ollama_hits", 0)
            stats["fallback_hits"] += es.get("fallback_hits", 0)

        conn.close()

        # Save enriched schema as YAML
        import yaml
        from pathlib import Path
        skills_dir = Path(__file__).parent.parent / "skills" / "schema"
        for tname, tdata in enriched_tables.items():
            # Remove enrichment_stats before saving
            save_data = {k: v for k, v in tdata.items() if k != "enrichment_stats"}
            filepath = skills_dir / f"{tname.lower()}.yaml"
            with open(filepath, "w") as f:
                yaml.dump(save_data, f, default_flow_style=False, sort_keys=False)

        return {
            "tables_count": len(enriched_tables),
            "columns_count": total_cols,
            "tables": list(enriched_tables.keys()),
            "enrichment": stats,
        }

    except Exception as e:
        return {"error": str(e)}

# ---- Skills Library ----

@app.get("/api/skills")
def get_skills():
    data = load_all()
    skills = []

    # Schema tables
    for name, t in data["schema"].items():
        cols = t.get("columns", {})
        skills.append({
            "id": f"schema_{name}", "cat": "schema", "name": name,
            "desc": (t.get("description") or "")[:200],
            "tags": t.get("tags", [t.get("classification", "")]),
            "detail": t
        })

    # Joins
    for jid, j in data["joins"].items():
        skills.append({
            "id": f"join_{jid}", "cat": "joins", "name": j.get("name", jid),
            "desc": j.get("description", j.get("sql", "")[:200]),
            "tags": [j.get("join_type", ""), j.get("left_table", ""), j.get("right_table", "")],
            "detail": j
        })

    # Domain
    domain = data["domain"]
    if domain.get("measures"):
        skills.append({
            "id": "domain_measures", "cat": "domain", "name": "HEDIS Measures",
            "desc": f"{len(domain['measures'])} measures defined",
            "tags": ["HEDIS", "measures"],
            "detail": {"count": len(domain["measures"]), "measures": list(domain["measures"].keys())}
        })
    if domain.get("measure_types"):
        skills.append({
            "id": "domain_types", "cat": "domain", "name": "HEDIS Measure Types",
            "desc": "Visit→visitSSUI, Event→eventSSUI, Patient-Process→patientSSUI",
            "tags": ["HEDIS", "measure type"],
            "detail": domain["measure_types"]
        })
    if domain.get("clinical_status_codes"):
        skills.append({
            "id": "domain_clinical", "cat": "domain", "name": "Clinical Status Codes",
            "desc": "16=DVDE, 17=DE, 23=ECC, 24=ERF",
            "tags": ["HEDIS", "clinical", "status"],
            "detail": domain["clinical_status_codes"]
        })
    if domain.get("field_templates"):
        skills.append({
            "id": "domain_templates", "cat": "domain", "name": "Field Templates",
            "desc": f"{len(domain['field_templates'])} field templates defined",
            "tags": ["templates", "fields"],
            "detail": {"count": len(domain["field_templates"]), "templates": list(domain["field_templates"].keys())}
        })
    if domain.get("standard_slicers"):
        for s in domain["standard_slicers"]:
            skills.append({
                "id": f"slicer_{s['name'].replace(' ','_')}", "cat": "slicers",
                "name": f"{s['name']} slicer",
                "desc": f"Column: {s.get('column','')}. {'Required' if s.get('required_for_all') else 'Optional'}.",
                "tags": ["slicer", s["name"]],
                "detail": s
            })
    if domain.get("standard_cross_field_rules"):
        for i, r in enumerate(domain["standard_cross_field_rules"]):
            rule_text = r.get("rule", "") if isinstance(r, dict) else str(r)
            skills.append({
                "id": f"validation_{i}", "cat": "validations",
                "name": rule_text[:80] or f"Validation {i+1}",
                "desc": f"Severity: {r.get('severity','') if isinstance(r,dict) else ''}",
                "tags": ["cross-field", r.get("severity","") if isinstance(r,dict) else ""],
                "detail": r
            })

    # Reports
    for rid, r in data["reports"].items():
        skills.append({
            "id": f"report_{rid}", "cat": "reports", "name": r.get("report_name", rid),
            "desc": f"{len(r.get('fields',[]))} fields, {len(r.get('slicers',[]))} slicers. Status: {r.get('status','')}",
            "tags": ["report", r.get("report_type", ""), r.get("status", "")],
            "detail": {
                "report_type": r.get("report_type"),
                "base_table": r.get("base_table"),
                "fields_count": len(r.get("fields", [])),
                "slicers_count": len(r.get("slicers", [])),
                "composite_key": r.get("composite_key", []),
                "status": r.get("status"),
            }
        })

    return {"skills": skills, "total": len(skills)}

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
        "llm": f"{_model_config['model']} ({_model_config['provider']} · {_model_config['url']})",
    }
