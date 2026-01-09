# ICPC Team Audio Generator

Generate audio files for ICPC team and organization names using Google Text-to-Speech API.

## Installation

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/nickygerritsen/icpc-team-audio-generator.git
cd icpc-team-audio-generator
uv sync
```

## Google Cloud Setup

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the [Cloud Text-to-Speech API](https://console.cloud.google.com/apis/library/texttospeech.googleapis.com)
3. Create a service account and download the JSON key file
4. Either:
   - Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to the path of the key file
   - Or provide the path during configuration

## Usage

### 1. Configure

Run the interactive configuration wizard for your contest folder:

```bash
uv run icpc-audio configure /path/to/contest
```

This will prompt for:
- Google Cloud credentials path (optional if `GOOGLE_APPLICATION_CREDENTIALS` is set)
- Mode: teams or organizations
- Language (e.g., en-US)
- Voice (e.g., en-US-Wavenet-D)
- Audio format (mp3, m4a, wav, ogg)
- Number of parallel jobs

Configuration is saved to `icpc-audio.yaml` in the contest folder.

### 2. Generate

Generate audio files:

```bash
uv run icpc-audio generate /path/to/contest
```

Options:
- `--dry-run` - Preview what would be generated without creating files
- `--force` - Overwrite existing audio files

Audio files are saved to:
- Teams: `teams/{id}/audio.{format}`
- Organizations: `organizations/{id}/audio.{format}`

### 3. List voices

List available Google TTS voices:

```bash
uv run icpc-audio voices /path/to/contest
uv run icpc-audio voices -c /path/to/credentials.json -l en-US
```

## Contest Package Structure

The tool expects a contest package folder with:
- `teams.json` - Team data with `id`, `name`, and `display_name` fields
- `organizations.json` - Organization data with `id`, `name`, and `formal_name` fields
- `teams/` - Directory for team files (audio will be saved here)
- `organizations/` - Directory for organization files (audio will be saved here)

## License

MIT
