# Archive Voice

Archive Voice is a local desktop transcription app for oral history, journalism and historical interviews.

It uses `faster-whisper` locally. Audio is not uploaded to cloud transcription services.

## Features

- Batch transcription for MP3 files, with optional WAV, M4A, AAC and FLAC support
- Multilingual Whisper models only: `large-v3`, `medium`, and `small`
- Language modes: Auto-detect, English, Polish, German, Latvian
- Research, timestamped, and clean transcript styles
- TXT and DOCX export
- Optional JSON sidecar with segment metadata
- Background processing with cancellation
- Traceable transcript metadata and journalistic verification warnings

## Requirements

- Python 3.11 or 3.12
- `ffmpeg` and `ffprobe` available on your PATH
- Enough local disk/RAM for the selected Whisper model

Install Python dependencies:

```bash
python -m pip install -e .
```

Run the app:

```bash
python -m archive_voice
```

## Building a Clickable App

For a non-technical user, do not ask them to install Python packages. Build a packaged app instead.

See [packaging/README.md](packaging/README.md).

Important:

- `ffmpeg` does not auto-download. Bundle `ffmpeg` and `ffprobe` in `packaging/assets/bin/` before building.
- Whisper models may download on first use if they are not bundled and the computer has internet access, but that is not ideal for a handoff.
- For a self-contained offline app, bundle at least one model folder in `packaging/assets/models/` before building.
- Build separately on each operating system: macOS builds the `.app`; Windows builds the `.exe` folder.

## Offline Use

The app does not upload audio or call cloud transcription APIs. The first use of a named faster-whisper model may require the model to be present locally or downloaded by faster-whisper/CTranslate2 tooling. For fully offline work, download or bundle the selected multilingual model before disconnecting from the internet.

## Output Warning

Every transcript includes:

> This is a machine-generated transcript. It should be checked against the original recording before quotation, publication or archival use. Names, dates, places and unclear passages require human verification.
