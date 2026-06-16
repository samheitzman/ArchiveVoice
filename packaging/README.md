# Packaging Archive Voice

Use these files to build a double-clickable app for a non-technical recipient.

Build on the same operating system you plan to distribute:

- Build the macOS `.app` on macOS.
- Build the Windows `.exe` folder on Windows.

PyInstaller does not cross-compile Mac apps from Windows or Windows apps from Mac.

## Bundled Assets

Archive Voice looks for bundled runtime assets here:

```text
packaging/assets/bin/
packaging/assets/models/
```

For a fully offline handoff, include:

- `packaging/assets/bin/ffmpeg` and `packaging/assets/bin/ffprobe` on macOS
- `packaging/assets/bin/ffmpeg.exe` and `packaging/assets/bin/ffprobe.exe` on Windows
- CTranslate2/faster-whisper model folders such as:
  - `packaging/assets/models/small/`
  - `packaging/assets/models/medium/`
  - `packaging/assets/models/large-v3/`
- Optional pyannote diarization model folder for speaker tags:
  - `packaging/assets/models/pyannote-speaker-diarization-community-1/`

The app can still run without bundled models if the machine already has model access/cache, but that is not a true offline handoff.

## Recommended Handoff Build

For a journalist or historian who just needs to click and run, build with:

- bundled `ffmpeg` and `ffprobe`
- bundled `small` or `medium` model for reasonable app size
- `large-v3` only when the recipient has enough disk/RAM and accuracy matters more than package size
- bundled pyannote diarization model only if the recipient needs speaker tags offline

Archive Voice also bundles PyAV/FFmpeg libraries through Python dependencies. If external `ffmpeg` or `ffprobe` is missing or cannot run on a Mac, the app falls back to packaged audio metadata handling.

## macOS

From the project root:

```bash
packaging/scripts/build_macos.sh
```

Output:

```text
dist/Archive Voice.app
dist/ArchiveVoice-0.2.0-mac-arm64.dmg
```

The current macOS build produced on an Apple Silicon Mac is `arm64`. It is intended for Apple Silicon Macs. For Intel Macs, build on an Intel Mac or set up a universal build with universal Python/native dependencies.

This repository includes a manual GitHub Actions workflow, `Build macOS Intel DMG`, that runs on GitHub's Intel macOS runner and builds `ArchiveVoice-<version>-mac-x64.dmg`.

For distribution outside your own machine, sign and notarize the app with your Apple Developer certificate. Unsigned or ad-hoc-signed apps may require right-click > Open on the recipient's Mac and are not truly foolproof under Gatekeeper.

## Windows

From PowerShell in the project root:

```powershell
.\packaging\scripts\build_windows.ps1
```

Output:

```text
dist\Archive Voice\Archive Voice.exe
```

Zip the whole `dist\Archive Voice` folder and send that folder to the recipient. The `.exe` depends on the adjacent bundled files in that folder.
