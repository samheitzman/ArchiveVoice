from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .constants import QUALITY_WARNING
from .models import TranscriptResult, TranscriptSegment


def format_timestamp(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "Unknown"
    return format_timestamp(seconds)


def style_slug(style: str) -> str:
    return {
        "Research Transcript": "research_transcript",
        "Timestamped Transcript": "timestamped_transcript",
        "Clean Transcript": "clean_transcript",
        "Reading Transcript": "reading_transcript",
    }.get(style, "transcript")


def style_uses_timestamps(style: str, include_timestamps: bool) -> bool:
    if style in {"Research Transcript", "Timestamped Transcript"}:
        return True
    if style in {"Clean Transcript", "Reading Transcript"}:
        return False
    return include_timestamps


def transcript_base_path(audio_path: Path, output_dir: Path, style: str) -> Path:
    suffix = style_slug(style)
    return output_dir / f"{audio_path.stem}_{suffix}"


def render_transcript_text(result: TranscriptResult, style: str, include_timestamps: bool) -> str:
    metadata = result.metadata
    lines: list[str] = []

    if style == "Research Transcript":
        lines.extend(
            [
                f"Interview: {metadata.source_file}",
                f"Source path: {metadata.source_path}",
                f"Transcribed: {metadata.transcribed_at.isoformat(timespec='seconds')}",
                f"Model: {metadata.model}",
                f"Language mode: {metadata.language_mode}",
                f"Detected language: {metadata.detected_language or 'Not available'}",
                f"Output mode: {metadata.output_mode}",
                f"Duration: {format_duration(metadata.duration_seconds)}",
                "",
            ]
        )

    if style == "Reading Transcript":
        lines.extend(render_reading_paragraphs(result.segments))
    else:
        for segment in result.segments:
            if style == "Clean Transcript" and not include_timestamps:
                lines.append(segment.text)
            elif style == "Research Transcript":
                lines.append(f"[{format_timestamp(segment.start)} - {format_timestamp(segment.end)}]")
                lines.append(segment.text)
                lines.append("")
            else:
                lines.append(f"[{format_timestamp(segment.start)}] {segment.text}")

    lines.extend(["", "Notes:", f"- {QUALITY_WARNING}"])
    return "\n".join(lines).strip() + "\n"


def render_reading_paragraphs(
    segments: list[TranscriptSegment],
    pause_break_seconds: float = 1.6,
    max_paragraph_chars: int = 900,
) -> list[str]:
    paragraphs: list[str] = []
    current_parts: list[str] = []
    current_length = 0
    previous_end: float | None = None

    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        gap = 0.0 if previous_end is None else max(0.0, segment.start - previous_end)
        should_break = bool(current_parts) and (
            gap >= pause_break_seconds or current_length + len(text) > max_paragraph_chars
        )
        if should_break:
            paragraphs.append(" ".join(current_parts))
            paragraphs.append("")
            current_parts = []
            current_length = 0
        current_parts.append(text)
        current_length += len(text) + 1
        previous_end = segment.end

    if current_parts:
        paragraphs.append(" ".join(current_parts))

    return paragraphs


def export_txt(result: TranscriptResult, path: Path, style: str, include_timestamps: bool) -> Path:
    path.write_text(render_transcript_text(result, style, include_timestamps), encoding="utf-8")
    return path


def export_docx(result: TranscriptResult, path: Path, style: str, include_timestamps: bool) -> Path:
    try:
        from docx import Document
        from docx.enum.text import WD_BREAK
        from docx.shared import Inches
    except ImportError as exc:
        raise RuntimeError(
            "python-docx is not installed. Install the app requirements to export DOCX files."
        ) from exc

    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)

    metadata = result.metadata
    document.add_heading(metadata.source_file, level=1)

    table = document.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    rows = [
        ("Source audio file", metadata.source_file),
        ("Original file path", metadata.source_path),
        ("Date/time transcribed", metadata.transcribed_at.isoformat(timespec="seconds")),
        ("Model used", metadata.model),
        ("Language mode", metadata.language_mode),
        ("Detected language", metadata.detected_language or "Not available"),
        ("Output mode", metadata.output_mode),
        ("Duration", format_duration(metadata.duration_seconds)),
    ]
    for label, value in rows:
        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = value

    document.add_paragraph()
    document.add_heading("Transcript", level=2)

    if style == "Reading Transcript":
        for paragraph_text in render_reading_paragraphs(result.segments):
            if paragraph_text:
                document.add_paragraph(paragraph_text)
    elif style == "Clean Transcript" and not include_timestamps:
        for segment in result.segments:
            document.add_paragraph(segment.text)
    else:
        for segment in result.segments:
            if style == "Research Transcript":
                stamp = f"[{format_timestamp(segment.start)} - {format_timestamp(segment.end)}]"
                document.add_paragraph(stamp, style=None)
                document.add_paragraph(segment.text)
            else:
                document.add_paragraph(f"[{format_timestamp(segment.start)}] {segment.text}")

    document.add_paragraph()
    document.add_heading("Notes", level=2)
    paragraph = document.add_paragraph(QUALITY_WARNING)
    paragraph.runs[-1].add_break(WD_BREAK.LINE)
    document.add_paragraph("Names, dates, places and unclear passages require human verification.", style=None)

    document.save(path)
    return path


def export_json(result: TranscriptResult, path: Path) -> Path:
    metadata = result.metadata
    payload = {
        "source_file": metadata.source_file,
        "source_path": metadata.source_path,
        "transcribed_at": metadata.transcribed_at.isoformat(timespec="seconds"),
        "model": metadata.model,
        "language_mode": metadata.language_mode,
        "language_code": metadata.language_code,
        "detected_language": metadata.detected_language,
        "detected_language_probability": metadata.detected_language_probability,
        "output_mode": metadata.output_mode,
        "duration_seconds": metadata.duration_seconds,
        "segments": [
            {"start": segment.start, "end": segment.end, "text": segment.text}
            for segment in result.segments
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def export_all(
    result: TranscriptResult,
    audio_path: Path,
    output_dir: Path,
    styles: list[str],
    include_timestamps: bool,
    write_txt: bool,
    write_docx: bool,
    write_json_sidecar: bool,
) -> list[Path]:
    created: list[Path] = []
    for style in styles:
        base_path = transcript_base_path(audio_path, output_dir, style)
        timestamps_for_style = style_uses_timestamps(style, include_timestamps)
        if write_txt:
            created.append(export_txt(result, base_path.with_suffix(".txt"), style, timestamps_for_style))
        if write_docx:
            created.append(export_docx(result, base_path.with_suffix(".docx"), style, timestamps_for_style))
    if write_json_sidecar:
        base_path = output_dir / f"{audio_path.stem}_transcript_segments"
        created.append(export_json(result, base_path.with_suffix(".json")))
    return created


def empty_result_for_tests(source_file: str = "Interview_01.mp3") -> TranscriptResult:
    from .models import TranscriptMetadata

    return TranscriptResult(
        metadata=TranscriptMetadata(
            source_file=source_file,
            source_path=f"/archive/{source_file}",
            transcribed_at=datetime(2026, 6, 16, 14, 0, 0),
            model="large-v3",
            language_mode="Auto-detect",
            language_code=None,
            detected_language="en",
            duration_seconds=31.0,
        ),
        segments=[
            TranscriptSegment(0.0, 12.0, "My name is Anna."),
            TranscriptSegment(12.0, 31.0, "I remember the winter very clearly."),
        ],
    )
