"""
discovery.py — Unified Antigravity and Environment Discovery for Finest Computer Use.

Provides structured, single-source detection for:
  - Antigravity macOS application bundle (.app)
  - Antigravity command line interface (CLI)
  - Antigravity configuration directory (~/.gemini)
"""

import os
import shutil
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

@dataclass
class AntigravityDiscovery:
    app_found: bool
    app_path: Optional[str]
    app_valid: bool
    cli_found: bool
    cli_path: Optional[str]
    config_found: bool
    config_path: Optional[str]
    installed_confirmed: bool
    details: List[str]
    status_summary: str

def is_valid_app_bundle(app_path: str) -> bool:
    """
    Verify that an application bundle has the expected macOS structure with an executable binary.
    An empty directory or broken bundle without Contents/MacOS/<executable> is rejected.
    """
    if not (os.path.isdir(app_path) and app_path.endswith(".app")):
        return False
    macos_dir = os.path.join(app_path, "Contents", "MacOS")
    if not os.path.isdir(macos_dir):
        return False
    try:
        for entry in os.listdir(macos_dir):
            entry_path = os.path.join(macos_dir, entry)
            if os.path.isfile(entry_path) and os.access(entry_path, os.X_OK):
                return True
    except OSError:
        return False
    return False

def discover_antigravity(home_dir: Optional[str] = None, allow_simulated: bool = False) -> AntigravityDiscovery:
    """
    Perform unified Antigravity discovery across application bundles, CLI binaries, and config paths.

    CRITICAL RULE:
    The existence of ~/.gemini alone indicates configuration presence, NOT application installation.
    installed_confirmed is True if and only if a structurally valid .app bundle or CLI binary is found.
    """
    home = home_dir or os.path.expanduser("~")
    gemini_dir = os.path.join(home, ".gemini")
    config_found = os.path.exists(gemini_dir)
    config_path = gemini_dir if config_found else None

    is_isolated = (home != os.path.expanduser("~")) or (os.environ.get("FINEST_ISOLATE_APP_SEARCH") == "1")

    app_candidates = []
    if os.environ.get("ANTIGRAVITY_APP_PATH"):
        app_candidates.append(os.environ["ANTIGRAVITY_APP_PATH"])
    elif not is_isolated:
        app_candidates.append("/Applications/Antigravity.app")
    app_candidates.append(os.path.join(home, "Applications", "Antigravity.app"))

    found_app_path = None
    app_valid = False
    for p in app_candidates:
        if os.path.exists(p):
            found_app_path = p
            if is_valid_app_bundle(p):
                app_valid = True
                break

    cli_path = None
    if is_isolated:
        fixture_bin = os.path.join(home, "bin")
        for c in ["agy", "antigravity"]:
            p = os.path.join(fixture_bin, c)
            if os.path.exists(p) and os.access(p, os.X_OK):
                cli_path = p
                break
    else:
        cli_path = shutil.which("agy") or shutil.which("antigravity")

    app_found = found_app_path is not None
    cli_found = cli_path is not None
    installed_confirmed = app_valid or cli_found

    details = []
    if app_valid and found_app_path:
        details.append(f"Application bundle ({found_app_path})")
    elif app_found and found_app_path:
        details.append(f"Invalid app bundle ({found_app_path})")
    if cli_found and cli_path:
        details.append(f"CLI ({cli_path})")
    if config_found:
        details.append(f"Config dir ({gemini_dir})")

    if installed_confirmed:
        summary = f"Antigravity installation confirmed ({', '.join(details)})"
    elif config_found:
        if allow_simulated:
            installed_confirmed = True
            summary = "Antigravity configuration present (simulated in portable/dry-run mode)"
        else:
            summary = f"Config directory exists ({gemini_dir}), but Antigravity application or CLI is NOT confirmed"
    else:
        summary = "Antigravity not detected in /Applications, PATH, or ~/.gemini"

    return AntigravityDiscovery(
        app_found=app_found,
        app_path=found_app_path,
        app_valid=app_valid,
        cli_found=cli_found,
        cli_path=cli_path,
        config_found=config_found,
        config_path=config_path,
        installed_confirmed=installed_confirmed,
        details=details,
        status_summary=summary,
    )
