from __future__ import annotations

import shutil
import subprocess
import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from .exporters import export_all, export_translation_all
from .models import (
    TranscriptMetadata,
    TranscriptResult,
    TranscriptSegment,
    TranscriptionSettings,
)
from .runtime import bundled_binary, model_size_or_path


class BatchTranscriptionWorker(QObject):
    file_started = Signal(int)
    file_progress = Signal(int, str, str, str)
    duration_detected = Signal(int, str)
    file_finished = Signal(int, str, str)
    file_failed = Signal(int, str)
    batch_progress = Signal(int, int)
    overall_progress = Signal(int)
    log_message = Signal(str)
    finished = Signal()

    def __init__(self, audio_files: list[Path], settings: TranscriptionSettings):
        super().__init__()
        self.audio_files = audio_files
        self.settings = settings
        self._cancelled = False
        self._model = None

    @Slot()
    def cancel(self) -> None:
        self._cancelled = True

    @Slot()
    def run(self) -> None:
        try:
            self.log_message.emit("Starting local transcription batch.")
            self._preflight()
            self._model = self._load_model()
            self.log_message.emit("Model loaded.")
            total = len(self.audio_files)
            for index, audio_path in enumerate(self.audio_files):
                if self._cancelled:
                    self.file_progress.emit(index, "Cancelled", "", "")
                    self.log_message.emit(f"File cancelled before processing: {audio_path.name}")
                    continue
                self.file_started.emit(index)
                self.batch_progress.emit(index, total)
                try:
                    created_paths = self._transcribe_one(index, audio_path)
                    output_text = "\n".join(str(path) for path in created_paths)
                    self.file_finished.emit(index, "Complete", output_text)
                except CancelledError:
                    self.file_progress.emit(index, "Cancelled", "", "")
                    self.log_message.emit(f"File cancelled: {audio_path.name}")
                except Exception as exc:
                    technical = traceback.format_exc()
                    self.log_message.emit(technical)
                    self.file_failed.emit(index, friendly_error(exc))
                    self.log_message.emit("File failed. The rest of the batch will continue.")
            self.batch_progress.emit(total, total)
            self.overall_progress.emit(100)
        except Exception as exc:
            technical = traceback.format_exc()
            self.log_message.emit(technical)
            for index in range(len(self.audio_files)):
                self.file_failed.emit(index, friendly_error(exc))
        finally:
            self.finished.emit()

    def _preflight(self) -> None:
        self.log_message.emit("Checking file list.")
        if not self.audio_files:
            raise RuntimeError("Add at least one interview file before starting transcription.")
        self.log_message.emit("Checking output folder.")
        if not self.settings.output_dir.exists():
            raise RuntimeError("Choose an available output folder before starting transcription.")
        self.log_message.emit(f"Output folder: {self.settings.output_dir}")
        self.log_message.emit("Checking selected output formats.")
        if not self.settings.write_txt and not self.settings.write_docx:
            raise RuntimeError("Select at least one output format: TXT or DOCX.")
        self.log_message.emit("Checking selected output styles.")
        if not self.settings.output_styles:
            raise RuntimeError("Select at least one output style.")
        self.log_message.emit("Checking ffmpeg and ffprobe.")
        ffmpeg = resolve_binary("ffmpeg")
        ffprobe = resolve_binary("ffprobe")
        if ffmpeg is None:
            self.log_message.emit("ffmpeg not found. Archive Voice will use the packaged audio libraries.")
        else:
            self.log_message.emit(f"ffmpeg found: {ffmpeg}")
        if ffprobe is None:
            self.log_message.emit("ffprobe not found. Archive Voice will estimate duration from audio metadata.")
        else:
            self.log_message.emit(f"ffprobe found: {ffprobe}")

    def _load_model(self):
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper is not installed. Install the app requirements and try again."
            ) from exc

        self.log_message.emit(f"Loading local Whisper model: {self.settings.model_size}")
        model_source = model_size_or_path(self.settings.model_size)
        if model_source != self.settings.model_size:
            self.log_message.emit(f"Using bundled model path: {model_source}")
        else:
            self.log_message.emit("Using named model. faster-whisper may download it if it is not cached.")
        try:
            return WhisperModel(
                model_source,
                device="auto",
                compute_type="auto",
            )
        except Exception as exc:
            raise RuntimeError(
                "Archive Voice could not load the selected local transcription model. "
                "The model may be missing, unavailable offline, or too large for this computer."
            ) from exc

    def _transcribe_one(self, row: int, audio_path: Path) -> list[Path]:
        if self._cancelled:
            raise CancelledError()
        if not audio_path.exists():
            raise RuntimeError("The audio file could not be found.")

        self.log_message.emit(f"Processing {audio_path.name}")
        self.log_message.emit("Reading audio duration.")
        duration = probe_duration(audio_path)
        self.duration_detected.emit(row, format_duration_for_ui(duration))
        if duration is None:
            self.log_message.emit("Could not read duration. Continuing without percentage progress.")
        else:
            self.log_message.emit(f"Duration: {format_duration_for_ui(duration)}.")
        self.file_progress.emit(row, "Starting transcription", "", "")
        self.log_message.emit("Starting transcription.")

        segments_iter, info = self._model.transcribe(
            str(audio_path),
            language=self.settings.language_code,
            task="transcribe",
            beam_size=self.settings.beam_size,
            vad_filter=self.settings.vad_filter,
            initial_prompt=self.settings.initial_prompt or None,
        )

        segments: list[TranscriptSegment] = []
        last_logged_percent = -5
        for segment in segments_iter:
            if self._cancelled:
                raise CancelledError()
            text = segment.text.strip()
            if text:
                segments.append(TranscriptSegment(segment.start, segment.end, text))
            if duration:
                percent = progress_percent(segment.end, duration)
                progress_for_bar = percent
                if self.settings.create_english_translation:
                    progress_for_bar = phase_file_percent(0, 70, percent)
                status = (
                    f"Transcribing {format_duration_for_ui(segment.end)} / "
                    f"{format_duration_for_ui(duration)} ({percent}%)"
                )
                self.file_progress.emit(row, status, "", "")
                self.overall_progress.emit(overall_batch_percent(row, len(self.audio_files), progress_for_bar))
                if percent >= last_logged_percent + 5 or percent >= 100:
                    self.log_message.emit(status)
                    last_logged_percent = percent
            else:
                self.file_progress.emit(row, f"Transcribing segment {len(segments)}", "", "")

        if not segments:
            raise RuntimeError("Archive Voice could not detect speech in this file.")
        self.log_message.emit(f"Transcription complete. Segments: {len(segments)}.")
        detected_language = getattr(info, "language", None)
        language_probability = getattr(info, "language_probability", None)
        if detected_language:
            if language_probability is None:
                self.log_message.emit(f"Detected language: {detected_language}.")
            else:
                self.log_message.emit(
                    f"Detected language: {detected_language} ({language_probability:.0%} confidence)."
                )

        metadata = TranscriptMetadata(
            source_file=audio_path.name,
            source_path=str(audio_path),
            transcribed_at=datetime.now().astimezone(),
            model=self.settings.model_size,
            language_mode=self.settings.language_label,
            language_code=self.settings.language_code,
            detected_language=detected_language,
            detected_language_probability=language_probability,
            duration_seconds=duration,
        )
        result = TranscriptResult(metadata=metadata, segments=segments)
        self.file_progress.emit(row, "Writing transcript files", "", "")
        self.log_message.emit(f"Output styles: {', '.join(self.settings.output_styles)}.")
        if self.settings.write_txt:
            self.log_message.emit("Writing TXT transcript.")
        if self.settings.write_docx:
            self.log_message.emit("Writing DOCX transcript.")
        if self.settings.write_json:
            self.log_message.emit("Writing JSON sidecar.")
        created = export_all(
            result,
            audio_path=audio_path,
            output_dir=self.settings.output_dir,
            styles=self.settings.output_styles,
            include_timestamps=self.settings.include_timestamps,
            write_txt=self.settings.write_txt,
            write_docx=self.settings.write_docx,
            write_json_sidecar=self.settings.write_json,
        )
        self.settings.created_paths.extend(created)
        for path in created:
            self.log_message.emit(f"Saved: {path}")
        if self.settings.create_english_translation:
            translation_created = self._translate_one(row, audio_path, duration)
            created.extend(translation_created)
            self.settings.created_paths.extend(translation_created)
            for path in translation_created:
                self.log_message.emit(f"Saved: {path}")
        return created

    def _translate_one(self, row: int, audio_path: Path, duration: float | None) -> list[Path]:
        if self._cancelled:
            raise CancelledError()
        self.file_progress.emit(row, "Starting English translation", "", "")
        self.log_message.emit(
            "Starting English translation pass. This creates machine translation, "
            "not an English-language transcription."
        )

        translation_prompt = (
            "Translate the speech into English for oral history review. Preserve names, "
            "places, dates and uncertainty. Do not summarise."
        )
        segments_iter, info = self._model.transcribe(
            str(audio_path),
            language=self.settings.language_code,
            task="translate",
            beam_size=self.settings.beam_size,
            vad_filter=self.settings.vad_filter,
            initial_prompt=translation_prompt,
        )

        segments: list[TranscriptSegment] = []
        last_logged_percent = -5
        for segment in segments_iter:
            if self._cancelled:
                raise CancelledError()
            text = segment.text.strip()
            if text:
                segments.append(TranscriptSegment(segment.start, segment.end, text))
            if duration:
                percent = progress_percent(segment.end, duration)
                progress_for_bar = phase_file_percent(70, 98, percent)
                status = (
                    f"Translating to English {format_duration_for_ui(segment.end)} / "
                    f"{format_duration_for_ui(duration)} ({percent}%)"
                )
                self.file_progress.emit(row, status, "", "")
                self.overall_progress.emit(overall_batch_percent(row, len(self.audio_files), progress_for_bar))
                if percent >= last_logged_percent + 5 or percent >= 100:
                    self.log_message.emit(status)
                    last_logged_percent = percent
            else:
                self.file_progress.emit(row, f"Translating segment {len(segments)}", "", "")

        if not segments:
            raise RuntimeError("Archive Voice could not create an English translation for this file.")

        detected_language = getattr(info, "language", None)
        language_probability = getattr(info, "language_probability", None)
        metadata = TranscriptMetadata(
            source_file=audio_path.name,
            source_path=str(audio_path),
            transcribed_at=datetime.now().astimezone(),
            model=self.settings.model_size,
            language_mode=self.settings.language_label,
            language_code=self.settings.language_code,
            detected_language=detected_language,
            detected_language_probability=language_probability,
            output_mode="Machine English translation, not English-language transcription",
            duration_seconds=duration,
        )
        result = TranscriptResult(metadata=metadata, segments=segments)

        self.file_progress.emit(row, "Writing English translation files", "", "")
        self.overall_progress.emit(overall_batch_percent(row, len(self.audio_files), 99))
        if self.settings.write_txt:
            self.log_message.emit("Writing TXT English translation.")
        if self.settings.write_docx:
            self.log_message.emit("Writing DOCX English translation.")
        return export_translation_all(
            result,
            audio_path=audio_path,
            output_dir=self.settings.output_dir,
            include_timestamps=self.settings.include_timestamps,
            write_txt=self.settings.write_txt,
            write_docx=self.settings.write_docx,
        )


class CancelledError(Exception):
    pass


def probe_duration(audio_path: Path) -> float | None:
    ffprobe = resolve_binary("ffprobe")
    if ffprobe is not None:
        try:
            result = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(audio_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return float(result.stdout.strip())
        except Exception:
            pass
    return probe_duration_with_av(audio_path)


def probe_duration_with_av(audio_path: Path) -> float | None:
    try:
        import av

        with av.open(str(audio_path)) as container:
            if container.duration is not None:
                return float(container.duration / av.time_base)
            durations = []
            for stream in container.streams.audio:
                if stream.duration is not None and stream.time_base is not None:
                    durations.append(float(stream.duration * stream.time_base))
            if durations:
                return max(durations)
    except Exception:
        return None
    return None


def resolve_binary(name: str) -> str | None:
    bundled = bundled_binary(name)
    if bundled is not None:
        return str(bundled)
    return shutil.which(name)


def format_duration_for_ui(seconds: float | None) -> str:
    if seconds is None:
        return "Unknown"
    total_seconds = max(0, int(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def progress_percent(current_seconds: float, duration_seconds: float) -> int:
    if duration_seconds <= 0:
        return 0
    return min(100, max(0, int((current_seconds / duration_seconds) * 100)))


def phase_file_percent(phase_start: int, phase_end: int, phase_percent: int) -> int:
    phase_percent = min(100, max(0, phase_percent))
    span = max(0, phase_end - phase_start)
    return min(100, max(0, phase_start + int((phase_percent / 100) * span)))


def overall_batch_percent(row: int, total_files: int, file_percent: int) -> int:
    if total_files <= 0:
        return 0
    completed_file_fraction = row / total_files
    current_file_fraction = (file_percent / 100) / total_files
    return min(99, max(0, int((completed_file_fraction + current_file_fraction) * 100)))


def friendly_error(exc: Exception) -> str:
    message = str(exc).strip()
    if not message:
        return (
            "Archive Voice could not transcribe this file. The audio may be corrupted, "
            "unsupported or too unclear. The rest of the batch will continue."
        )
    return message
