from __future__ import annotations

import json

from archive_voice.constants import QUALITY_WARNING
from archive_voice.exporters import (
    empty_result_for_tests,
    export_all,
    export_json,
    export_txt,
    format_timestamp,
    render_transcript_text,
    render_reading_paragraphs,
    style_uses_timestamps,
    transcript_base_path,
)


def test_format_timestamp() -> None:
    assert format_timestamp(0) == "00:00:00"
    assert format_timestamp(17.8) == "00:00:17"
    assert format_timestamp(3661.2) == "01:01:01"


def test_research_transcript_includes_traceability() -> None:
    result = empty_result_for_tests()

    text = render_transcript_text(result, "Research Transcript", include_timestamps=True)

    assert "Interview: Interview_01.mp3" in text
    assert "Model: large-v3" in text
    assert "Language mode: Auto-detect" in text
    assert "[00:00:00 - 00:00:12]" in text
    assert QUALITY_WARNING in text


def test_clean_transcript_omits_segment_timestamps() -> None:
    result = empty_result_for_tests()

    text = render_transcript_text(result, "Clean Transcript", include_timestamps=False)

    assert "[00:00:00" not in text
    assert "My name is Anna." in text
    assert QUALITY_WARNING in text


def test_reading_transcript_uses_paragraphs_without_timestamps() -> None:
    result = empty_result_for_tests()

    text = render_transcript_text(result, "Reading Transcript", include_timestamps=False)

    assert "[00:00:00" not in text
    assert "My name is Anna. I remember the winter very clearly." in text
    assert QUALITY_WARNING in text


def test_style_filename_suffixes(tmp_path) -> None:
    research = transcript_base_path(tmp_path / "Interview 01.mp3", tmp_path, "Research Transcript")
    clean = transcript_base_path(tmp_path / "Interview 01.mp3", tmp_path, "Clean Transcript")
    reading = transcript_base_path(tmp_path / "Interview 01.mp3", tmp_path, "Reading Transcript")

    assert research.name == "Interview 01_research_transcript"
    assert clean.name == "Interview 01_clean_transcript"
    assert reading.name == "Interview 01_reading_transcript"


def test_style_timestamp_defaults() -> None:
    assert style_uses_timestamps("Research Transcript", include_timestamps=False)
    assert style_uses_timestamps("Timestamped Transcript", include_timestamps=False)
    assert not style_uses_timestamps("Clean Transcript", include_timestamps=False)
    assert not style_uses_timestamps("Reading Transcript", include_timestamps=True)


def test_reading_paragraphs_break_on_pause() -> None:
    result = empty_result_for_tests()
    result.segments[1].start = 15.0

    paragraphs = render_reading_paragraphs(result.segments, pause_break_seconds=1.6)

    assert paragraphs == ["My name is Anna.", "", "I remember the winter very clearly."]


def test_export_txt_writes_utf8(tmp_path) -> None:
    result = empty_result_for_tests("Polish.mp3")
    result.segments[0].text = "Lodz, Warszawa, Krakow."
    output_path = tmp_path / "Polish_transcript.txt"

    export_txt(result, output_path, "Research Transcript", include_timestamps=True)

    assert "Lodz, Warszawa, Krakow." in output_path.read_text(encoding="utf-8")


def test_export_json_sidecar(tmp_path) -> None:
    result = empty_result_for_tests()
    output_path = tmp_path / "Interview_01_transcript.json"

    export_json(result, output_path)

    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["source_file"] == "Interview_01.mp3"
    assert data["detected_language"] == "en"
    assert data["segments"][0]["text"] == "My name is Anna."


def test_export_all_writes_multiple_styles(tmp_path) -> None:
    result = empty_result_for_tests("Interview_01.mp3")

    created = export_all(
        result,
        audio_path=tmp_path / "Interview_01.mp3",
        output_dir=tmp_path,
        styles=["Research Transcript", "Clean Transcript", "Reading Transcript"],
        include_timestamps=False,
        write_txt=True,
        write_docx=False,
        write_json_sidecar=True,
    )

    names = sorted(path.name for path in created)
    assert names == [
        "Interview_01_clean_transcript.txt",
        "Interview_01_reading_transcript.txt",
        "Interview_01_research_transcript.txt",
        "Interview_01_transcript_segments.json",
    ]
