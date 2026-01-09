"""CLI entry point using Click."""

import os
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from icpc_audio.config import load_config
from icpc_audio.configure import run_configure
from icpc_audio.generator import generate_audio
from icpc_audio.models import AudioFormat, GenerationConfig, Mode
from icpc_audio.tts import TTSClient

console = Console()


@click.group()
@click.version_option()
def main() -> None:
    """ICPC Team Audio Generator - Generate audio files for team/organization names."""
    pass


@main.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--force", is_flag=True, help="Overwrite existing audio files")
@click.option("--dry-run", is_flag=True, help="Preview what would be generated")
def generate(
    folder: Path,
    force: bool,
    dry_run: bool,
) -> None:
    """Generate audio files for team or organization names.

    FOLDER is the path to the contest package folder containing icpc-audio.yaml
    config file, teams.json, and/or organizations.json.

    Run 'icpc-audio configure FOLDER' first to create the config file.
    """
    # Load config from the folder
    saved_config = load_config(folder)

    if not saved_config:
        console.print(f"[red]Error: No icpc-audio.yaml found in {folder}[/red]")
        console.print(f"Run [cyan]icpc-audio configure {folder}[/cyan] first")
        raise SystemExit(1)

    # Get credentials: config file > environment variable
    credentials_path: Optional[Path] = None
    if saved_config.credentials_path:
        credentials_path = Path(saved_config.credentials_path)
    elif os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        credentials_path = Path(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])

    if not credentials_path:
        console.print("[red]Error: No credentials configured[/red]")
        console.print("Set credentials_path in config or GOOGLE_APPLICATION_CREDENTIALS env var")
        raise SystemExit(1)

    if not credentials_path.exists():
        console.print(f"[red]Error: Credentials file not found: {credentials_path}[/red]")
        raise SystemExit(1)

    config = GenerationConfig(
        folder_path=folder,
        mode=Mode(saved_config.mode),
        audio_format=AudioFormat(saved_config.format),
        language=saved_config.language,
        voice=saved_config.voice,
        credentials_path=credentials_path,
        jobs=saved_config.jobs,
        force=force,
        dry_run=dry_run,
    )

    generate_audio(config)


@main.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False, path_type=Path))
def configure(folder: Path) -> None:
    """Run interactive configuration wizard.

    FOLDER is the path to the contest package folder where icpc-audio.yaml
    will be created.
    """
    try:
        run_configure(folder)
    except KeyboardInterrupt:
        console.print("\n[yellow]Configuration cancelled.[/yellow]")


@main.command()
@click.argument(
    "folder",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=False,
)
@click.option("-l", "--language", help="Filter by language code (e.g., en-US)")
@click.option(
    "-c",
    "--credentials",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to Google Cloud credentials JSON",
)
def voices(
    folder: Optional[Path],
    language: Optional[str],
    credentials: Optional[Path],
) -> None:
    """List available Google TTS voices.

    Optionally specify FOLDER to load credentials from icpc-audio.yaml.
    """
    # Try to get credentials from config if not provided
    if not credentials and folder:
        saved_config = load_config(folder)
        if saved_config and saved_config.credentials_path:
            credentials = Path(saved_config.credentials_path)

    try:
        client = TTSClient(credentials)
        voice_list = client.list_voices(language_code=language)
    except Exception as e:
        console.print(f"[red]Error connecting to Google TTS: {e}[/red]")
        raise SystemExit(1)

    table = Table(title="Available Google TTS Voices")
    table.add_column("Language", style="cyan")
    table.add_column("Voice Name", style="green")
    table.add_column("Gender")
    table.add_column("Type")

    for v in sorted(voice_list, key=lambda x: (x.language_codes[0], x.name)):
        lang = v.language_codes[0]
        gender = v.ssml_gender.name
        if "Neural2" in v.name or "Journey" in v.name:
            vtype = "Neural"
        elif "Wavenet" in v.name:
            vtype = "Wavenet"
        else:
            vtype = "Standard"
        table.add_row(lang, v.name, gender, vtype)

    console.print(table)
    console.print(f"\nTotal: {len(voice_list)} voices")


if __name__ == "__main__":
    main()
