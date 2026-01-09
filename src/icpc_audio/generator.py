"""Main audio generation logic."""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Union

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table

from icpc_audio.models import GenerationConfig, Mode, Organization, Team
from icpc_audio.tts import TTSClient

console = Console()


def load_organizations(json_path: Path) -> list[Organization]:
    """Load organizations from JSON file."""
    with open(json_path) as f:
        data = json.load(f)
    return [
        Organization(
            id=item["id"],
            name=item["name"],
            formal_name=item.get("formal_name", item["name"]),
            country=item.get("country"),
        )
        for item in data
    ]


def load_teams(json_path: Path) -> list[Team]:
    """Load teams from JSON file."""
    with open(json_path) as f:
        data = json.load(f)
    return [
        Team(
            id=item["id"],
            name=item["name"],
            display_name=item.get("display_name"),
            organization_id=item.get("organization_id"),
        )
        for item in data
    ]


def get_output_path(config: GenerationConfig, item_id: str) -> Path:
    """Get output path for audio file."""
    subdir = config.mode.value  # "organizations" or "teams"
    return config.folder_path / subdir / item_id / f"audio.{config.audio_format.value}"


@dataclass
class GenerationTask:
    """A single audio generation task."""

    item: Union[Organization, Team]
    output_path: Path


@dataclass
class GenerationResult:
    """Result of a generation task."""

    task: GenerationTask
    success: bool
    error: str | None = None


def generate_single(
    task: GenerationTask,
    tts_client: TTSClient,
    config: GenerationConfig,
) -> GenerationResult:
    """Generate audio for a single item."""
    try:
        # Ensure parent directory exists
        task.output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate audio
        audio_bytes = tts_client.synthesize(
            text=task.item.display_text,
            language_code=config.language,
            voice_name=config.voice,
            audio_format=config.audio_format.value,
        )

        # Write to file
        with open(task.output_path, "wb") as f:
            f.write(audio_bytes)

        return GenerationResult(task=task, success=True)
    except Exception as e:
        return GenerationResult(task=task, success=False, error=str(e))


def generate_audio(config: GenerationConfig) -> None:
    """Main audio generation function."""
    # Load data
    json_file = config.folder_path / f"{config.mode.value}.json"

    if not json_file.exists():
        console.print(f"[red]Error: {json_file} not found![/red]")
        raise SystemExit(1)

    if config.mode == Mode.ORGANIZATIONS:
        items: list[Union[Organization, Team]] = load_organizations(json_file)
    else:
        items = load_teams(json_file)

    console.print(f"\n[bold]Loaded {len(items)} {config.mode.value}[/bold]")
    console.print(f"  Voice: [cyan]{config.voice}[/cyan]")
    console.print(f"  Format: [cyan]{config.audio_format.value}[/cyan]")
    console.print(f"  Parallel jobs: [cyan]{config.jobs}[/cyan]")

    # Determine what needs to be generated
    to_generate: list[GenerationTask] = []
    skipped: list[tuple[Union[Organization, Team], Path, str]] = []

    for item in items:
        output_path = get_output_path(config, item.id)

        if not config.force and output_path.exists():
            skipped.append((item, output_path, "exists"))
        else:
            to_generate.append(GenerationTask(item=item, output_path=output_path))

    # Show summary
    console.print(f"\n  To generate: [green]{len(to_generate)}[/green]")
    console.print(f"  Skipped (existing): [yellow]{len(skipped)}[/yellow]")

    if config.dry_run:
        show_dry_run_preview(to_generate, skipped, config)
        return

    if not to_generate:
        console.print("\n[green]Nothing to generate![/green]")
        return

    # Initialize TTS client
    tts_client = TTSClient(config.credentials_path)

    # Generate with progress bar and parallel execution
    errors: list[GenerationResult] = []
    successful = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task("Generating audio...", total=len(to_generate))

        with ThreadPoolExecutor(max_workers=config.jobs) as executor:
            futures = {
                executor.submit(generate_single, task, tts_client, config): task
                for task in to_generate
            }

            for future in as_completed(futures):
                result = future.result()
                if result.success:
                    successful += 1
                else:
                    errors.append(result)

                progress.update(
                    task_id,
                    description=f"Generated: {result.task.item.display_text[:40]}...",
                    advance=1,
                )

    # Summary
    console.print(f"\n[bold]Generation complete![/bold]")
    console.print(f"  Generated: [green]{successful}[/green]")
    if errors:
        console.print(f"  Errors: [red]{len(errors)}[/red]")
        for result in errors:
            console.print(
                f"    - {result.task.item.id} ({result.task.item.display_text}): {result.error}"
            )


def show_dry_run_preview(
    to_generate: list[GenerationTask],
    skipped: list[tuple[Union[Organization, Team], Path, str]],
    config: GenerationConfig,
) -> None:
    """Show preview of what would be generated."""
    console.print("\n[bold yellow]DRY RUN - No files will be created[/bold yellow]\n")

    if to_generate:
        table = Table(title="Files to Generate")
        table.add_column("ID", style="cyan")
        table.add_column("Text to Speak", style="green")
        table.add_column("Output Path", style="dim")

        for task in to_generate[:20]:  # Limit preview
            rel_path = task.output_path.relative_to(config.folder_path)
            table.add_row(
                task.item.id,
                task.item.display_text[:50],
                str(rel_path),
            )

        if len(to_generate) > 20:
            table.add_row("...", f"({len(to_generate) - 20} more)", "...")

        console.print(table)

    if skipped:
        console.print(f"\n[yellow]Would skip {len(skipped)} existing files[/yellow]")
