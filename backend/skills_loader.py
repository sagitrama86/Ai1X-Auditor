"""
Skills loader — reads all YAMLs into memory.
"""
import os, yaml
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent / "skills"

def _load_yaml(path):
    with open(path) as f:
        docs = list(yaml.safe_load_all(f))
    return docs[0] if len(docs) == 1 else docs

def load_schema():
    tables = {}
    for p in (SKILLS_DIR / "schema").glob("*.yaml"):
        doc = _load_yaml(p)
        if isinstance(doc, list):
            for d in doc:
                if "table_name" in d:
                    tables[d["table_name"]] = d
        elif "table_name" in doc:
            tables[doc["table_name"]] = doc
    return tables

def load_joins():
    joins = {}
    for p in (SKILLS_DIR / "joins").glob("*.yaml"):
        docs = _load_yaml(p)
        if not isinstance(docs, list):
            docs = [docs]
        for d in docs:
            if "join_id" in d:
                joins[d["join_id"]] = d
    return joins

def load_domain():
    path = SKILLS_DIR / "domain" / "hedis_foundation.yaml"
    return _load_yaml(path) if path.exists() else {}

def load_reports():
    reports = {}
    for p in (SKILLS_DIR / "reports").glob("*.yaml"):
        doc = _load_yaml(p)
        if "report_id" in doc:
            reports[doc["report_id"]] = doc
    return reports

def load_all():
    return {
        "schema": load_schema(),
        "joins": load_joins(),
        "domain": load_domain(),
        "reports": load_reports(),
    }
