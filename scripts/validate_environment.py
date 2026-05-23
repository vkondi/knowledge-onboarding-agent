#!/usr/bin/env python3
"""Validate that the local environment is ready for Knowledge Onboarding Agent.

Checks:
  - Python version >= 3.11
  - Ollama daemon is reachable at localhost:11434
  - Required models are available locally (not just downloaded — confirmed present)
  - Available RAM (requires psutil; skipped if not installed)

Usage:
    python scripts/validate_environment.py

Exit codes:
    0 — all required checks passed
    1 — one or more required checks failed
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Models that must be present before development can proceed.
# See docs/decisions/ADR-001-model-selection.md for rationale.
REQUIRED_MODELS = ["nomic-embed-text", "mistral"]
OLLAMA_BASE_URL = "http://localhost:11434"
MIN_PYTHON = (3, 11)
MIN_FREE_RAM_GB = 6.0


# ---------------------------------------------------------------------------
# Check helpers
# ---------------------------------------------------------------------------

def _ok(msg: str) -> None:
    print(f"  [ OK ] {msg}")


def _fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")


def _warn(msg: str) -> None:
    print(f"  [WARN] {msg}")


def _skip(msg: str) -> None:
    print(f"  [SKIP] {msg}")


def check_python_version() -> bool:
    version = sys.version_info[:2]
    if version >= MIN_PYTHON:
        _ok(f"Python {version[0]}.{version[1]}")
        return True
    _fail(
        f"Python {version[0]}.{version[1]} — required >= "
        f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}"
    )
    return False


def check_ollama_running() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=5) as resp:
            if resp.status == 200:
                _ok(f"Ollama daemon reachable at {OLLAMA_BASE_URL}")
                return True
    except (urllib.error.URLError, OSError):
        pass
    _fail(f"Ollama daemon not reachable at {OLLAMA_BASE_URL}")
    print("         → Start Ollama with: ollama serve")
    return False


def _fetch_available_models() -> list[str]:
    try:
        with urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=5) as resp:
            data = json.loads(resp.read())
        return [m["name"].split(":")[0] for m in data.get("models", [])]
    except Exception:
        return []


def check_required_models() -> bool:
    available = _fetch_available_models()
    all_present = True
    for model in REQUIRED_MODELS:
        if model in available:
            _ok(f"Model present: {model}")
        else:
            _fail(f"Model missing: {model}")
            print(f"         → Run: ollama pull {model}")
            all_present = False
    return all_present


def check_available_ram() -> None:
    try:
        import psutil  # optional; install with: pip install psutil
    except ImportError:
        _skip("RAM check skipped — psutil not installed (pip install psutil)")
        return

    mem = psutil.virtual_memory()
    available_gb = mem.available / (1024 ** 3)
    total_gb = mem.total / (1024 ** 3)

    if available_gb >= MIN_FREE_RAM_GB:
        _ok(f"RAM: {available_gb:.1f} GB free / {total_gb:.1f} GB total")
    else:
        _warn(
            f"RAM: only {available_gb:.1f} GB free / {total_gb:.1f} GB total "
            f"(recommended >= {MIN_FREE_RAM_GB} GB free)"
        )
        print("         → Close unused applications before running the full pipeline.")


def check_config_file() -> bool:
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    if config_path.exists():
        _ok(f"Config file found: {config_path.relative_to(config_path.parent.parent)}")
        return True
    _fail(f"Config file not found: config/settings.yaml")
    return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    print("\nKnowledge Onboarding Agent — Environment Validation")
    print("=" * 42)

    results: list[bool] = []

    print("\nPython:")
    results.append(check_python_version())

    print("\nConfig:")
    results.append(check_config_file())

    print("\nOllama:")
    ollama_ok = check_ollama_running()
    results.append(ollama_ok)

    if ollama_ok:
        print("\nModels:")
        results.append(check_required_models())
    else:
        print("\nModels: [SKIP] Ollama not running — cannot verify models")

    print("\nMemory:")
    check_available_ram()  # warnings only, does not affect exit code

    print()
    if all(results):
        print("All checks passed. Environment is ready.")
        return 0

    print("One or more checks failed. Resolve the issues above before proceeding.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
