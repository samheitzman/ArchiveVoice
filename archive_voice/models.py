from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


@dataclass
class TranscriptMetadata:
    source_file: str
    source_path: str
    transcribed_at: datetime
    model: str
    language_mode: str
    language_code: str | None
    detected_language: str | None = None
    detected_language_probability: float | None = None
    output_mode: str = "Original language transcript"
    duration_seconds: float | None = None


@dataclass
class TranscriptResult:
    metadata: TranscriptMetadata
    segments: list[TranscriptSegment]


@dataclass
class TranscriptionSettings:
    output_dir: Path
    write_txt: bool = True
    write_docx: bool = True
    write_json: bool = False
    model_size: str = "large-v3"
    language_label: str = "Auto-detect"
    language_code: str | None = None
    output_styles: list[str] = field(default_factory=lambda: ["Research Transcript"])
    include_timestamps: bool = True
    vad_filter: bool = True
    beam_size: int = 5
    initial_prompt: str = ""
    keep_filler_words: bool = True
    segment_length_preference: str = "Model default"
    created_paths: list[Path] = field(default_factory=list)
