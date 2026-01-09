"""Google Text-to-Speech API wrapper."""

import os
from pathlib import Path
from typing import Optional

from google.cloud import texttospeech


class TTSClient:
    """Wrapper for Google Text-to-Speech API."""

    ENCODING_MAP = {
        "mp3": texttospeech.AudioEncoding.MP3,
        "wav": texttospeech.AudioEncoding.LINEAR16,  # Includes WAV header
        "m4a": texttospeech.AudioEncoding.M4A,
        "ogg": texttospeech.AudioEncoding.OGG_OPUS,
    }

    def __init__(self, credentials_path: Optional[Path] = None):
        """Initialize TTS client with optional credentials path."""
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_path)
        self._client = texttospeech.TextToSpeechClient()

    def list_voices(
        self, language_code: Optional[str] = None
    ) -> list[texttospeech.Voice]:
        """List available voices, optionally filtered by language."""
        response = self._client.list_voices(language_code=language_code)
        return list(response.voices)

    def list_languages(self) -> list[str]:
        """Get list of unique language codes."""
        voices = self.list_voices()
        languages: set[str] = set()
        for voice in voices:
            for lang in voice.language_codes:
                languages.add(lang)
        return sorted(languages)

    def synthesize(
        self,
        text: str,
        language_code: str,
        voice_name: str,
        audio_format: str,
    ) -> bytes:
        """Synthesize speech and return audio bytes."""
        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name,
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=self.ENCODING_MAP[audio_format],
        )

        response = self._client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )

        return response.audio_content
