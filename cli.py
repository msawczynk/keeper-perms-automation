#!/usr/bin/env python3
"""
Keeper Permissions Automation – Refactored CLI
=============================================
Implements Phase-1 commands using the new atomic service layer.
Commands:
  • configure – view (or scaffold) the Perms-Config record
  • template   – generate a CSV template
  • validate   – lint a CSV file
  • dry-run    – list the operations that would be executed
  • apply      – execute the provisioning job (checkpoint + logging)
"""

import json
import uuid
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.table import Table

from keeper_auto.services import (
    ConfigService,
    VaultService,
    TemplateService,
    ValidationService,
    ProvisioningService,
)
from keeper_auto.logger import init_logger
from keeper_auto.checkpoint import create_checkpoint_manager
from keeper_auto.models import ConfigRecord, VaultData

app = typer.Typer(name="keeper-perms", help="Automate Keeper permissions provisioning.")
console = Console()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_config_or_exit(record_uid: Optional[str]) -> ConfigRecord:
    cfg = ConfigService().load_config(record_uid)
    if cfg is None:
        console.print("❌ Configuration record not found.", style="bold red")
        raise typer.Exit(code=1)
    return cfg

# ---------------------------------------------------------------------------
# configure
# ---------------------------------------------------------------------------

@app.command()
def configure(
    record_uid: str = typer.Option(None, "--record", "-r", help="UID of the configuration record to load."),
    create: bool = typer.Option(False, "--create", help="Create a new configuration template on stdout."),
    root_folder: str = typer.Option("[Perms]", "--root-folder", help="Root folder name for permissions."),
):
    """Display or scaffold the Perms-Config record."""
    if create:
        cfg = {
            "root_folder_name": root_folder,
            "included_teams": None,
            "included_folders": None,
            "excluded_folders": [],
        }
        console.print("--- 📝 Configuration JSON template ---", style="cyan")
        console.print(json.dumps(cfg, indent=2))
        console.print("Save this JSON in a Keeper record titled 'Perms-Config' and rerun commands.", style="yellow")
        raise typer.Exit()

    cfg = _load_config_or_exit(record_uid)

    console.print("--- ⚙️  Current Configuration ---", style="bold blue")
    console.print(f"Root folder       : [cyan]{cfg.root_folder_name}[/cyan]")
    console.print(f"Included teams    : [cyan]{cfg.included_teams or 'ALL'}[/cyan]")
    console.print(f"Included folders  : [cyan]{cfg.included_folders or 'ALL'}[/cyan]")
    console.print(f"Excluded folders  : [cyan]{len(cfg.excluded_folders)} UID(s) excluded[/cyan]")

# ---------------------------------------------------------------------------
# template
# ---------------------------------------------------------------------------

@app.command()
def template(
    output_file: Path = typer.Option("template.csv", "--out", "-o", help="Output CSV path"),
    config_uid: str = typer.Option(None, "--config", "-c", help="UID of the configuration record"),
):
    """Generate a CSV template for the current vault snapshot."""
    cfg = _load_config_or_exit(config_uid)

    vault_service = VaultService(cfg)
    vault_data: VaultData = vault_service.load_vault_data()  # type: ignore

    TemplateService(vault_data, cfg).generate_template(output_file)
    console.print(f"✅ Template written to [cyan]{output_file.resolve()}[/cyan]", style="bold green")

# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

@app.command()
def validate(
    file: Path = typer.Argument(..., help="CSV file to validate"),
    max_records: int = typer.Option(5000, "--max-records", help="Safety row limit"),
):
    """Lint a CSV file for structural & semantic errors."""
    vs = ValidationService()
    result = vs.validate_csv(file, max_records)

    if result.is_valid:
        console.print("✅ CSV is valid", style="bold green")
    else:
        console.print("❌ Validation errors:", style="bold red")
        for err in result.errors:
            console.print(f"  • {err}", style="red")
        raise typer.Exit(code=1)

    if result.warnings:
        console.print("⚠️  Warnings:", style="yellow")
        for w in result.warnings:
            console.print(f"  • {w}", style="yellow")

# ---------------------------------------------------------------------------
# dry-run
# ---------------------------------------------------------------------------

@app.command(name="dry-run")
def dry_run(
    file: Path = typer.Argument(..., help="CSV file to process"),
    config_uid: str = typer.Option(None, "--config", "-c", help="UID of the configuration record"),
    max_records: int = typer.Option(5000, "--max-records", help="Safety row limit"),
):
    """Show the operations that would be performed without mutating the vault."""
    cfg = _load_config_or_exit(config_uid)

    # Validate first
    val = ValidationService().validate_csv(file, max_records)
    if not val.is_valid:
        console.print("❌ CSV failed validation – aborting dry-run", style="bold red")
        raise typer.Exit(code=1)

    logger = init_logger()
    vault_data = VaultService(cfg).load_vault_data()
    ops: List[str] = ProvisioningService(vault_data, cfg, logger).dry_run(file)

    console.print(f"--- Proposed operations ({len(ops)}) ---", style="bold blue")
    for op in ops:
        console.print(f"  • {op}")

# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------

@app.command()
def apply(
    file: Path = typer.Argument(..., help="CSV file to apply."),
    config_uid: str = typer.Option(None, "--config", "-c", help="UID of the configuration record"),
    max_records: int = typer.Option(5000, "--max-records", help="Safety row limit"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
):
    """Execute provisioning – creates folders, links records, sets team permissions."""
    cfg = _load_config_or_exit(config_uid)

    # Validate first
    val = ValidationService().validate_csv(file, max_records)
    if not val.is_valid:
        console.print("❌ CSV failed validation – aborting", style="bold red")
        for err in val.errors:
            console.print(f"  • {err}", style="red")
        raise typer.Exit(code=1)

    row_count = val.metadata.get("row_count", 0)
    if row_count > max_records and not force:
        console.print(f"❌ {row_count} rows exceed max-records {max_records}. Use --force to override.", style="bold red")
        raise typer.Exit(code=1)

    # Confirmation
    if not force:
        if not typer.confirm(f"Apply {row_count} rows to the vault? This is irreversible."):
            console.print("🛑 Operation cancelled.", style="yellow")
            raise typer.Abort()

    run_id = str(uuid.uuid4())[:8]
    logger = init_logger(run_id=run_id)
    checkpoint = create_checkpoint_manager(run_id=run_id)
    checkpoint.start_checkpoint(str(file), total_operations=row_count)

    vault_data = VaultService(cfg).load_vault_data()
    prov = ProvisioningService(vault_data, cfg, logger)

    console.print("🚀 Applying changes…", style="cyan")
    success = prov.apply_changes(file, max_records, force)
    checkpoint.finalize_checkpoint()

    if success:
        console.print("✅ Apply completed successfully!", style="bold green")
    else:
        console.print("❌ Apply finished with errors – check logs.", style="bold red")
        raise typer.Exit(code=1)

# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
