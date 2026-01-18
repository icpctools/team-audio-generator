"""Google Gemini Text-to-Speech API wrapper."""

import base64
import os
import time
from pathlib import Path
from typing import Optional

import google.auth
import google.auth.transport.requests
import requests
from rich.console import Console

console = Console()

API_URL = "https://texttospeech.googleapis.com/v1beta1/text:synthesize"

# Gemini TTS voices - one male, one female
VOICES = {
    "male": "Achird",
    "female": "Achernar",
}

# Audio encoding map
ENCODING_MAP = {
    "mp3": "MP3",
    "wav": "LINEAR16",
    "m4a": "ALAW",
    "ogg": "OGG_OPUS",
}


class TTSClient:
    """Wrapper for Google Gemini Text-to-Speech API."""

    def __init__(self, credentials_path: Optional[Path] = None):
        """Initialize TTS client with optional credentials path."""
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_path)
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0

    def _get_access_token(self) -> str:
        """Get or refresh access token."""
        current_time = time.time()
        if self._access_token and current_time < self._token_expiry - 60:
            return self._access_token

        credentials, project = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        self._access_token = credentials.token
        # Token typically valid for 1 hour
        self._token_expiry = current_time + 3600
        return self._access_token

    def synthesize(
        self,
        text: str,
        prompt: str,
        language_code: str,
        gender: str,
        audio_format: str,
        max_retries: int = 5,
    ) -> bytes:
        """Synthesize speech using Gemini TTS REST API with retry on rate limit."""
        access_token = self._get_access_token()
        voice_name = VOICES[gender]

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        body = {
            "audioConfig": {
                "audioEncoding": ENCODING_MAP.get(audio_format, "LINEAR16"),
                "pitch": 0,
                "speakingRate": 1,
            },
            "input": {
                "prompt": prompt,
                "text": text,
            },
            "voice": {
                "languageCode": language_code,
                "modelName": "gemini-2.5-pro-tts",
                "name": voice_name,
            },
        }

        wait_time = 10
        for attempt in range(max_retries):
            response = requests.post(API_URL, headers=headers, json=body)

            if response.status_code == 429:
                console.print(
                    f"[yellow]rate limited, waiting {wait_time}s...[/yellow]", end=" "
                )
                time.sleep(wait_time)
                wait_time = min(wait_time * 2, 120)
                continue

            response.raise_for_status()
            result = response.json()
            return base64.b64decode(result["audioContent"])

        raise Exception(f"Rate limited after {max_retries} retries")
