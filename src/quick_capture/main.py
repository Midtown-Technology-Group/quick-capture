"""
Command interface for Quick Capture.

Provides commands for capturing tasks, ideas, notes, and logs to Logseq daily notes.
"""

import sys
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from . import __version__
from .config import load_config
from .writer import CaptureWriter

app = typer.Typer(
    name="qcapture",
    help="Fast, frictionless capture for Logseq daily notes",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        rprint(f"[bold blue]qcapture[/bold blue] version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None, "--version", "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
):
    """Quick Capture - Fast capture for Logseq daily notes."""
    pass


@app.command()
def capture(
    content: str = typer.Argument(..., help="Content to capture"),
    type: str = typer.Option(
        "note", "--type", "-t",
        help="Capture type: task, idea, note, log",
        show_default=True,
    ),
    section: Optional[str] = typer.Option(
        None, "--section", "-s",
        help="Target section (overrides type mapping)",
    ),
    date: Optional[str] = typer.Option(
        None, "--date", "-d",
        help="Target date (YYYY-MM-DD, default: today)",
    ),
):
    """Capture content to today's daily note.
    
    Examples:
        qc capture "Review Q2 proposal" --type task
        qc capture "New idea for Bifrost" --type idea
        qc capture "Learned about Kerberos" --type note
    """
    # Validate type
    valid_types = ["task", "idea", "note", "log"]
    if type not in valid_types:
        rprint(f"[red]Error:[/red] Invalid type '{type}'. Must be one of: {', '.join(valid_types)}")
        raise typer.Exit(1)
    
    # Load config and create writer
    config = load_config()
    writer = CaptureWriter(config)
    
    try:
        # Capture
        note_path, entry = writer.capture(
            content=content,
            capture_type=type,
            section=section,
            date_str=date,
        )
        
        # Output success
        target_section = section or config.qcapture.section_mappings.get(type, "Work Log")
        
        rprint(Panel(
            f"[bold green]✓[/bold green] Captured to [cyan]{note_path}[/cyan]\n"
            f"[dim]Section:[/dim] [yellow]{target_section}[/yellow]\n"
            f"[dim]Entry:[/dim] {entry}",
            title="Capture Success",
            border_style="green",
        ))
        
    except Exception as e:
        rprint(f"[red]Error:[/red] Failed to capture: {e}")
        raise typer.Exit(1)


@app.command(name="q")
def quick(
    content: str = typer.Argument(..., help="Quick capture content"),
    date: Optional[str] = typer.Option(
        None, "--date", "-d",
        help="Target date (YYYY-MM-DD, default: today)",
    ),
):
    """Quick capture (alias for 'capture --type note').
    
    Examples:
        qc q "Quick thought about project"
        qc q "Talked to Mike about migration"
    """
    capture.callback(content, type="note", section=None, date=date)


@app.command()
def task(
    content: str = typer.Argument(..., help="Task content"),
    date: Optional[str] = typer.Option(
        None, "--date", "-d",
        help="Target date (YYYY-MM-DD, default: today)",
    ),
):
    """Capture a task (alias for 'capture --type task').
    
    Examples:
        qc task "Fix server issue #urgent"
        qc task "Review proposal with @Sarah"
    """
    capture.callback(content, type="task", section=None, date=date)


@app.command()
def idea(
    content: str = typer.Argument(..., help="Idea content"),
    date: Optional[str] = typer.Option(
        None, "--date", "-d",
        help="Target date (YYYY-MM-DD, default: today)",
    ),
):
    """Capture an idea (alias for 'capture --type idea').
    
    Examples:
        qc idea "New feature for Bifrost"
        qc idea "Blog post about Direct Send"
    """
    capture.callback(content, type="idea", section=None, date=date)


@app.command()
def list(
    date: Optional[str] = typer.Option(
        None, "--date", "-d",
        help="Date to list (YYYY-MM-DD, default: today)",
    ),
):
    """List today's captures.
    
    Displays all captures from the daily note for the specified date.
    """
    config = load_config()
    note_path = config.get_today_note_path(date)
    
    if not note_path.exists():
        rprint(f"[yellow]No daily note found for {note_path.stem}[/yellow]")
        return
    
    content = note_path.read_text(encoding="utf-8")
    
    # Parse and display captures
    rprint(Panel(
        f"[cyan]{note_path}[/cyan]",
        title="Daily Note",
        border_style="blue",
    ))
    
    # Simple display for now - could be enhanced to show only captures
    rprint(content)


@app.command()
def config():
    """Show current configuration.
    
    Displays the effective configuration including vault path,
    timezone, and alias mappings.
    """
    cfg = load_config()
    
    rprint(Panel(
        f"[bold]Vault Path:[/bold] {cfg.vault_path}\n"
        f"[bold]Daily Notes:[/bold] {cfg.daily_notes_path}\n"
        f"[bold]Timezone:[/bold] {cfg.timezone}\n"
        f"[bold]Default Section:[/bold] {cfg.qcapture.default_section}\n"
        f"\n[bold]Aliases:[/bold]\n" +
        "\n".join(f"  {k} → {v}" for k, v in cfg.qcapture.aliases.items())
        if cfg.qcapture.aliases
        else "  (none configured)",
        title="Configuration",
        border_style="cyan",
    ))


def main():
    """Entry point for Quick Capture."""
    app()
