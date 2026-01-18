"""Interactive configuration wizard using questionary."""

import os
from pathlib import Path

import questionary
from rich.console import Console

from icpc_audio.config import load_config, save_config
from icpc_audio.models import AudioFormat, Config, Mode, DEFAULT_PROMPT

console = Console()

# Common languages for ICPC
LANGUAGES = [
    "en-US",
    "de-DE",
    "fr-FR",
    "es-ES",
    "pt-BR",
    "ru-RU",
    "cmn-CN",
    "ja-JP",
    "ko-KR",
    "ar-XA",
]


def run_configure(folder: Path) -> None:
    """Run the interactive configuration wizard."""
    console.print("\n[bold]ICPC Audio Generator - Configuration Wizard[/bold]\n")
    console.print(f"Configuring for: [cyan]{folder}[/cyan]\n")

    # Load existing config for defaults
    existing = load_config(folder)
    if existing:
        console.print("[dim]Found existing config, using as defaults[/dim]\n")

    # Step 1: Google credentials (optional - can use GOOGLE_APPLICATION_CREDENTIALS env var)
    credentials_path = questionary.text(
        "Path to Google Cloud credentials JSON (leave empty to use GOOGLE_APPLICATION_CREDENTIALS env var):",
        default=existing.credentials_path if existing and existing.credentials_path else "",
        validate=lambda p: p == "" or Path(p).exists() or "File does not exist",
    ).ask()

    if credentials_path is None:
        raise KeyboardInterrupt()

    # Step 2: Mode selection
    mode_choices = [
        questionary.Choice("Teams - Use team display names from teams.json", Mode.TEAMS.value),
        questionary.Choice("Organizations - Use formal names from organizations.json", Mode.ORGANIZATIONS.value),
    ]

    default_mode = existing.mode if existing else Mode.TEAMS.value

    mode = questionary.select(
        "What do you want to generate audio for?",
        choices=mode_choices,
        default=default_mode,
    ).ask()

    if mode is None:
        raise KeyboardInterrupt()

    # Step 3: Language selection
    default_lang = existing.language if existing else "en-US"

    language = questionary.select(
        "Select default language:",
        choices=LANGUAGES,
        default=default_lang if default_lang in LANGUAGES else "en-US",
    ).ask()

    if language is None:
        raise KeyboardInterrupt()

    # Step 4: Audio format
    format_choices = [
        questionary.Choice("WAV - Uncompressed, best quality", AudioFormat.WAV.value),
        questionary.Choice("MP3 - Compressed, widely compatible", AudioFormat.MP3.value),
        questionary.Choice("M4A - Good quality, Apple compatible", AudioFormat.M4A.value),
        questionary.Choice("OGG - Opus codec, good quality/size ratio", AudioFormat.OGG.value),
    ]

    default_format = existing.format if existing else AudioFormat.WAV.value

    audio_format = questionary.select(
        "Select audio format:",
        choices=format_choices,
        default=default_format,
    ).ask()

    if audio_format is None:
        raise KeyboardInterrupt()

    # Step 5: Parallelism
    default_jobs = str(existing.jobs) if existing else "4"

    jobs = questionary.text(
        "Number of parallel jobs (1-16):",
        default=default_jobs,
        validate=lambda x: x.isdigit() and 1 <= int(x) <= 16 or "Enter a number between 1 and 16",
    ).ask()

    if jobs is None:
        raise KeyboardInterrupt()

    # Step 6: Prompt
    default_prompt = existing.prompt if existing else DEFAULT_PROMPT

    console.print("\n[dim]The prompt guides how the TTS announces names.[/dim]")
    use_default_prompt = questionary.confirm(
        "Use default ICPC announcer prompt?",
        default=default_prompt == DEFAULT_PROMPT,
    ).ask()

    if use_default_prompt:
        prompt = DEFAULT_PROMPT
    else:
        prompt = questionary.text(
            "Enter custom prompt:",
            default=default_prompt,
        ).ask()

    if prompt is None:
        raise KeyboardInterrupt()

    # Save configuration
    config = Config(
        credentials_path=credentials_path if credentials_path else None,
        language=language,
        format=audio_format,
        mode=mode,
        jobs=int(jobs),
        prompt=prompt,
        overrides=existing.overrides if existing else {},
    )

    config_path = save_config(config, folder)
    console.print(f"\n[green]Configuration saved to {config_path}[/green]")
    console.print("\n[dim]Note: Audio will be generated with both male and female voices.[/dim]")
    console.print("[dim]Edit icpc-audio.yaml to add per-team/org overrides if needed.[/dim]")
    console.print("\nYou can now run:")
    console.print(f"  [cyan]icpc-audio generate {folder}[/cyan]")
