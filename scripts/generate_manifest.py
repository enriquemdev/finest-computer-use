#!/usr/bin/env python3
"""
generate_manifest.py — Deterministic Manifest & Checksum Tool for Finest Computer Use.

Capabilities:
  1. Generates MANIFEST.json and checksums.sha256 deterministically.
  2. Verifies existing MANIFEST.json and checksums.sha256 (--verify).
  3. Validates cross-file version consistency (--check-version).
"""

import sys
import os
import json
import hashlib
import re
from typing import Dict, List, Tuple

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXCLUDE_DIRS = {'.git', '__pycache__', '.pytest_cache', 'build', 'dist', '.egg-info'}
EXCLUDE_FILES = {'checksums.sha256', 'MANIFEST.json'}

def get_tracked_files(repo_dir: str) -> List[str]:
    files_to_hash = []
    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith('.git')]
        for f in files:
            if f in EXCLUDE_FILES or f.endswith('.pyc') or f.startswith('.'):
                continue
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, repo_dir)
            if not rel_path.startswith('.git'):
                files_to_hash.append(rel_path)
    files_to_hash.sort()
    return files_to_hash

def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, 'rb') as fp:
        while chunk := fp.read(65536):
            h.update(chunk)
    return h.hexdigest()

def get_version(repo_dir: str) -> str:
    version_file = os.path.join(repo_dir, "VERSION")
    with open(version_file, "r", encoding="utf-8") as f:
        return f.read().strip()

def check_version_consistency(repo_dir: str) -> Tuple[bool, List[str]]:
    errors = []
    ver = get_version(repo_dir)

    # 1. pyproject.toml
    pyproject_path = os.path.join(repo_dir, "pyproject.toml")
    if os.path.exists(pyproject_path):
        with open(pyproject_path, "r", encoding="utf-8") as f:
            content = f.read()
        m = re.search(r'version\s*=\s*"([^"]+)"', content)
        if not m or m.group(1) != ver:
            errors.append(f"pyproject.toml version ({m.group(1) if m else 'missing'}) != VERSION ({ver})")

    # 2. MANIFEST.json (if exists)
    manifest_path = os.path.join(repo_dir, "MANIFEST.json")
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("version") != ver:
                errors.append(f"MANIFEST.json version ({data.get('version')}) != VERSION ({ver})")
        except Exception as e:
            errors.append(f"Could not parse MANIFEST.json: {e}")

    # 3. README.md badge & title
    readme_path = os.path.join(repo_dir, "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            r_content = f.read()
        m_title = re.search(r'#\s+Finest Computer Use Safety\s+\(v([0-9\.]+)\)', r_content)
        if not m_title or m_title.group(1) != ver:
            errors.append(f"README.md title version ({m_title.group(1) if m_title else 'missing'}) != VERSION ({ver})")
        m_badge = re.search(r'badge/version-([0-9\.]+)-blue', r_content)
        if not m_badge or m_badge.group(1) != ver:
            errors.append(f"README.md badge version ({m_badge.group(1) if m_badge else 'missing'}) != VERSION ({ver})")

    # 4. CHANGELOG.md (should have entry for ver)
    changelog_path = os.path.join(repo_dir, "CHANGELOG.md")
    if os.path.exists(changelog_path):
        with open(changelog_path, "r", encoding="utf-8") as f:
            c_content = f.read()
        if f"## [{ver}]" not in c_content:
            errors.append(f"CHANGELOG.md lacks entry header '## [{ver}]'")

    return len(errors) == 0, errors

def generate(repo_dir: str):
    ver = get_version(repo_dir)
    files = get_tracked_files(repo_dir)

    manifest_files = {}
    checksum_lines = []

    for rel in files:
        full = os.path.join(repo_dir, rel)
        sha = compute_sha256(full)
        manifest_files[rel] = sha
        checksum_lines.append(f"{sha}  {rel}")

    # Write checksums.sha256
    with open(os.path.join(repo_dir, "checksums.sha256"), "w", encoding="utf-8") as f:
        f.write("\n".join(checksum_lines) + "\n")

    # Write MANIFEST.json
    manifest_data = {
        "name": "finest-computer-use",
        "version": ver,
        "description": "macOS Computer Use Safety Architecture Freeze & Clean Onboarding",
        "files": manifest_files
    }
    with open(os.path.join(repo_dir, "MANIFEST.json"), "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    print(f"Generated checksums.sha256 and MANIFEST.json for {len(files)} files (v{ver}).")

def verify(repo_dir: str) -> bool:
    manifest_path = os.path.join(repo_dir, "MANIFEST.json")
    if not os.path.exists(manifest_path):
        print("ERROR: MANIFEST.json does not exist.")
        return False

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    declared_files = manifest_data.get("files", {})
    all_ok = True
    mismatches = 0

    for rel, declared_hash in declared_files.items():
        full = os.path.join(repo_dir, rel)
        if not os.path.exists(full):
            print(f"  [MISSING] {rel}")
            all_ok = False
            mismatches += 1
            continue
        actual_hash = compute_sha256(full)
        if actual_hash != declared_hash:
            print(f"  [MISMATCH] {rel}: declared {declared_hash[:8]}... != actual {actual_hash[:8]}...")
            all_ok = False
            mismatches += 1

    if all_ok:
        print(f"MANIFEST VERIFICATION PASSED: All {len(declared_files)} files match cryptographic hashes.")
    else:
        print(f"MANIFEST VERIFICATION FAILED: {mismatches} issues found.")
    return all_ok

def main():
    if "--check-version" in sys.argv:
        ok, errors = check_version_consistency(REPO_DIR)
        if ok:
            print(f"VERSION CONSISTENCY CHECK PASSED (v{get_version(REPO_DIR)}).")
            sys.exit(0)
        else:
            print("VERSION CONSISTENCY CHECK FAILED:")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)

    if "--verify" in sys.argv:
        ok = verify(REPO_DIR)
        sys.exit(0 if ok else 1)

    generate(REPO_DIR)
    ok, errors = check_version_consistency(REPO_DIR)
    if not ok:
        print("WARNING: Version inconsistencies detected during manifest generation:")
        for e in errors:
            print(f"  - {e}")

if __name__ == "__main__":
    main()
