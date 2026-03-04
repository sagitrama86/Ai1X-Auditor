"""
AI Chat — Ollama integration with few-shot prompting + post-processing validation.
"""
import requests, json, re
from skills_loader import load_all

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2-vision"

def _build_system_prompt(data):
    domain = data["domain"]
    tables = list(data["schema"].keys())
    measures = list(domain.get("measures", {}).keys())
    templates = list(domain.get("field_templates", {}).keys())
    report_types = domain.get("report_types", {})
    std_slicers = domain.get("standard_slicers", [])
    std_rules = domain.get("standard_cross_field_rules", [])
    std_filters = domain.get("standard_fixed_filters", [])

    # Build report types summary
    rt_summary = ""
    for rtype, rinfo in report_types.items():
        rt_summary += f"\n  {rtype}: group_by={rinfo.get('typical_group_by')}, columns={rinfo.get('typical_columns')}"

    slicer_names = [s["name"] for s in std_slicers]
    rule_texts = [r.get("rule","") if isinstance(r,dict) else r for r in std_rules]
    filter_texts = [f"{f['column']}={f['value']}" if isinstance(f,dict) else f for f in std_filters]

    return f"""You are a HEDIS healthcare quality reporting expert. You help create Power BI report validation definitions.

DATABASE TABLES: {', '.join(tables)}
HEDIS MEASURES: {', '.join(measures)}
AVAILABLE FIELD TEMPLATES: {', '.join(templates)}
ALLOWED DATA TYPES: String, Integer, Decimal, Percentage, Date, Datetime

REPORT TYPES:{rt_summary}

STANDARD SLICERS (always include ALL 11): {', '.join(slicer_names)}
STANDARD FIXED FILTERS: {', '.join(filter_texts)}
STANDARD CROSS-FIELD RULES: {'; '.join(rule_texts[:5])}

CRITICAL RULES:
- group_by must include ALL non-aggregate columns from the field list
- composite_key identifies unique rows — typically Measures + Submission (+ extra for breakdowns)
- ALL 11 standard slicers must be included, plus any report-specific ones
- cross_field_validations use operators: <=, >=, ==, +
- data_type must be one of: String, Integer, Decimal, Percentage, Date, Datetime
- Always include fixed_filters: isRaw=0, isUtilization=0, RN=1
- Always include deduplication: ROW_NUMBER on factssui+SubmissionId

EXAMPLE — When user says "Create MeasureList report with Measures, Submission, Compliance %, Denominator, Compliant":

```json
{{
  "report_name": "MeasureList",
  "report_type": "MeasureList",
  "fields": [
    {{"display_name": "Measures", "template_ref": "Measures", "data_type": "String", "is_aggregate": false}},
    {{"display_name": "Submission", "template_ref": "Submission", "data_type": "String", "is_aggregate": false}},
    {{"display_name": "Compliance %", "template_ref": "Compliance %", "data_type": "Percentage", "is_aggregate": true}},
    {{"display_name": "Denominator", "template_ref": "Denominator", "data_type": "Integer", "is_aggregate": true}},
    {{"display_name": "Compliant", "template_ref": "Compliant", "data_type": "Integer", "is_aggregate": true}}
  ],
  "group_by": ["Measures", "Submission"],
  "sort_by": [{{"column": "Measures", "direction": "ASC"}}, {{"column": "Submission", "direction": "ASC"}}],
  "composite_key": ["Measures", "Submission"],
  "slicers": ["Organization Name", "Measurement Year", "Line of Business", "Business Group", "Submission", "Products", "Health Plans", "NCQA Domain", "Health Category", "Measures", "Enrollment Status"],
  "fixed_filters": ["isRaw = 0", "isUtilization = 0", "RN = 1"],
  "cross_field_validations": [
    {{"left": "Compliant", "operator": "<=", "right": "Denominator", "severity": "error"}},
    {{"left": "Compliant + Non Compliant", "operator": "==", "right": "Denominator", "severity": "error"}}
  ],
  "gaps": []
}}
```

Respond ONLY with valid JSON in this exact format. No markdown, no explanation before or after the JSON."""


def _call_ollama(prompt, system_prompt):
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False
        }, timeout=45)
        if resp.status_code == 200:
            return resp.json().get("response", "")
    except Exception:
        return None
    return None


def _extract_json(text):
    """Extract JSON from LLM response, handling markdown code blocks."""
    # Try to find JSON in code blocks
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Try raw JSON
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


def _validate_and_fix(report_json, data):
    """Post-process LLM output to ensure correctness using HEDIS foundation."""
    domain = data["domain"]
    templates = domain.get("field_templates", {})
    report_types = domain.get("report_types", {})
    std_slicers = domain.get("standard_slicers", [])
    std_rules = domain.get("standard_cross_field_rules", [])
    allowed_types = {"String", "Integer", "Decimal", "Percentage", "Date", "Datetime"}

    fixes = []

    # 1. Fix report_type detection
    rname = (report_json.get("report_name", "") + " " + report_json.get("report_type", "")).lower()
    detected_type = "MeasureList"
    if "idss" in rname:
        detected_type = "IDSSHierarchy"
    elif "provider" in rname:
        detected_type = "ProviderDetail"
    elif "gap" in rname:
        detected_type = "GapsInCare"
    report_json["report_type"] = detected_type

    # 2. Fix data types
    for field in report_json.get("fields", []):
        tref = field.get("template_ref", "")
        tmpl = templates.get(tref, {})

        # Fix data type from template
        tmpl_type = tmpl.get("data_type", "")
        if tmpl_type in allowed_types:
            if field.get("data_type") != tmpl_type:
                fixes.append(f"Fixed data type for '{field['display_name']}': {field.get('data_type')} → {tmpl_type}")
                field["data_type"] = tmpl_type
        elif field.get("data_type") not in allowed_types:
            # Map common LLM mistakes
            dt_map = {"string": "String", "text": "String", "numeric": "Integer", "number": "Integer", "float": "Decimal", "percent": "Percentage"}
            old = field["data_type"]
            field["data_type"] = dt_map.get(old.lower(), "String") if old else "String"
            fixes.append(f"Fixed data type for '{field['display_name']}': {old} → {field['data_type']}")

        # Fix is_aggregate from template
        if "is_aggregate" in tmpl:
            field["is_aggregate"] = tmpl["is_aggregate"]

    # 3. Fix group_by — must include all non-aggregate fields
    field_names = [f["display_name"] for f in report_json.get("fields", [])]
    non_agg = [f["display_name"] for f in report_json.get("fields", []) if not f.get("is_aggregate", False)]
    type_info = report_types.get(detected_type, {})
    expected_gb = type_info.get("typical_group_by", non_agg)

    current_gb = report_json.get("group_by", [])
    if isinstance(current_gb, list) and len(current_gb) > 0 and isinstance(current_gb[0], dict):
        current_gb = [g.get("field", g.get("column", "")) for g in current_gb]

    if set(current_gb) != set(expected_gb):
        fixes.append(f"Fixed group_by: {current_gb} → {expected_gb}")
        report_json["group_by"] = expected_gb

    # 4. Fix composite_key
    current_ck = report_json.get("composite_key", [])
    if isinstance(current_ck, list) and len(current_ck) > 0 and isinstance(current_ck[0], dict):
        current_ck = [c.get("field", c.get("column", "")) for c in current_ck]

    # For IDSS, composite key should include Source Feed Type + Source System
    if detected_type == "IDSSHierarchy":
        expected_ck = ["Measures", "Submission", "Source Feed Type", "Source System"]
    else:
        expected_ck = expected_gb[:2] if len(expected_gb) >= 2 else expected_gb

    if set(current_ck) != set(expected_ck):
        fixes.append(f"Fixed composite_key: {current_ck} → {expected_ck}")
    report_json["composite_key"] = expected_ck

    # 5. Fix slicers — must include all 11 standard + any extras
    slicer_names = [s["name"] for s in std_slicers]
    current_slicers = report_json.get("slicers", [])
    if isinstance(current_slicers, list) and len(current_slicers) > 0 and isinstance(current_slicers[0], dict):
        current_slicers = [s.get("field", s.get("name", "")) for s in current_slicers]

    if set(current_slicers) != set(slicer_names):
        fixes.append(f"Fixed slicers: added {len(slicer_names) - len(set(current_slicers) & set(slicer_names))} missing standard slicers")
    report_json["slicers"] = slicer_names

    # 6. Fix fixed_filters
    report_json["fixed_filters"] = ["isRaw = 0", "isUtilization = 0", "RN = 1"]

    # 7. Fix cross_field_validations
    validated_rules = []
    for rule in std_rules:
        rule_text = rule.get("rule", "") if isinstance(rule, dict) else ""
        severity = rule.get("severity", "error") if isinstance(rule, dict) else "error"
        applies = rule.get("applies_when", "") if isinstance(rule, dict) else ""

        # Check if the fields in this rule exist in our report
        rule_lower = rule_text.lower()
        fields_lower = [f.lower() for f in field_names]

        should_add = False
        if "compliant" in rule_lower and "denominator" in rule_lower:
            if "compliant" in fields_lower and "denominator" in fields_lower:
                should_add = True
        elif "compliance" in rule_lower and "compliance %" in fields_lower:
            should_add = True
        elif "exclusion" in rule_lower:
            if any("exclusion" in f for f in fields_lower) and "denominator" in fields_lower:
                should_add = True
        elif "pctl" in rule_lower:
            if any("pctl" in f for f in fields_lower):
                should_add = True
        elif "vde" in rule_lower or "ede" in rule_lower:
            if any(x in fields_lower for x in ["vde", "ede", "ecc", "erf"]):
                should_add = True

        if should_add:
            validated_rules.append({"rule": rule_text, "severity": severity})

    report_json["cross_field_validations"] = validated_rules
    if len(validated_rules) != len(report_json.get("cross_field_validations_original", [])):
        fixes.append(f"Auto-generated {len(validated_rules)} cross-field validations from HEDIS rules")

    # 8. Detect gaps — columns in typical_columns but not in user's list
    gaps = []
    typical = type_info.get("typical_columns", [])
    for tc in typical:
        if tc not in field_names and not any(tc.lower() in f.lower() for f in field_names):
            gaps.append(f"HEDIS expects '{tc}' for {detected_type} reports — not in your column list")
    report_json["gaps"] = gaps

    # 9. Add sort_by
    report_json["sort_by"] = [{"column": c, "direction": "ASC"} for c in expected_gb[:2]]

    # 10. Add deduplication
    report_json["deduplication"] = {
        "method": "ROW_NUMBER",
        "partition_by": ["factssui", "SubmissionId"],
        "filter": "RN = 1"
    }

    report_json["_fixes_applied"] = fixes
    return report_json


def _format_response(report_json):
    """Format the validated report JSON into a human-readable chat response."""
    fields = report_json.get("fields", [])
    gaps = report_json.get("gaps", [])
    rules = report_json.get("cross_field_validations", [])
    fixes = report_json.get("_fixes_applied", [])
    slicers = report_json.get("slicers", [])

    lines = []
    lines.append(f"I'll create the **{report_json.get('report_type', '')}** report: **{report_json.get('report_name', '')}**\n")

    lines.append(f"**Fields ({len(fields)}):**")
    for f in fields:
        lines.append(f"  ✅ {f['display_name']} → {f['data_type']} {'(aggregate)' if f.get('is_aggregate') else ''}")

    lines.append(f"\n**Auto-generated:**")
    lines.append(f"  • Report Type: {report_json.get('report_type')}")
    lines.append(f"  • Group By: {', '.join(report_json.get('group_by', []))}")
    lines.append(f"  • Sort By: {', '.join(s['column']+' '+s['direction'] for s in report_json.get('sort_by', []))}")
    lines.append(f"  • Composite Key: {' + '.join(report_json.get('composite_key', []))}")
    lines.append(f"  • Slicers: {len(slicers)} standard HEDIS slicers")
    lines.append(f"  • Fixed Filters: {', '.join(report_json.get('fixed_filters', []))}")
    lines.append(f"  • Deduplication: ROW_NUMBER on factssui + SubmissionId")

    lines.append(f"\n**Cross-Field Validations ({len(rules)}):**")
    for r in rules:
        sev = "✕ error" if r["severity"] == "error" else "⚠ warning"
        lines.append(f"  ✅ {r['rule']} ({sev})")

    if gaps:
        lines.append(f"\n**⚠ Gaps Found ({len(gaps)}):**")
        for g in gaps:
            lines.append(f"  ⚠️ {g}")
    else:
        lines.append(f"\n**Gaps: None** — all expected columns present ✅")

    if fixes:
        lines.append(f"\n**🔧 Auto-corrections ({len(fixes)}):**")
        for f in fixes:
            lines.append(f"  🔧 {f}")

    lines.append(f"\n**Cross-Report Validations:**")
    lines.append(f"  ✅ Denominator should match MeasureList for same Measure+Submission")

    lines.append(f"\nShall I save this report and generate the SQL?")

    return "\n".join(lines)


def chat(user_input: str) -> str:
    data = load_all()
    lower = user_input.lower()

    # Only use LLM for report creation
    if "create" in lower and "report" in lower:
        system_prompt = _build_system_prompt(data)
        llm_response = _call_ollama(user_input, system_prompt)

        if llm_response:
            report_json = _extract_json(llm_response)
            if report_json:
                validated = _validate_and_fix(report_json, data)
                # Store in memory for save step
                _last_report[0] = validated
                return _format_response(validated)

        # Fallback: build from templates directly (no LLM)
        validated = _rule_based_create_json(user_input, data)
        _last_report[0] = validated
        return _format_response(validated)

    # Save the last created report
    if ("save" in lower or "yes" in lower) and _last_report[0]:
        return _save_report(_last_report[0])

    # For non-create queries, use simple rule-based
    return _rule_based_other(user_input, data)


def _rule_based_create(user_input, data):
    """Create report without LLM — pure rule-based using HEDIS foundation."""
    validated = _rule_based_create_json(user_input, data)
    return _format_response(validated)


def _rule_based_create_json(user_input, data):
    """Create report JSON without LLM."""
    domain = data["domain"]
    templates = domain.get("field_templates", {})
    report_types = domain.get("report_types", {})
    lower = user_input.lower()

    # Detect report type
    detected_type = "MeasureList"
    if "idss" in lower: detected_type = "IDSSHierarchy"
    elif "provider" in lower: detected_type = "ProviderDetail"
    elif "gap" in lower: detected_type = "GapsInCare"

    # Match columns
    fields = []
    for tname, tmpl in templates.items():
        if tname.lower() in lower or any(w in lower for w in tname.lower().split()):
            dt = tmpl.get("data_type", "String")
            if dt not in {"String","Integer","Decimal","Percentage","Date","Datetime"}:
                dt = "String"
            fields.append({
                "display_name": tname,
                "template_ref": tname,
                "data_type": dt,
                "is_aggregate": tmpl.get("is_aggregate", False)
            })

    report_json = {
        "report_name": user_input.split("report")[1].split(".")[0].split("with")[0].strip() if "report" in lower else "New Report",
        "report_type": detected_type,
        "fields": fields,
        "group_by": [],
        "composite_key": [],
        "slicers": [],
        "cross_field_validations": [],
    }

    return _validate_and_fix(report_json, data)


# In-memory store for last created report (for save step)
_last_report = [None]


def _save_report(report_json):
    """Save report JSON as YAML to skills/reports/."""
    import yaml
    from pathlib import Path

    name = report_json.get("report_name", "new_report")
    report_id = name.lower().replace(" ", "_").replace("-", "_").replace("__", "_").strip("_")

    # Build the YAML structure matching measurelist.yaml format
    yaml_data = {
        "report_id": report_id,
        "report_name": name,
        "report_type": report_json.get("report_type", "MeasureList"),
        "base_table": "factqualityreport",
        "status": "ready",
        "description": f"Auto-generated report: {name}",
        "fixed_filters": report_json.get("fixed_filters", ["F.isRaw = 0", "F.isUtilization = 0", "RN = 1"]),
        "deduplication": report_json.get("deduplication", {
            "method": "ROW_NUMBER",
            "partition_by": ["F.factSSUI", "F.SubmissionID"],
            "order_by": "F.factSSUI, F.SubmissionID ASC",
            "filter": "RN = 1"
        }),
        "composite_key": report_json.get("composite_key", []),
        "duplicate_rows_per_composite_key": False,
        "duplicate_rows_per_all_columns": False,
        "sort_by": report_json.get("sort_by", []),
        "fields": [],
        "slicers": [],
        "cross_field_validations": [],
    }

    # Fields
    for f in report_json.get("fields", []):
        yaml_data["fields"].append({
            "display_name": f["display_name"],
            "template_ref": f.get("template_ref", f["display_name"]),
            "data_type": f.get("data_type", "String"),
            "allow_null": f.get("data_type") in ("Integer",) and f.get("is_aggregate", False),
        })

    # Slicers
    for s in report_json.get("slicers", []):
        yaml_data["slicers"].append({"name": s, "required": s in ("Organization Name", "Measurement Year")})

    # Cross-field validations
    for r in report_json.get("cross_field_validations", []):
        yaml_data["cross_field_validations"].append(r)

    # Write YAML
    skills_dir = Path(__file__).parent.parent / "skills" / "reports"
    filepath = skills_dir / f"{report_id}.yaml"
    with open(filepath, "w") as f:
        yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    _last_report[0] = None  # Clear after save

    return f"""✅ **Report saved!**

**File:** `skills/reports/{report_id}.yaml`
**Report ID:** `{report_id}`
**Fields:** {len(yaml_data['fields'])}
**Slicers:** {len(yaml_data['slicers'])}
**Validations:** {len(yaml_data['cross_field_validations'])}

The report is now available on the **Reports** page and ready for:
  • SQL generation → go to **SQL Output**
  • Data comparison → go to **Compare**

What would you like to do next?"""


def _rule_based_other(user_input, data):
    """Handle non-create queries."""
    lower = user_input.lower()

    if "measure" in lower and ("what" in lower or "show" in lower or "list" in lower):
        measures = data["domain"].get("measures", {})
        lines = ["Here are the HEDIS measures I know about:\n"]
        for code, info in measures.items():
            lines.append(f"  **{code}** — {info['name']} (type: {info['measure_type']}, domain: {info['domain']})")
        return "\n".join(lines)

    elif "schema" in lower or "table" in lower:
        tables = data["schema"]
        tname = None
        for t in tables:
            if t.lower() in lower:
                tname = t
                break
        if tname:
            t = tables[tname]
            cols = list(t.get("columns", {}).keys())
            return f"**{tname}** ({t.get('classification','')}, ~{t.get('row_count_approx','')} rows)\n\n{t.get('description','')}\n\n**Columns ({len(cols)}):** {', '.join(cols[:15])}{'...' if len(cols)>15 else ''}"
        else:
            lines = ["Tables in the schema:\n"]
            for name, t in tables.items():
                lines.append(f"  **{name}** — {t.get('classification','')} ({t.get('row_count_approx','')} rows)")
            return "\n".join(lines)

    elif "sql" in lower or "generate" in lower:
        return "To generate SQL, go to the **SQL Output** page or tell me which report and slicer values you want.\n\nExample: 'Generate SQL for MeasureList with Organization=Acme Health and Year=2024'"

    else:
        return f"I can help with:\n\n• **Create a report** — 'Create report IDSS Hierarchy with columns...'\n• **Show measures** — 'What HEDIS measures do you know?'\n• **Explore schema** — 'Show me the schema for factqualityreport'\n• **Generate SQL** — 'Generate SQL for MeasureList'\n\nWhat would you like to do?"
