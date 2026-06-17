from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from collections.abc import Iterator

from .models import SpeakerTurn, TranscriptSegment
from .runtime import bundled_binary, bundled_diarization_model_path


DIARIZATION_MODEL_ID = "pyannote/speaker-diarization-community-1"


def run_speaker_diarization(audio_path: Path, speaker_count_label: str = "Auto") -> list[SpeakerTurn]:
    try:
        from pyannote.audio import Pipeline
    except ImportError as exc:
        raise RuntimeError(
            "Speaker tagging needs pyannote.audio. Install the v0.4 requirements or turn off speaker tagging."
        ) from exc

    model_source = diarization_model_source()
    try:
        pipeline = load_pipeline(Pipeline, model_source)
    except Exception as exc:
        raise RuntimeError(
            "Archive Voice could not load the speaker tagging model. To use speaker tagging, accept the "
            "pyannote model terms on Hugging Face, set an HF_TOKEN, or bundle the diarization model for offline use."
        ) from exc

    kwargs = speaker_count_kwargs(speaker_count_label)
    try:
        with diarization_audio_path(audio_path) as prepared_audio_path:
            output = pipeline(str(prepared_audio_path), **kwargs)
    except Exception as exc:
        raise RuntimeError(f"Archive Voice could not identify speakers in this file: {exc}") from exc

    return normalize_speaker_turns(extract_speaker_turns(output))


@contextmanager
def diarization_audio_path(audio_path: Path) -> Iterator[Path]:
    ffmpeg = resolve_binary("ffmpeg")
    if ffmpeg is None:
        yield audio_path
        return
    with tempfile.TemporaryDirectory(prefix="archive-voice-diarization-") as temp_dir:
        prepared_path = Path(temp_dir) / f"{audio_path.stem}_diarization.wav"
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(audio_path),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-acodec",
                "pcm_s16le",
                str(prepared_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        yield prepared_path


def resolve_binary(name: str) -> str | None:
    bundled = bundled_binary(name)
    if bundled is not None:
        return str(bundled)
    return shutil.which(name)


def diarization_model_source() -> str:
    bundled = bundled_diarization_model_path()
    if bundled is not None:
        return str(bundled)
    return DIARIZATION_MODEL_ID


def load_pipeline(pipeline_class, model_source: str):
    if Path(model_source).exists():
        return pipeline_class.from_pretrained(model_source)
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    if token:
        return pipeline_class.from_pretrained(model_source, token=token)
    return pipeline_class.from_pretrained(model_source)


def speaker_count_kwargs(speaker_count_label: str) -> dict[str, int]:
    if speaker_count_label.isdigit():
        return {"num_speakers": int(speaker_count_label)}
    return {"min_speakers": 2, "max_speakers": 5}


def extract_speaker_turns(output) -> list[SpeakerTurn]:
    diarization = getattr(output, "exclusive_speaker_diarization", None)
    if diarization is None:
        diarization = getattr(output, "speaker_diarization", None)
    if diarization is None:
        diarization = output

    turns: list[SpeakerTurn] = []
    if hasattr(diarization, "itertracks"):
        for turn, _track, speaker in diarization.itertracks(yield_label=True):
            turns.append(SpeakerTurn(float(turn.start), float(turn.end), str(speaker)))
        return turns

    for item in diarization:
        if len(item) == 2:
            turn, speaker = item
        else:
            turn, _track, speaker = item
        turns.append(SpeakerTurn(float(turn.start), float(turn.end), str(speaker)))
    return turns


def normalize_speaker_turns(turns: list[SpeakerTurn]) -> list[SpeakerTurn]:
    speaker_names: dict[str, str] = {}
    normalized: list[SpeakerTurn] = []
    for turn in sorted(turns, key=lambda item: (item.start, item.end)):
        if turn.speaker_label not in speaker_names:
            speaker_names[turn.speaker_label] = f"Speaker {len(speaker_names) + 1}"
        normalized.append(
            SpeakerTurn(
                start=turn.start,
                end=turn.end,
                speaker_label=speaker_names[turn.speaker_label],
            )
        )
    return normalized


def assign_speakers_to_segments(
    segments: list[TranscriptSegment],
    speaker_turns: list[SpeakerTurn],
) -> list[TranscriptSegment]:
    return [
        TranscriptSegment(
            start=segment.start,
            end=segment.end,
            text=segment.text,
            speaker_label=best_speaker_for_segment(segment, speaker_turns),
        )
        for segment in segments
    ]


def best_speaker_for_segment(segment: TranscriptSegment, speaker_turns: list[SpeakerTurn]) -> str | None:
    overlap_by_speaker: dict[str, float] = {}
    for turn in speaker_turns:
        overlap = max(0.0, min(segment.end, turn.end) - max(segment.start, turn.start))
        if overlap > 0:
            overlap_by_speaker[turn.speaker_label] = overlap_by_speaker.get(turn.speaker_label, 0.0) + overlap
    if overlap_by_speaker:
        return max(overlap_by_speaker.items(), key=lambda item: item[1])[0]
    nearest = nearest_speaker_turn(segment, speaker_turns)
    return nearest.speaker_label if nearest is not None else None


def nearest_speaker_turn(
    segment: TranscriptSegment,
    speaker_turns: list[SpeakerTurn],
    max_gap_seconds: float = 1.0,
) -> SpeakerTurn | None:
    nearest: SpeakerTurn | None = None
    nearest_gap = max_gap_seconds
    for turn in speaker_turns:
        gap = min(abs(segment.start - turn.end), abs(segment.end - turn.start))
        if gap <= nearest_gap:
            nearest = turn
            nearest_gap = gap
    return nearest
