"""Interactive configuration wizard using questionary."""

import os
from pathlib import Path

import questionary
from rich.console import Console

from icpc_audio.config import load_config, save_config
from icpc_audio.models import AudioFormat, Config, Mode
from icpc_audio.tts import TTSClient

console = Console()


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

    # Determine actual credentials to use for API connection
    effective_credentials: Path | None = None
    if credentials_path:
        effective_credentials = Path(credentials_path)
    elif os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        effective_credentials = Path(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
        console.print(f"[dim]Using GOOGLE_APPLICATION_CREDENTIALS: {effective_credentials}[/dim]")

    if not effective_credentials:
        console.print("[red]Error: No credentials provided and GOOGLE_APPLICATION_CREDENTIALS not set[/red]")
        raise SystemExit(1)

    # Step 2: Connect and fetch voices
    console.print("\n[yellow]Connecting to Google TTS to fetch available voices...[/yellow]")
    try:
        tts_client = TTSClient(effective_credentials)
        languages = tts_client.list_languages()
    except Exception as e:
        console.print(f"[red]Error connecting to Google TTS: {e}[/red]")
        console.print("[yellow]Please check your credentials and try again.[/yellow]")
        raise SystemExit(1)

    console.print(f"[green]Connected! Found {len(languages)} languages.[/green]\n")

    # Step 3: Mode selection
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

    # Step 4: Language selection
    default_lang = existing.language if existing else "en-US"

    # If saved language is not English, show all languages
    show_all_default = not default_lang.startswith("en-")

    english_langs = [lang for lang in languages if lang.startswith("en-")]

    show_all = questionary.confirm(
        f"Show all {len(languages)} languages? (No = show English only)",
        default=show_all_default,
    ).ask()

    lang_choices = languages if show_all else english_langs

    # Make sure default is in choices
    if default_lang not in lang_choices:
        default_lang = lang_choices[0] if lang_choices else "en-US"

    language = questionary.select(
        "Select language:",
        choices=lang_choices,
        default=default_lang,
    ).ask()

    if language is None:
        raise KeyboardInterrupt()

    # Step 5: Voice selection
    voices = tts_client.list_voices(language_code=language)
    voice_choices = []
    default_voice = existing.voice if existing else None

    for v in sorted(voices, key=lambda x: x.name):
        gender = v.ssml_gender.name.lower()
        if "Neural2" in v.name or "Journey" in v.name:
            voice_type = "neural"
        elif "Wavenet" in v.name:
            voice_type = "wavenet"
        else:
            voice_type = "standard"
        label = f"{v.name} ({gender}, {voice_type})"
        voice_choices.append(questionary.Choice(label, v.name))

    # Find default voice in choices, or use first
    voice_values = [c.value for c in voice_choices]
    if default_voice not in voice_values:
        default_voice = voice_values[0] if voice_values else None

    voice = questionary.select(
        "Select voice:",
        choices=voice_choices,
        default=default_voice,
    ).ask()

    if voice is None:
        raise KeyboardInterrupt()

    # Step 6: Audio format
    format_choices = [
        questionary.Choice("MP3 - Compressed, widely compatible", AudioFormat.MP3.value),
        questionary.Choice("M4A - Good quality, Apple compatible", AudioFormat.M4A.value),
        questionary.Choice("WAV - Uncompressed, large files", AudioFormat.WAV.value),
        questionary.Choice("OGG - Opus codec, good quality/size ratio", AudioFormat.OGG.value),
    ]

    default_format = existing.format if existing else AudioFormat.MP3.value

    audio_format = questionary.select(
        "Select audio format:",
        choices=format_choices,
        default=default_format,
    ).ask()

    if audio_format is None:
        raise KeyboardInterrupt()

    # Step 7: Parallelism
    default_jobs = str(existing.jobs) if existing else "4"

    jobs = questionary.text(
        "Number of parallel jobs (1-16):",
        default=default_jobs,
        validate=lambda x: x.isdigit() and 1 <= int(x) <= 16 or "Enter a number between 1 and 16",
    ).ask()

    if jobs is None:
        raise KeyboardInterrupt()

    # Save configuration
    config = Config(
        credentials_path=credentials_path if credentials_path else None,
        language=language,
        voice=voice,
        format=audio_format,
        mode=mode,
        jobs=int(jobs),
    )

    config_path = save_config(config, folder)
    console.print(f"\n[green]Configuration saved to {config_path}[/green]")
    console.print("\nYou can now run:")
    console.print(f"  [cyan]icpc-audio generate {folder}[/cyan]")
