"""
AI1X CLI — Terminal interface for AI1X Auditor
"""
import sys
import json
import requests
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt

API = "http://localhost:8000"
console = Console()

COMMANDS = {
    "/help":    "Show available commands",
    "/schema":  "Browse schema — /schema [table_name]",
    "/reports": "List reports — /reports [report_id]",
    "/sql":     "Generate SQL — /sql <report_id> [--slicer value]",
    "/compare": "Compare CSVs — /compare <pbi.csv> <sql.csv>",
    "/skills":  "Browse skills library",
    "/health":  "Check backend status",
    "/clear":   "Clear screen",
    "/quit":    "Exit",
}


def api_get(path):
    try:
        r = requests.get(f"{API}{path}", timeout=10)
        return r.json()
    except Exception as e:
        console.print(f"[red]✕ Backend error: {e}[/red]")
        return None


def api_post(path, data):
    try:
        r = requests.post(f"{API}{path}", json=data, timeout=60)
        return r.json()
    except Exception as e:
        console.print(f"[red]✕ Backend error: {e}[/red]")
        return None


def show_help():
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan bold")
    table.add_column(style="dim")
    for cmd, desc in COMMANDS.items():
        table.add_row(cmd, desc)
    console.print(table)
    console.print("\n[dim]Or just type a message to chat with the AI.[/dim]")


def show_health():
    data = api_get("/api/health")
    if not data:
        return
    console.print(f"[green]✓[/green] Status: {data['status']}")
    console.print(f"  Tables: {data.get('schema_tables', 0)} · Joins: {data.get('joins', 0)} · Reports: {data.get('reports', 0)}")
    console.print(f"  Measures: {data.get('hedis_measures', 0)} · Templates: {data.get('field_templates', 0)}")


def show_schema(args):
    if args:
        table_name = args[0]
        data = api_get(f"/api/schema/{table_name}")
        if not data or data.get("error"):
            console.print(f"[red]✕ {data.get('error', 'Not found')}[/red]")
            return
        cols = data.get("columns", {})
        desc = data.get("description", "")
        console.print(Panel(
            f"[dim]{desc}[/dim]",
            title=f"[bold]{table_name}[/bold] — {data.get('classification', '')} · {len(cols)} columns · ~{data.get('row_count_approx', '?')} rows",
            border_style="blue"
        ))
        table = Table(show_lines=False, padding=(0, 1))
        table.add_column("#", style="dim", width=3)
        table.add_column("Column", style="bold")
        table.add_column("Type", style="cyan")
        table.add_column("Role", style="magenta")
        table.add_column("Null", width=4)
        table.add_column("Key", style="yellow")
        table.add_column("Description", style="dim", max_width=40)
        for i, (cname, cdef) in enumerate(cols.items(), 1):
            null = "[green]✓[/green]" if cdef.get("nullable", True) else "[red]✕[/red]"
            key = "PK" if cdef.get("pk") else (cdef.get("fk") or "—")
            desc = (cdef.get("description") or cdef.get("record_level_info") or cdef.get("grain") or "")[:40]
            role = cdef.get("semantic_role", "")
            table.add_row(str(i), cname, cdef.get("data_type", ""), role, null, key, desc)
        console.print(table)
    else:
        data = api_get("/api/schema")
        if not data:
            return
        table = Table(title="Schema", show_lines=False, padding=(0, 1))
        table.add_column("Table", style="bold")
        table.add_column("Type", style="cyan")
        table.add_column("Columns", justify="right")
        table.add_column("Rows", justify="right", style="dim")
        for t in data.get("tables", []):
            table.add_row(t["table_name"], t.get("classification", ""), str(t["columns_count"]), str(t.get("row_count") or "—"))
        console.print(table)


def show_reports(args):
    if args:
        data = api_get(f"/api/reports/{args[0]}")
        if not data or data.get("error"):
            console.print(f"[red]✕ {data.get('error', 'Not found')}[/red]")
            return
        console.print(Panel(
            f"[dim]{data.get('description', '')}[/dim]",
            title=f"[bold]{data.get('report_name', '')}[/bold] — {data.get('status', '')}",
            border_style="green"
        ))
        fields = data.get("fields", [])
        table = Table(title=f"Fields ({len(fields)})", show_lines=False, padding=(0, 1))
        table.add_column("Name", style="bold")
        table.add_column("Type", style="cyan")
        table.add_column("Null", width=4)
        for f in fields:
            null = "[green]✓[/green]" if f.get("allow_null", True) else "[red]✕[/red]"
            table.add_row(f["display_name"], f.get("data_type", ""), null)
        console.print(table)

        slicers = data.get("slicers", [])
        console.print(f"\n[bold]Slicers ({len(slicers)}):[/bold]")
        for s in slicers:
            req = "[yellow]required[/yellow]" if s.get("required") else "[dim]optional[/dim]"
            console.print(f"  {s['name']} {req}")
    else:
        data = api_get("/api/reports")
        if not data:
            return
        for r in data.get("reports", []):
            console.print(f"  [bold]{r['report_id']}[/bold] — {r.get('report_name', '')} · {r['fields_count']} fields · {r['slicers_count']} slicers · [green]{r.get('status', '')}[/green]")


def generate_sql(args):
    if not args:
        console.print("[red]Usage: /sql <report_id> [--slicer value ...][/red]")
        return
    report_id = args[0]
    slicers = {}
    i = 1
    while i < len(args) - 1:
        if args[i].startswith("--"):
            key = args[i][2:].replace("-", " ").title()
            slicers[key] = args[i + 1]
            i += 2
        else:
            i += 1

    data = api_post("/api/generate-sql", {"report_id": report_id, "slicers": slicers})
    if not data:
        return
    sql = data.get("sql", "")
    lines = sql.count("\n") + 1
    console.print(f"\n[green]⚡ Generated {lines} lines of SQL for [bold]{report_id}[/bold][/green]")
    if slicers:
        console.print(f"[dim]   Slicers: {slicers}[/dim]")
    console.print()
    console.print(Panel(sql, title="SQL", border_style="magenta", expand=False))


def compare_csvs(args):
    if len(args) < 2:
        console.print("[red]Usage: /compare <pbi.csv> <sql.csv> [key1 key2 ...][/red]")
        return
    try:
        pbi = open(args[0]).read()
        sql = open(args[1]).read()
    except FileNotFoundError as e:
        console.print(f"[red]✕ {e}[/red]")
        return

    keys = args[2:] if len(args) > 2 else ["Measures", "Submission"]
    data = api_post("/api/compare", {"pbi_csv": pbi, "sql_csv": sql, "composite_key": keys})
    if not data:
        return

    rate = data.get("match_rate", 0)
    color = "green" if rate >= 99 else "yellow" if rate >= 95 else "red"
    console.print(f"\n[{color}]⚖️  Match Rate: {rate}%[/{color}]")
    console.print(f"  PBI rows: {data['pbi_rows']} · SQL rows: {data['sql_rows']}")
    console.print(f"  Matched: {data['matched_rows']} · Mismatched: {data['mismatched_rows']}")
    console.print(f"  Extra in PBI: {data.get('extra_in_pbi', 0)} · Missing from PBI: {data.get('missing_from_pbi', 0)}")

    mismatches = data.get("mismatches", [])
    if mismatches:
        table = Table(title=f"Mismatches ({len(mismatches)})", show_lines=False, padding=(0, 1))
        table.add_column("Row Key", style="bold")
        table.add_column("Field")
        table.add_column("PBI", style="cyan")
        table.add_column("SQL", style="magenta")
        table.add_column("Diff", style="red")
        for m in mismatches[:20]:
            table.add_row(m["row_key"], m["field"], m["pbi_value"], m["sql_value"], m["diff"])
        console.print(table)
        if len(mismatches) > 20:
            console.print(f"[dim]  ... and {len(mismatches) - 20} more[/dim]")


def show_skills():
    data = api_get("/api/skills")
    if not data:
        return
    skills = data.get("skills", [])
    cats = {}
    for s in skills:
        cats.setdefault(s["cat"], []).append(s)

    for cat, items in cats.items():
        console.print(f"\n[bold cyan]{cat.upper()}[/bold cyan] ({len(items)})")
        for s in items:
            console.print(f"  [bold]{s['name']}[/bold] [dim]— {s['desc'][:80]}[/dim]")


def chat(message):
    data = api_post("/api/chat", {"message": message})
    if not data:
        return
    response = data.get("response", "")
    console.print()
    try:
        console.print(Markdown(response))
    except Exception:
        console.print(response)


def banner():
    health = api_get("/api/health")
    console.print()
    console.print("[bold blue]🔷 AI1X Auditor[/bold blue]")
    if health and health.get("status") == "ok":
        console.print(f"[dim]   Connected · {health.get('schema_tables', 0)} tables · {health.get('reports', 0)} reports · {health.get('hedis_measures', 0)} measures[/dim]")
    else:
        console.print("[yellow]   ⚠ Backend not reachable. Start: py -m uvicorn main:app --port 8000[/yellow]")
    console.print(f"[dim]   Type /help for commands or just chat.\n[/dim]")


def main():
    banner()

    while True:
        try:
            user_input = Prompt.ask("[bold blue]>[/bold blue]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Bye![/dim]")
            break

        if not user_input:
            continue

        if user_input in ("/quit", "/exit", "/q"):
            console.print("[dim]Bye![/dim]")
            break

        parts = user_input.split()
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == "/help":
            show_help()
        elif cmd == "/health":
            show_health()
        elif cmd == "/schema":
            show_schema(args)
        elif cmd == "/reports":
            show_reports(args)
        elif cmd == "/sql":
            generate_sql(args)
        elif cmd == "/compare":
            compare_csvs(args)
        elif cmd == "/skills":
            show_skills()
        elif cmd == "/clear":
            console.clear()
            banner()
        elif cmd.startswith("/"):
            console.print(f"[red]Unknown command: {cmd}. Type /help[/red]")
        else:
            chat(user_input)

        console.print()


if __name__ == "__main__":
    main()
