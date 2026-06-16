from __future__ import annotations

from collections import OrderedDict

APP_NAME = "Archive Voice"
SUBTITLE = "Local transcription for oral history, journalism and historical interviews"
PRIVACY_NOTE = "All transcription runs locally on this computer. Your audio is not uploaded."

LANGUAGE_CODES = OrderedDict(
    {
        "Auto-detect": None,
        "English": "en",
        "Polish": "pl",
        "German": "de",
        "Latvian": "lv",
    }
)

MODEL_OPTIONS = OrderedDict(
    {
        "High Accuracy: large-v3": "large-v3",
        "Standard: medium": "medium",
        "Fast: small": "small",
    }
)

OUTPUT_STYLES = (
    "Research Transcript",
    "Timestamped Transcript",
    "Clean Transcript",
    "Reading Transcript",
)

OUTPUT_STYLE_DESCRIPTIONS = (
    "Research: metadata, source path and segment timestamps for checking.",
    "Timestamped: simple timestamped lines for reviewing against audio.",
    "Clean: plain segment text without timestamps.",
    "Reading: paragraph-style text for reading, with no wording changes.",
)

SPEAKER_COUNT_OPTIONS = ("Auto", "2", "3", "4", "5")

SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac"}
REQUIRED_AUDIO_EXTENSION = ".mp3"

QUALITY_WARNING = (
    "This is a machine-generated transcript. It should be checked against the "
    "original recording before quotation, publication or archival use. Names, "
    "dates, places and unclear passages require human verification."
)

TRANSLATION_WARNING = (
    "This is a machine-generated English translation, not an original-language "
    "transcript and not an English-language transcription. It should be checked "
    "against the original recording and the original-language transcript before "
    "quotation, publication or archival use."
)

SPEAKER_WARNING = (
    "Speaker labels are machine-estimated from voice characteristics and timing. "
    "They should be checked against the original recording before quotation, "
    "publication or archival use."
)

DEFAULT_CONTEXT_PROMPT = (
    "This is an oral history interview about war, historical events, personal "
    "memory, displacement, family history, places, dates and names. The speaker "
    "may be speaking English, Polish, German or Latvian. Preserve names, places, "
    "dates and uncertainty. Do not summarise. Do not rewrite testimony. "
    "Transcribe as accurately as possible."
)

LANGUAGE_CONTEXT_PROMPTS = {
    "English": (
        "This is English speech, possibly spoken by a non-native speaker with a "
        "Polish, German or Latvian accent. Transcribe the English accurately. "
        "Do not translate. Preserve names, places, dates and uncertainty."
    ),
    "Polish": (
        "This is Polish speech in an oral history interview about war, historical "
        "events and personal memory. Transcribe the Polish accurately. Preserve "
        "names, places, dates and uncertainty. Do not translate unless translation "
        "output is specifically enabled."
    ),
    "German": (
        "This is German speech in an oral history interview about war, historical "
        "events and personal memory. Transcribe the German accurately. Preserve "
        "names, places, dates and uncertainty. Do not translate unless translation "
        "output is specifically enabled."
    ),
    "Latvian": (
        "This is Latvian speech in an oral history interview about war, historical "
        "events and personal memory. Transcribe the Latvian accurately. Preserve "
        "names, places, dates and uncertainty. Do not translate unless translation "
        "output is specifically enabled."
    ),
}
