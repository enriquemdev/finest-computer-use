#!/usr/bin/env python3
"""
deploy_firewall.py — Safe Deployment and Atomic Rollback Manager for Firewall Modules.

Enforces strict safety workflow:
WRITE STAGING -> PY_COMPILE -> ISOLATED IMPORT TEST -> BACKUP LKG -> ATOMIC REPLACE -> HEALTH CHECK -> CONFIRM
Rolls back immediately to .last_known_good if any step fails.
"""

import sys
import os
import shutil
import tempfile
import py_compile
import subprocess
from typing import Optional, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_default_target_dir() -> str:
    """Return runtime installation directory in ~/.gemini."""
    return os.path.expanduser("~/.gemini/config/skills/computer-use/scripts")

def deploy_module(
    module_filename: str,
    new_content: str,
    target_dir: Optional[str] = None,
    run_healthcheck: bool = True
) -> Tuple[bool, str]:
    """
    Safely deploy a new version of a firewall module.
    Returns (success, message).
    """
    dest_dir = target_dir or get_default_target_dir()
    os.makedirs(dest_dir, exist_ok=True)

    target_path = os.path.join(dest_dir, module_filename)
    lkg_path = target_path + ".last_known_good"
    module_name = os.path.splitext(module_filename)[0]

    # Step 1: Create isolated staging directory and write content
    staging_dir = tempfile.mkdtemp(prefix="fw_stage_")
    staging_file = os.path.join(staging_dir, module_filename)
    
    try:
        with open(staging_file, "w", encoding="utf-8") as f:
            f.write(new_content)

        # Step 2: py_compile syntax verification
        try:
            py_compile.compile(staging_file, doraise=True)
        except py_compile.PyCompileError as pe:
            return False, f"STAGING FAILED: Syntax / Indentation Error during py_compile: {pe}"

        # Step 3: Isolated subprocess import verification
        test_code = (
            f"import sys; sys.path.insert(0, '{staging_dir}'); "
            f"sys.path.insert(1, '{dest_dir}'); "
            f"import {module_name}; print('IMPORT_OK')"
        )
        res = subprocess.run(
            [sys.executable, "-c", test_code],
            capture_output=True,
            text=True,
            timeout=5
        )
        if res.returncode != 0 or "IMPORT_OK" not in res.stdout:
            return False, f"STAGING FAILED: Module import test failed: {res.stderr.strip() or res.stdout.strip()}"

        # Step 4: Backup current target to .last_known_good
        if os.path.exists(target_path):
            try:
                shutil.copy2(target_path, lkg_path)
            except Exception as e:
                return False, f"DEPLOYMENT ABORTED: Failed to create last_known_good backup: {e}"

        # Step 5: Atomic replacement using tempfile on same filesystem
        temp_dest = os.path.join(dest_dir, f".deploy_{module_filename}.tmp")
        shutil.copy2(staging_file, temp_dest)
        os.replace(temp_dest, target_path)

        # Step 6: Run health check if requested
        if run_healthcheck:
            healthcheck_candidates = [
                os.path.join(dest_dir, "firewall_healthcheck.py"),
                os.path.join(SCRIPT_DIR, "firewall_healthcheck.py")
            ]
            healthcheck_path = next((p for p in healthcheck_candidates if os.path.exists(p)), None)
            if healthcheck_path:
                hc_res = subprocess.run(
                    [sys.executable, healthcheck_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if hc_res.returncode != 0:
                    rollback_ok, rb_msg = rollback_module(module_filename, dest_dir)
                    return False, f"HEALTHCHECK FAILED after replace (Rollback: {rb_msg}): {hc_res.stderr.strip() or hc_res.stdout.strip()}"

        return True, f"SUCCESS: Deployed {module_filename} safely with atomic replace and backup."

    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

def rollback_module(module_filename: str, target_dir: Optional[str] = None) -> Tuple[bool, str]:
    """Roll back module from .last_known_good."""
    dest_dir = target_dir or get_default_target_dir()
    target_path = os.path.join(dest_dir, module_filename)
    lkg_path = target_path + ".last_known_good"

    if not os.path.exists(lkg_path):
        return False, f"No last_known_good backup found for {module_filename} at {lkg_path}"

    try:
        temp_dest = os.path.join(dest_dir, f".rollback_{module_filename}.tmp")
        shutil.copy2(lkg_path, temp_dest)
        os.replace(temp_dest, target_path)
        return True, f"Restored {module_filename} from {lkg_path}"
    except Exception as e:
        return False, f"Failed to rollback {module_filename}: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: deploy_firewall.py <deploy|rollback> <module_filename> [source_file] [target_dir]")
        sys.exit(1)

    cmd = sys.argv[1]
    mod_file = sys.argv[2] if len(sys.argv) > 2 else ""

    if cmd == "rollback":
        tgt_dir = sys.argv[3] if len(sys.argv) > 3 else None
        ok, msg = rollback_module(mod_file, tgt_dir)
        print(msg)
        sys.exit(0 if ok else 1)
    elif cmd == "deploy":
        if len(sys.argv) < 4:
            print("Usage: deploy_firewall.py deploy <module_filename> <source_file> [target_dir]")
            sys.exit(1)
        src_file = sys.argv[3]
        tgt_dir = sys.argv[4] if len(sys.argv) > 4 else None
        with open(src_file, "r", encoding="utf-8") as f:
            content = f.read()
        ok, msg = deploy_module(mod_file, content, target_dir=tgt_dir, run_healthcheck=False)
        print(msg)
        sys.exit(0 if ok else 1)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
