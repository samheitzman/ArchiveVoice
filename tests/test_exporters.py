from __future__ import annotations

import json

from archive_voice.constants import QUALITY_WARNING, SPEAKER_WARNING, TRANSLATION_WARNING
from archive_voice.diarization import assign_speakers_to_segments
from archive_voice.exporters import (
    empty_result_for_tests,
    export_all,
    export_translation_all,
    export_json,
    export_txt,
    format_timestamp,
    detect_segment_language,
    render_transcript_text,
    render_translation_text,
    render_reading_paragraphs,
    split_reading_units,
    style_uses_timestamps,
    transcript_base_path,
    translation_source_label,
    unique_output_path,
)
from archive_voice.models import TranscriptSegment
from archive_voice.models import SpeakerTurn


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


def test_translation_output_is_clearly_labeled() -> None:
    result = empty_result_for_tests("Polish.mp3")
    result.metadata.output_mode = "Machine English translation, not English-language transcription"
    result.segments[0].text = "Wait, Grandma."

    text = render_translation_text(result, include_timestamps=True)

    assert text.startswith("MACHINE ENGLISH TRANSLATION")
    assert "not an original-language transcript" in text
    assert "not an English-language transcription" in text
    assert "Output mode: Machine English translation, not English-language transcription" in text
    assert "[00:00:00 - 00:00:12]" in text
    assert TRANSLATION_WARNING in text


def test_translation_output_labels_original_english_and_translated_speech() -> None:
    result = empty_result_for_tests("Mixed.mp3")
    result.metadata.output_mode = "Machine English translation, not English-language transcription"
    result.segments = [
        TranscriptSegment(0.0, 4.0, "Do you have any questions?"),
        TranscriptSegment(4.0, 9.0, "Wait, Grandma."),
    ]
    source_segments = [
        TranscriptSegment(0.0, 4.0, "Do you have any questions?"),
        TranscriptSegment(4.0, 9.0, "Czekaj, babcia."),
    ]

    text = render_translation_text(result, include_timestamps=True, source_segments=source_segments)

    assert "Original English speech: Do you have any questions?" in text
    assert "Machine translation from non-English speech: Wait, Grandma." in text


def test_translation_output_includes_speaker_and_source_labels() -> None:
    result = empty_result_for_tests("Mixed.mp3")
    result.metadata.output_mode = "Machine English translation, not English-language transcription"
    result.segments = [
        TranscriptSegment(0.0, 4.0, "Do you have any questions?"),
        TranscriptSegment(4.0, 9.0, "Wait, Grandma."),
    ]
    source_segments = [
        TranscriptSegment(0.0, 4.0, "Do you have any questions?", speaker_label="Speaker 1"),
        TranscriptSegment(4.0, 9.0, "Czekaj, babcia.", speaker_label="Speaker 2"),
    ]

    text = render_translation_text(result, include_timestamps=True, source_segments=source_segments)

    assert "Speaker 1, Original English speech: Do you have any questions?" in text
    assert "Speaker 2, Machine translation from non-English speech: Wait, Grandma." in text
    assert SPEAKER_WARNING in text


def test_translation_source_label_uses_timestamp_overlap() -> None:
    source_segments = [
        TranscriptSegment(0.0, 3.0, "Do you have any questions?"),
        TranscriptSegment(3.0, 8.0, "A jak pani tutaj była?"),
    ]

    assert translation_source_label(TranscriptSegment(0.5, 2.0, "Do you have any questions?"), source_segments) == (
        "Original English speech"
    )
    assert translation_source_label(TranscriptSegment(3.5, 7.0, "When you were here?"), source_segments) == (
        "Machine translation from non-English speech"
    )


def test_transcript_output_includes_speaker_labels_and_warning() -> None:
    result = empty_result_for_tests("Interview_01.mp3")
    result.segments = [
        TranscriptSegment(0.0, 4.0, "My name is Anna.", speaker_label="Speaker 1"),
        TranscriptSegment(4.0, 9.0, "Do you have any questions?", speaker_label="Speaker 2"),
    ]

    text = render_transcript_text(result, "Research Transcript", include_timestamps=True)

    assert "Speaker 1: My name is Anna." in text
    assert "Speaker 2: Do you have any questions?" in text
    assert SPEAKER_WARNING in text


def test_assign_speakers_to_segments_uses_largest_overlap() -> None:
    segments = [
        TranscriptSegment(0.0, 4.0, "First speaker."),
        TranscriptSegment(4.0, 9.0, "Second speaker."),
    ]
    speaker_turns = [
        SpeakerTurn(0.0, 4.5, "Speaker 1"),
        SpeakerTurn(4.5, 9.0, "Speaker 2"),
    ]

    assigned = assign_speakers_to_segments(segments, speaker_turns)

    assert [segment.speaker_label for segment in assigned] == ["Speaker 1", "Speaker 2"]


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
    single_style = transcript_base_path(
        tmp_path / "Interview 01.mp3",
        tmp_path,
        "Reading Transcript",
        use_style_suffix=False,
    )

    assert research.name == "Interview 01_research_transcript"
    assert clean.name == "Interview 01_clean_transcript"
    assert reading.name == "Interview 01_reading_transcript"
    assert single_style.name == "Interview 01"


def test_unique_output_path_adds_counter(tmp_path) -> None:
    existing = tmp_path / "Interview_01_reading_transcript.txt"
    existing.write_text("previous transcript", encoding="utf-8")

    path = unique_output_path(existing)

    assert path.name == "Interview_01_reading_transcript_2.txt"


def test_style_timestamp_defaults() -> None:
    assert style_uses_timestamps("Research Transcript", include_timestamps=False)
    assert style_uses_timestamps("Timestamped Transcript", include_timestamps=False)
    assert not style_uses_timestamps("Clean Transcript", include_timestamps=False)
    assert not style_uses_timestamps("Reading Transcript", include_timestamps=True)


def test_reading_paragraphs_break_on_pause() -> None:
    result = empty_result_for_tests()
    result.segments[1].start = 15.0

    paragraphs = render_reading_paragraphs(result.segments, pause_break_seconds=1.6)

    assert paragraphs == ["My name is Anna.", "", "I remember the winter very clearly.", ""]


def test_reading_paragraphs_break_on_language_change() -> None:
    result = empty_result_for_tests()
    result.segments[0].text = (
        "Czekaj, babcia. Do you have any questions? "
        "A jak pani tutaj była, czy pani widziała więźniów żydowskich?"
    )
    result.segments[1].text = "Because she starts to say the same thing over."

    paragraphs = render_reading_paragraphs(result.segments)

    assert paragraphs == [
        "[Polish] Czekaj, babcia.",
        "",
        "[English] Do you have any questions?",
        "",
        "[Polish] A jak pani tutaj była, czy pani widziała więźniów żydowskich?",
        "",
        "[English] Because she starts to say the same thing over.",
        "",
    ]


def test_split_reading_units() -> None:
    units = split_reading_units("Czekaj, babcia. Do you have any questions? A jak pani tutaj była?")

    assert units == ["Czekaj, babcia.", "Do you have any questions?", "A jak pani tutaj była?"]


def test_split_reading_units_uses_interview_cues() -> None:
    units = split_reading_units(
        "Te ręce były chude, aż sine i czarne. Dobra babcia, przetłumaczymy. "
        "She said that she was always scared and they hid."
    )

    assert units == [
        "Te ręce były chude, aż sine i czarne.",
        "Dobra babcia, przetłumaczymy.",
        "She said that she was always scared and they hid.",
    ]


def test_reading_paragraphs_break_on_questions() -> None:
    result = empty_result_for_tests()
    result.segments[0].text = "Czy pani pamięta tych ludzi? Tak, pamiętam. Oni mieli czarne mundury."
    result.segments[1].text = "Do you have any questions? She starts to say the same thing over."

    paragraphs = render_reading_paragraphs(result.segments)

    assert paragraphs == [
        "[Polish] Czy pani pamięta tych ludzi?",
        "",
        "[Polish] Tak, pamiętam. Oni mieli czarne mundury.",
        "",
        "[English] Do you have any questions?",
        "",
        "[English] She starts to say the same thing over.",
        "",
    ]


def test_detect_segment_language() -> None:
    assert detect_segment_language("A jak pani tutaj była, czy pani widziała więźniów?") == "Polish"
    assert detect_segment_language("Do you have any questions?") == "English"


def test_export_txt_writes_utf8(tmp_path) -> None:
    result = empty_result_for_tests("Polish.mp3")
    result.segments[0].text = "Lodz, Warszawa, Krakow."
    output_path = tmp_path / "Polish_transcript.txt"

    export_txt(result, output_path, "Research Transcript", include_timestamps=True)

    assert "Lodz, Warszawa, Krakow." in output_path.read_text(encoding="utf-8")


def test_export_txt_does_not_overwrite_existing_file(tmp_path) -> None:
    result = empty_result_for_tests("Polish.mp3")
    output_path = tmp_path / "Polish_transcript.txt"
    output_path.write_text("previous transcript", encoding="utf-8")

    created = export_txt(result, output_path, "Research Transcript", include_timestamps=True)

    assert created.name == "Polish_transcript_2.txt"
    assert output_path.read_text(encoding="utf-8") == "previous transcript"
    assert "Interview: Polish.mp3" in created.read_text(encoding="utf-8")


def test_export_json_sidecar(tmp_path) -> None:
    result = empty_result_for_tests()
    output_path = tmp_path / "Interview_01_transcript.json"

    export_json(result, output_path)

    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["source_file"] == "Interview_01.mp3"
    assert data["detected_language"] == "en"
    assert data["segments"][0]["text"] == "My name is Anna."


def test_export_json_does_not_overwrite_existing_file(tmp_path) -> None:
    result = empty_result_for_tests()
    output_path = tmp_path / "Interview_01_transcript.json"
    output_path.write_text('{"previous": true}', encoding="utf-8")

    created = export_json(result, output_path)

    assert created.name == "Interview_01_transcript_2.json"
    assert json.loads(output_path.read_text(encoding="utf-8")) == {"previous": True}


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


def test_export_all_single_style_matches_audio_filename(tmp_path) -> None:
    result = empty_result_for_tests("Interview_01.mp3")

    created = export_all(
        result,
        audio_path=tmp_path / "Interview_01.mp3",
        output_dir=tmp_path,
        styles=["Reading Transcript"],
        include_timestamps=False,
        write_txt=True,
        write_docx=False,
        write_json_sidecar=False,
    )

    assert [path.name for path in created] == ["Interview_01.txt"]
    assert "My name is Anna." in created[0].read_text(encoding="utf-8")


def test_export_translation_all_uses_separate_filename_and_no_overwrite(tmp_path) -> None:
    result = empty_result_for_tests("Interview_01.mp3")
    existing = tmp_path / "Interview_01_english_translation.txt"
    existing.write_text("previous translation", encoding="utf-8")

    created = export_translation_all(
        result,
        audio_path=tmp_path / "Interview_01.mp3",
        output_dir=tmp_path,
        include_timestamps=True,
        write_txt=True,
        write_docx=False,
        source_segments=result.segments,
    )

    assert [path.name for path in created] == ["Interview_01_english_translation_2.txt"]
    assert existing.read_text(encoding="utf-8") == "previous translation"
    assert "MACHINE ENGLISH TRANSLATION" in created[0].read_text(encoding="utf-8")
