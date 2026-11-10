from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .client import StaleCheck, StaleCheckError

app = typer.Typer(
    add_completion=False,
    help="StaleCheck CLI: catch stale, time-sensitive claims in AI answers.",
)
console = Console()

_STYLES = {"fresh": "green", "stale": "bold red", "unverifiable": "yellow"}
_TEXT_SUFFIXES = {".md", ".mdx", ".txt", ".rst", ".json"}


def _client(url: str | None, api_key: str | None) -> StaleCheck:
    return StaleCheck(base_url=url, api_key=api_key)


def _render(result, show_evidence: bool = True) -> None:
    color = _STYLES.get(result.verdict, "white")
    console.print(
        f"\n[{color}]{result.verdict.upper()}[/{color}]"
        f"  score={result.staleness_score:.2f}"
        f"  action={result.action}"
        f"  provider={result.provider}"
        f"  {result.latency_ms}ms" + ("  [dim](cached)[/dim]" if result.cached else "")
    )
    table = Table(show_header=True, header_style="bold")
    table.add_column("Claim")
    table.add_column("Vol.", justify="center")
    table.add_column("Verdict", justify="center")
    table.add_column("Why", overflow="fold")
    for claim in result.claims:
        vstyle = _STYLES.get(claim.verdict, "white")
        table.add_row(
            claim.text,
            claim.volatility,
            f"[{vstyle}]{claim.verdict}[/{vstyle}]",
            claim.reason,
        )
    console.print(table)
    if show_evidence:
        for claim in result.claims:
            for ev in claim.evidence:
                console.print(f"  [dim]-[/dim] {ev.title}: [link={ev.url}]{ev.url}[/link]")
    fixes = [c for c in result.claims if c.verdict == "stale" and c.suggested_fix]
    for claim in fixes:
        console.print(f"  [bold]fix:[/bold] {claim.suggested_fix}")


@app.command()
def check(
    text: str | None = typer.Argument(None, help="Text to check. Reads stdin if omitted."),
    url: str | None = typer.Option(None, "--url", envvar="STALECHECK_URL", help="API base URL."),
    api_key: str | None = typer.Option(None, "--api-key", envvar="STALECHECK_API_KEY"),
    mode: str = typer.Option("annotate", "--mode", help="annotate | auto_refresh | block"),
    no_web: bool = typer.Option(False, "--no-web", help="Skip live Tavily verification."),
    as_json: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
    fail_on_stale: bool = typer.Option(True, "--fail-on-stale/--no-fail-on-stale"),
) -> None:
    """Check a single answer for stale claims."""
    if text is None:
        text = sys.stdin.read()
    if not text or not text.strip():
        console.print("[red]No input text provided.[/red]")
        raise typer.Exit(2)

    try:
        result = _client(url, api_key).check(text, mode=mode, use_web=not no_web)
    except StaleCheckError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc

    if as_json:
        typer.echo(json.dumps(result.to_dict(), indent=2))
    else:
        _render(result)
    if fail_on_stale and result.verdict == "stale":
        raise typer.Exit(1)


@app.command()
def scan(
    path: Path = typer.Argument(Path("."), exists=True, help="File or directory to scan."),
    url: str | None = typer.Option(None, "--url", envvar="STALECHECK_URL"),
    api_key: str | None = typer.Option(None, "--api-key", envvar="STALECHECK_API_KEY"),
    mode: str = typer.Option("annotate", "--mode"),
    no_web: bool = typer.Option(False, "--no-web"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Scan docs or text files and fail if any stale claims are found (CI-friendly)."""
    files = (
        [path]
        if path.is_file()
        else sorted(p for p in path.rglob("*") if p.suffix.lower() in _TEXT_SUFFIXES)
    )
    if not files:
        console.print("[yellow]No files to scan.[/yellow]")
        return

    client = _client(url, api_key)
    rows = []
    stale_files = 0
    for file in files:
        try:
            content = file.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            console.print(f"[red]Cannot read {file}: {exc}[/red]")
            continue
        if not content.strip():
            continue
        try:
            result = client.check(content, mode=mode, use_web=not no_web)
        except StaleCheckError as exc:
            console.print(f"[red]{file}: {exc}[/red]")
            raise typer.Exit(2) from exc
        if result.verdict == "stale":
            stale_files += 1
        rows.append(
            {
                "file": str(file),
                "verdict": result.verdict,
                "score": result.staleness_score,
                "stale": len(result.stale_claims),
                "claims": len(result.claims),
                "result": result.to_dict(),
            }
        )

    if as_json:
        typer.echo(json.dumps(rows, indent=2))
    else:
        table = Table(show_header=True, header_style="bold")
        table.add_column("File")
        table.add_column("Verdict")
        table.add_column("Stale", justify="right")
        table.add_column("Claims", justify="right")
        for row in rows:
            style = _STYLES.get(row["verdict"], "white")
            table.add_row(
                row["file"],
                f"[{style}]{row['verdict']}[/{style}]",
                str(row["stale"]),
                str(row["claims"]),
            )
        console.print(table)
        console.print(f"\nScanned {len(rows)} files, {stale_files} with stale claims.")

    if stale_files:
        raise typer.Exit(1)


@app.command()
def stats(
    url: str | None = typer.Option(None, "--url", envvar="STALECHECK_URL"),
    api_key: str | None = typer.Option(None, "--api-key", envvar="STALECHECK_API_KEY"),
) -> None:
    """Show aggregate stats from the API."""
    try:
        data = _client(url, api_key).stats()
    except StaleCheckError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc
    typer.echo(json.dumps(data, indent=2))


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host"),
    port: int = typer.Option(8000, "--port"),
    reload: bool = typer.Option(False, "--reload"),
) -> None:
    """Run the StaleCheck API locally (requires stalecheck-api installed)."""
    try:
        import uvicorn
    except ImportError as exc:
        console.print("[red]uvicorn is not installed. Install the API package.[/red]")
        raise typer.Exit(2) from exc
    try:
        uvicorn.run("stalecheck_api.main:app", host=host, port=port, reload=reload)
    except ImportError as exc:
        console.print(
            "[red]stalecheck_api is not installed. Run from the monorepo with `uv sync`.[/red]"
        )
        raise typer.Exit(2) from exc


@app.command()
def version() -> None:
    """Print the CLI version."""
    from . import __version__

    typer.echo(f"stalecheck {__version__}")
