"""Data models for ICPC Audio Generator."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class Mode(str, Enum):
    """Generation mode."""

    ORGANIZATIONS = "organizations"
    TEAMS = "teams"


class AudioFormat(str, Enum):
    """Supported audio output formats."""

    MP3 = "mp3"
    WAV = "wav"
    M4A = "m4a"
    OGG = "ogg"


@dataclass
class Organization:
    """Organization data from organizations.json."""

    id: str
    name: str
    formal_name: str
    country: Optional[str] = None

    @property
    def display_text(self) -> str:
        """Text to be spoken - use formal_name."""
        return self.formal_name


@dataclass
class Team:
    """Team data from teams.json."""

    id: str
    name: str
    display_name: Optional[str] = None
    organization_id: Optional[str] = None

    @property
    def display_text(self) -> str:
        """Text to be spoken - prefer display_name over name."""
        return self.display_name or self.name


class Config(BaseModel):
    """Configuration stored in icpc-audio.yaml."""

    credentials_path: Optional[str] = None
    language: str = "en-US"
    voice: str = "en-US-Wavenet-D"
    format: str = "mp3"
    mode: str = "teams"
    jobs: int = 4


@dataclass
class GenerationConfig:
    """Runtime configuration for audio generation."""

    folder_path: Path
    mode: Mode
    audio_format: AudioFormat
    language: str
    voice: str
    credentials_path: Optional[Path]
    jobs: int
    force: bool = False
    dry_run: bool = False
