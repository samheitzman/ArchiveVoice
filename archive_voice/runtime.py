from __future__ import annotations

import os
import platform
import sys
import tempfile
from pathlib import Path


def bundled_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[1]


def resource_path(*parts: str) -> Path:
    return bundled_root().joinpath(*parts)


def binary_name(name: str) -> str:
    if platform.system() == "Windows":
        return f"{name}.exe"
    return name


def bundled_binary(name: str) -> Path | None:
    path = resource_path("assets", "bin", binary_name(name))
    return path if path.exists() else None


def bundled_model_path(model_size: str) -> Path | None:
    path = resource_path("assets", "models", model_size)
    return path if path.exists() else None


def bundled_diarization_model_path() -> Path | None:
    path = resource_path("assets", "models", "pyannote-speaker-diarization-community-1")
    return path if path.exists() else None


def model_size_or_path(model_size: str) -> str:
    bundled = bundled_model_path(model_size)
    if bundled is not None:
        return str(bundled)
    return model_size


def configure_packaged_runtime() -> None:
    bin_dir = resource_path("assets", "bin")
    if bin_dir.exists():
        os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"
    cache_dir = Path(tempfile.gettempdir()) / "archive-voice-cache"
    os.environ.setdefault("MPLCONFIGDIR", str(cache_dir / "matplotlib"))
    os.environ.setdefault("XDG_CACHE_HOME", str(cache_dir))
