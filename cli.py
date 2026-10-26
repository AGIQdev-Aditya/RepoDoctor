#!/usr/bin/env python3
"""
RepoDoctor — Autonomous Codebase Health, Security Auditing & PR CLI
Studio-grade Terminal Console with Rich Status Spinners, ASCII Tables & Gemma 4 Streaming.

Usage:
    python cli.py                       # Audit current repository
    python cli.py /path/to/project      # Audit specific codebase
    python cli.py --chat "query"        # Ask Gemma Copilot via 3-Gate Supervisor
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

import hardened
from engine import RepoDoctorEngine

# Initialize security supervisor
hardened.install()
console = Console()
engine = RepoDoctorEngine()


def print_banner(target_path: Path):
    banner_text = Text()
    banner_text.append("🩺 REPO-DOCTOR ", style="bold white on #6366f1")
    banner_text.append(" Autonomous Codebase Health & DevSecOps Engine\n", style="bold cyan")
    banner_text.append("Powered by Google Gemma 4 • 100% Offline Air-Gapped • 3-Gate Verification Architecture", style="dim")
    
    panel = Panel(
        banner_text,
        box=box.ROUNDED,
        border_style="#6366f1",
        subtitle=f"[dim]Inspecting: [bold #22d3ee]{target_path.resolve()}[/bold #22d3ee][/dim]"
    )
    console.print(panel)


def run_cli_audit(target_dir: str, generate_pr: bool = False):
    path = Path(target_dir).resolve()
    if not path.is_dir():
        console.print(f"[bold red]✕ Error:[/bold red] Target path is not a directory: {path}")
        sys.exit(1)

    print_banner(path)

    # Step 1: Execute Full Diagnostic with Live Spinner
    with console.status("[bold #6366f1]🩺 [1/3] Running AST analysis, secret scanner & Tarjan SCC cycle detection...", spinner="dots"):
        t0 = time.time()
        diag = engine.get_full_diagnosis(str(path))
        elapsed = round(time.time() - t0, 2)

    overview = diag.get("overview", {})
    security = diag.get("security", {})
    arch = diag.get("architecture", {})

    score = security.get("security_score", 0)
    grade = security.get("grade", "N/A")
    score_color = "bold green" if score >= 80 else "bold yellow" if score >= 60 else "bold red"

    # Score Panel
    score_panel = Panel(
        Text.assemble(
            ("SECURITY HEALTH SCORE: ", "dim"),
            (f"{score}/100 ", score_color),
            (f"• GRADE {grade} ", score_color),
            (f"({security.get('risk_level', 'UNKNOWN')})\n", "bold"),
            (f"Diagnostic completed in {elapsed}s across {overview.get('total_files', 0)} files ({overview.get('total_lines_of_code', 0)} LOC)", "dim")
        ),
        box=box.ROUNDED,
        border_style="green" if score >= 80 else "yellow" if score >= 60 else "red",
        title="[bold]Diagnostic Summary[/bold]"
    )
    console.print(score_panel)

    # Table 1: Codebase Vital Metrics
    t1 = Table(title="📊 Codebase Vital Signs", box=box.SIMPLE_HEAVY, border_style="#6366f1")
    t1.add_column("Metric", style="bold cyan")
    t1.add_column("Value", style="bold white")
    t1.add_column("Details", style="dim")

    t1.add_row("Total Files", str(overview.get("total_files", 0)), "Python & configuration sources")
    t1.add_row("Lines of Code (LOC)", f"{overview.get('total_lines_of_code', 0):,}", "Excluding virtual environments")
    t1.add_row("Comment Density", f"{overview.get('comment_density_pct', 0)}%", "Calculated from AST comments")
    t1.add_row("Python Modules", str(arch.get("total_python_modules", 0)), "Analyzed via AST import graph")
    t1.add_row("Dependency Edges", str(arch.get("total_dependency_edges", 0)), "Inter-module dependency couplings")

    cycles_count = arch.get("circular_dependencies_detected", 0)
    cycle_style = "bold red" if cycles_count > 0 else "bold green"
    t1.add_row("Circular Cycles", f"[{cycle_style}]{cycles_count} cycle(s)[/{cycle_style}]", "Detected via Tarjan SCC O(V+E)")
    console.print(t1)

    # Table 2: Security & Secret Findings
    secrets = security.get("secrets", [])
    vulns = security.get("vulnerabilities", [])

    if secrets or vulns:
        t2 = Table(title=f"🚨 Detected Vulnerabilities & Secrets ({len(secrets) + len(vulns)} Total)", box=box.SIMPLE_HEAVY, border_style="red")
        t2.add_column("Severity", style="bold")
        t2.add_column("Type / Rule", style="bold white")
        t2.add_column("Location", style="cyan")
        t2.add_column("Snippet / Evidence", style="dim")

        for s in secrets:
            t2.add_row("[bold red]CRITICAL[/bold red]", s.get("type", "Secret"), f"{s.get('file')}:{s.get('line')}", s.get("snippet", "")[:70])

        for v in vulns:
            sev = v.get("severity", "Medium")
            sev_style = "bold red" if sev in ("Critical", "High") else "bold yellow"
            t2.add_row(f"[{sev_style}]{sev.upper()}[/{sev_style}]", v.get("vulnerability", "Vuln"), f"{v.get('file')}:{v.get('line')}", v.get("snippet", "")[:70])

        console.print(t2)
    else:
        console.print(Panel("[bold green]✓ Zero high-entropy secrets or execution vulnerabilities detected![/bold green]", border_style="green"))

    # Table 3: Circular Dependency Cycles (if any)
    if arch.get("cycles"):
        t3 = Table(title="⚠️ Circular Dependency Details", box=box.SIMPLE_HEAVY, border_style="yellow")
        t3.add_column("Cycle Group", style="bold red")
        t3.add_column("Coupled Modules", style="white")
        for idx, cycle in enumerate(arch["cycles"], 1):
            t3.add_row(f"Cycle #{idx}", " ➔ ".join(cycle))
        console.print(t3)

    # Optional Step 2: Synthesize PR Review with Gemma 4 if requested
    if generate_pr:
        console.print("\n[bold #6366f1]✦ Generating Autonomous Pull Request Review with Gemma 4...[/bold #6366f1]")
        with console.status("[bold cyan]Gemma 4 synthesizing comprehensive code review comments...", spinner="dots"):
            pr_res = engine.synthesize_pr_review(str(path))

        pr_text = pr_res.get("pr_comment", "No comments generated.")
        pr_panel = Panel(
            Markdown(pr_text),
            title=f"[bold #22d3ee]🤖 Gemma 4 Autonomous PR Review ({pr_res.get('duration_sec', 0)}s)[/bold #22d3ee]",
            box=box.ROUNDED,
            border_style="#22d3ee"
        )
        console.print(pr_panel)
    else:
        console.print("\n[dim]💡 Tip: Run [bold white]python cli.py --pr[/bold white] to generate an autonomous Gemma 4 PR Review.[/dim]")

    console.print("\n[bold green]✓ RepoDoctor CLI run complete![/bold green] Web UI available at: [bold cyan]http://127.0.0.1:8502[/bold cyan]\n")


def run_cli_chat(prompt: str, target_dir: str):
    path = Path(target_dir).resolve()
    print_banner(path)
    console.print(f"[bold cyan]User Prompt:[/bold cyan] {prompt}\n")

    with console.status("[bold #6366f1]Gemma 4 running 3-Gate Security Supervisor...", spinner="dots"):
        chat_res = engine.chat_with_agent(prompt, str(path))

    console.print(Panel(Markdown(chat_res.get("final_response", "")), title="[bold #22d3ee]Gemma 4 Copilot Response[/bold #22d3ee]", border_style="#22d3ee"))
    
    if chat_res.get("tool_ledger"):
        t = Table(title="🔧 3-Gate Tool Execution Ledger", box=box.SIMPLE)
        t.add_column("Step", style="dim")
        t.add_column("Tool Executed", style="bold cyan")
        t.add_column("Arguments", style="dim")
        t.add_column("Gate Status", style="green")
        for entry in chat_res["tool_ledger"]:
            t.add_row(
                str(entry.get("step")),
                entry.get("tool_name", ""),
                str(entry.get("arguments", {})),
                entry.get("dispatch_report", {}).get("status", "ok")
            )
        console.print(t)


if __name__ == "__main__":
    args = sys.argv[1:]
    target = str(Path(__file__).parent)

    if "--chat" in args:
        idx = args.index("--chat")
        user_prompt = args[idx + 1] if idx + 1 < len(args) else "Summarize the repository health and security findings."
        run_cli_chat(user_prompt, target)
    else:
        generate_pr = "--pr" in args or "--all" in args
        non_flag_args = [a for a in args if not a.startswith("-")]
        if non_flag_args:
            target = non_flag_args[0]
        run_cli_audit(target, generate_pr=generate_pr)
