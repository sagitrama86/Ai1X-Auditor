"""
Schema Enrichment Pipeline — uses column_mappings cache + Ollama + HEDIS spec
to generate rich table YAMLs from raw schema discovery.
"""
import yaml, json, requests
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent / "skills"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2-vision"


def _load_yaml(path):
    if path.exists():
        return yaml.safe_load(open(path)) or {}
    return {}


def _load_column_cache():
    return _load_yaml(SKILLS_DIR / "domain" / "column_mappings.yaml")


def _save_column_cache(cache):
    with open(SKILLS_DIR / "domain" / "column_mappings.yaml", "w") as f:
        yaml.dump(cache, f, default_flow_style=False, sort_keys=False)


def _load_hedis_context():
    """Load a compact HEDIS context for Ollama (subset to fit context window)."""
    spec = _load_yaml(SKILLS_DIR / "domain" / "hedis_technical_spec.yaml")
    examples = _load_yaml(SKILLS_DIR / "domain" / "discovery_examples.yaml")

    # Build compact context
    parts = []

    # Measure types
    mt = spec.get("measure_types", {})
    if mt:
        parts.append("MEASURE TYPES: " + ", ".join(
            f"{k}: count {v.get('count_column','')} ({', '.join(v.get('examples',[]))})"
            for k, v in mt.items()))

    # Clinical status codes
    cs = spec.get("clinical_status_codes", {})
    for group in cs.values():
        if isinstance(group, dict):
            for code, info in group.items():
                if isinstance(info, dict):
                    parts.append(f"STATUS {code}: {info.get('label','')} — {info.get('meaning','')}")

    # Compliance calculation
    cc = spec.get("compliance_calculation", {})
    if cc.get("standard"):
        parts.append(f"COMPLIANCE: {cc['standard'].get('formula','')}")
    if cc.get("inverted"):
        parts.append(f"INVERTED COMPLIANCE: {cc['inverted'].get('formula','')}")

    # Standard filters
    sf = spec.get("standard_filters", {})
    for f in sf.get("required_for_all_quality_reports", []):
        if isinstance(f, dict):
            parts.append(f"REQUIRED FILTER: {f.get('column','')}={f.get('value','')} — {f.get('reason','')}")

    # Measures (compact)
    measures = spec.get("measure_catalog", {})
    for code, m in measures.items():
        parts.append(f"MEASURE {code}: {m.get('name','')} type={m.get('measure_type','')} inverse={m.get('inverse',False)}")

    # Few-shot examples (first 3)
    ex = examples.get("examples", [])[:3]
    for e in ex:
        if "raw" in e and "enriched" in e:
            parts.append(f"EXAMPLE: column '{e['raw'].get('column','')}' in {e['raw'].get('table','')} → "
                         f"business_name='{e['enriched'].get('business_name','')}', "
                         f"semantic_role={e['enriched'].get('semantic_role','')}, "
                         f"aggregatable={e['enriched'].get('aggregatable','')}")

    return "\n".join(parts)


def _call_ollama(prompt, system_prompt):
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False
        }, timeout=30)
        if resp.status_code == 200:
            return resp.json().get("response", "")
    except Exception:
        pass
    return None


def _enrich_column_ollama(col_name, col_info, table_name, table_cols, hedis_context):
    """Ask Ollama to enrich a single column."""
    system = f"""You are a HEDIS healthcare data expert. Given a database column, generate its metadata.

{hedis_context}

SEMANTIC ROLES: identifier, dimension, measure, flag, date, lookup, metric, code, status
AGGREGATION BEHAVIORS: additive, semi_additive, non_additive

Respond ONLY with valid JSON (no markdown):
{{"business_name":"...","description":"...","semantic_role":"...","aggregatable":true/false,"default_aggregation":"SUM/COUNT/null","aggregation_behavior":"additive/non_additive","filterable":true/false,"sortable":true/false,"groupable":true/false,"categorical":true/false,"allowed_values":{{}},"business_rules":[]}}"""

    other_cols = [c for c in table_cols if c != col_name][:10]
    prompt = (f"Table: {table_name}\n"
              f"Column: {col_name}\n"
              f"Type: {col_info.get('data_type','')}\n"
              f"Nullable: {col_info.get('nullable','')}\n"
              f"PK: {col_info.get('pk','')}\n"
              f"Sample values: {col_info.get('sample_values',[])}\n"
              f"Other columns in table: {', '.join(other_cols)}")

    raw = _call_ollama(prompt, system)
    if raw:
        try:
            # Extract JSON
            import re
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except (json.JSONDecodeError, Exception):
            pass
    return None


def _infer_basic(col_name, data_type, nullable, pk, sample_values=None):
    """Rule-based fallback when Ollama is unavailable."""
    dt = (data_type or "").upper()
    name_lower = col_name.lower()
    result = {"business_name": col_name}

    # PK
    if pk:
        result["semantic_role"] = "identifier"
        result["aggregatable"] = False
        result["aggregation_behavior"] = "non_additive"
        return result

    # Flags
    if dt in ("BIT", "TINYINT(1)") or name_lower.startswith("is"):
        result["semantic_role"] = "flag"
        result["aggregatable"] = False
        result["filterable"] = True
        result["categorical"] = True
        return result

    # Dates
    if "date" in name_lower or "year" in name_lower or dt in ("DATE", "DATETIME", "TIMESTAMP"):
        result["semantic_role"] = "date"
        result["filterable"] = True
        result["sortable"] = True
        result["groupable"] = True
        return result

    # IDs / lookups
    if name_lower.endswith("id") and dt in ("INT", "BIGINT"):
        result["semantic_role"] = "lookup"
        result["aggregatable"] = False
        return result

    # Names / descriptions
    if "name" in name_lower or "desc" in name_lower:
        result["semantic_role"] = "dimension"
        result["filterable"] = True
        result["sortable"] = True
        result["groupable"] = True
        result["categorical"] = True
        return result

    # Codes
    if "code" in name_lower or "type" in name_lower or "status" in name_lower:
        result["semantic_role"] = "code"
        result["filterable"] = True
        result["groupable"] = True
        result["categorical"] = True
        return result

    # Numeric measures
    if dt in ("INT", "BIGINT", "DECIMAL", "FLOAT", "NUMERIC") and not name_lower.endswith("id"):
        result["semantic_role"] = "measure"
        result["aggregatable"] = True
        result["default_aggregation"] = "SUM"
        result["aggregation_behavior"] = "additive"
        return result

    # Default: dimension
    result["semantic_role"] = "dimension"
    result["filterable"] = True
    result["groupable"] = True
    return result


def enrich_table(table_name, raw_columns, row_count=None, sample_data=None):
    """
    Enrich a raw table schema using:
    1. Column mappings cache (exact match)
    2. Ollama + HEDIS context (cache miss)
    3. Rule-based fallback (if Ollama unavailable)
    """
    cache = _load_column_cache()
    hedis_context = None  # lazy load
    enriched_columns = {}
    cache_hits = 0
    ollama_hits = 0
    fallback_hits = 0
    col_names = list(raw_columns.keys())

    for col_name, col_info in raw_columns.items():
        # 1. Check cache
        if col_name in cache:
            enriched = dict(cache[col_name])
            enriched["data_type"] = col_info.get("data_type", "")
            enriched["nullable"] = col_info.get("nullable", True)
            enriched["pk"] = col_info.get("pk", False)
            enriched_columns[col_name] = enriched
            cache_hits += 1
            continue

        # 2. Try Ollama
        if hedis_context is None:
            hedis_context = _load_hedis_context()

        samples = []
        if sample_data and col_name in sample_data:
            samples = sample_data[col_name]
        col_with_samples = dict(col_info)
        col_with_samples["sample_values"] = samples

        ollama_result = _enrich_column_ollama(col_name, col_with_samples, table_name, col_names, hedis_context)
        if ollama_result:
            ollama_result["data_type"] = col_info.get("data_type", "")
            ollama_result["nullable"] = col_info.get("nullable", True)
            ollama_result["pk"] = col_info.get("pk", False)
            enriched_columns[col_name] = ollama_result
            # Save to cache
            cache[col_name] = {k: v for k, v in ollama_result.items() if k not in ("data_type", "nullable", "pk")}
            ollama_hits += 1
            continue

        # 3. Rule-based fallback
        enriched = _infer_basic(col_name, col_info.get("data_type"), col_info.get("nullable"), col_info.get("pk"), samples)
        enriched["data_type"] = col_info.get("data_type", "")
        enriched["nullable"] = col_info.get("nullable", True)
        enriched["pk"] = col_info.get("pk", False)
        enriched_columns[col_name] = enriched
        fallback_hits += 1

    # Save updated cache
    _save_column_cache(cache)

    # Detect table classification
    name_lower = table_name.lower()
    classification = "dimension"
    if "fact" in name_lower:
        classification = "fact"
    elif "dim" in name_lower:
        classification = "dimension"
    elif any(x in name_lower for x in ("cutpoint", "mapping", "lookup", "ref")):
        classification = "lookup"

    # Detect grain from PKs
    pk_cols = [c for c, info in enriched_columns.items() if info.get("pk")]

    # Load join patterns
    join_patterns = _load_yaml(SKILLS_DIR / "domain" / "join_patterns.yaml")
    detected_joins = []
    for jid, jp in join_patterns.get("join_patterns", {}).items():
        if jp.get("left") == table_name or jp.get("right") == table_name:
            detected_joins.append({
                "table": jp["right"] if jp["left"] == table_name else jp["left"],
                "join_type": jp.get("join_type", "INNER"),
                "on": jp.get("on", []),
                "on_expression": jp.get("on_expression", ""),
                "relationship": jp.get("relationship", ""),
                "purpose": jp.get("purpose", ""),
                "note": jp.get("note", ""),
            })

    result = {
        "version": 1.0,
        "table_name": table_name,
        "schema": "dbo",
        "database": "HEDIS_RDW",
        "classification": classification,
        "description": "",
        "domain": "Quality Reporting",
        "subject_area": "HEDIS",
        "row_count_approx": row_count,
        "grain": {
            "description": "",
            "columns": pk_cols,
            "composite_primary_key": pk_cols,
        },
        "joins_with": detected_joins,
        "columns": enriched_columns,
        "enrichment_stats": {
            "cache_hits": cache_hits,
            "ollama_hits": ollama_hits,
            "fallback_hits": fallback_hits,
            "total": len(raw_columns),
        }
    }

    return result
