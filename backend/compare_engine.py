"""
Compare Engine — diffs Power BI data (CSV) against SQL results.
"""
import pandas as pd
from io import StringIO

def compare(pbi_csv: str, sql_csv: str, composite_key: list, tolerance: float = 0.01):
    pbi = pd.read_csv(StringIO(pbi_csv))
    sql = pd.read_csv(StringIO(sql_csv))

    result = {
        "pbi_rows": len(pbi),
        "sql_rows": len(sql),
        "matched_rows": 0,
        "mismatched_rows": 0,
        "extra_in_pbi": 0,
        "missing_from_pbi": 0,
        "total_cells": 0,
        "cell_mismatches": 0,
        "mismatches": [],
        "validations": [],
    }

    # Normalize column names
    pbi.columns = [c.strip() for c in pbi.columns]
    sql.columns = [c.strip() for c in sql.columns]

    # Find common columns
    common_cols = [c for c in pbi.columns if c in sql.columns]
    key_cols = [k for k in composite_key if k in common_cols]

    if not key_cols:
        result["error"] = "Composite key columns not found in both datasets"
        return result

    # Merge on composite key
    merged = pbi.merge(sql, on=key_cols, how="outer", suffixes=("_pbi", "_sql"), indicator=True)

    result["extra_in_pbi"] = int((merged["_merge"] == "left_only").sum())
    result["missing_from_pbi"] = int((merged["_merge"] == "right_only").sum())

    both = merged[merged["_merge"] == "both"]
    result["matched_rows"] = len(both)

    # Compare cells
    value_cols = [c for c in common_cols if c not in key_cols]
    for _, row in both.iterrows():
        row_key = " · ".join(str(row[k]) for k in key_cols)
        row_has_mismatch = False

        for col in value_cols:
            pbi_val = row.get(f"{col}_pbi")
            sql_val = row.get(f"{col}_sql")
            result["total_cells"] += 1

            # Handle NaN
            pbi_is_null = pd.isna(pbi_val)
            sql_is_null = pd.isna(sql_val)
            if pbi_is_null and sql_is_null:
                continue

            # Numeric comparison with tolerance
            try:
                pbi_num = float(pbi_val)
                sql_num = float(sql_val)
                if abs(pbi_num - sql_num) <= tolerance:
                    continue
                diff = round(pbi_num - sql_num, 4)
                result["mismatches"].append({
                    "row_key": row_key,
                    "field": col,
                    "pbi_value": str(pbi_val),
                    "sql_value": str(sql_val),
                    "diff": str(diff),
                    "severity": "error"
                })
                result["cell_mismatches"] += 1
                row_has_mismatch = True
                continue
            except (ValueError, TypeError):
                pass

            # String comparison
            if str(pbi_val).strip().lower() != str(sql_val).strip().lower():
                result["mismatches"].append({
                    "row_key": row_key,
                    "field": col,
                    "pbi_value": str(pbi_val),
                    "sql_value": str(sql_val),
                    "diff": "≠",
                    "severity": "error"
                })
                result["cell_mismatches"] += 1
                row_has_mismatch = True

        if row_has_mismatch:
            result["mismatched_rows"] += 1

    total = result["total_cells"]
    result["match_rate"] = round((total - result["cell_mismatches"]) / total * 100, 2) if total > 0 else 100.0

    return result
