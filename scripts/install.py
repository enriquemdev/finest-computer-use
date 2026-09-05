#!/usr/bin/env python3
"""
install.py — Safe, Idempotent Installer for Computer Use Safety.

Steps:
1. Back up existing configuration to ~/.gemini/backup/
2. Stage and compile Python runtime modules (py_compile)
3. Deploy runtime files to ~/.gemini/config/skills/computer-use/scripts/
4. Deploy SKILL.md to ~/.gemini/config/skills/computer-use/SKILL.md
5. Idempotently merge managed policy block into ~/.gemini/GEMINI.md
6. Idempotently register PreToolUse & PostToolUse hooks in ~/.gemini/config/hooks.json
7. Run firewall_healthcheck.py on installed system
8. If healthcheck fails, automatically roll back to backup
"""

import sys
import os
import json
import shutil
import subprocess
import py_compile
from typing import Optional

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_DIR, "src", "finest_computer_use")
POLICY_DIR = os.path.join(REPO_DIR, "policy")
SCRIPTS_DIR = os.path.join(REPO_DIR, "scripts")

def run_backup(home_dir: Optional[str] = None) -> Optional[str]:
    backup_script = os.path.join(SCRIPTS_DIR, "backup_current.py")
    if os.path.exists(backup_script):
        cmd = [sys.executable, backup_script]
        if home_dir:
            cmd.append(f"--home={home_dir}")
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if "created at:" in line.lower():
                    return line.split(":", 1)[1].strip()
    return None

def rollback_from_backup(backup_dir: str):
    print(f"[ROLLBACK] Restoring previous configuration from {backup_dir}...")
    manifest_path = os.path.join(backup_dir, "backup_manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        for item in manifest.get("backed_up_items", {}).values():
            src = item["backup"]
            dst = item["source"]
            if os.path.exists(src):
                if item["type"] == "directory":
                    shutil.rmtree(dst, ignore_errors=True)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
                print(f"  Restored {dst}")
    print("[ROLLBACK] Restoration complete.")

def install(home_dir: Optional[str] = None) -> int:
    home = home_dir or os.environ.get("GEMINI_HOME") or os.path.expanduser("~")
    target_scripts_dir = os.path.join(home, ".gemini/config/skills/computer-use/scripts")
    target_skill_md = os.path.join(home, ".gemini/config/skills/computer-use/SKILL.md")
    target_gemini_md = os.path.join(home, ".gemini/GEMINI.md")
    target_hooks_json = os.path.join(home, ".gemini/config/hooks.json")

    print("========================================================")
    print("INSTALLING FINEST COMPUTER USE SAFETY")
    print("========================================================")

    # 1. Backup
    print("\n1. Backing up existing installation...")
    backup_dir = run_backup(home_dir=home)
    if backup_dir:
        print(f"   Backup created at {backup_dir}")
    else:
        print("   Notice: No preexisting configuration to backup.")

    try:
        # 2. Compile & verify source files
        print("\n2. Staging and verifying Python modules...")
        modules = ["safe_interact.py", "effect_firewall.py", "effect_taxonomy.py"]
        for mod in modules:
            src_file = os.path.join(SRC_DIR, mod)
            if not os.path.exists(src_file):
                raise RuntimeError(f"Missing required source file: {src_file}")
            py_compile.compile(src_file, doraise=True)
            print(f"   Compiled: {mod}")

        # 3. Deploy scripts
        print("\n3. Deploying runtime modules...")
        os.makedirs(target_scripts_dir, exist_ok=True)
        for mod in modules:
            shutil.copy2(os.path.join(SRC_DIR, mod), os.path.join(target_scripts_dir, mod))
            print(f"   Installed {mod} -> {target_scripts_dir}")

        for util in ["deploy_firewall.py", "firewall_healthcheck.py"]:
            src_util = os.path.join(SCRIPTS_DIR, util)
            if os.path.exists(src_util):
                shutil.copy2(src_util, os.path.join(target_scripts_dir, util))
                print(f"   Installed {util} -> {target_scripts_dir}")

        # 4. Deploy SKILL.md
        print("\n4. Deploying SKILL.md...")
        skill_src = os.path.join(POLICY_DIR, "SKILL.md")
        if os.path.exists(skill_src):
            os.makedirs(os.path.dirname(target_skill_md), exist_ok=True)
            shutil.copy2(skill_src, target_skill_md)
            print(f"   Installed SKILL.md -> {target_skill_md}")

        # 5. Merge GEMINI.md policy block
        print("\n5. Merging policy into GEMINI.md...")
        policy_gemini_src = os.path.join(POLICY_DIR, "GEMINI.md")
        if os.path.exists(policy_gemini_src):
            with open(policy_gemini_src, "r", encoding="utf-8") as f:
                policy_text = f.read()

            start_delim = "<!-- finest-computer-use:start -->"
            end_delim = "<!-- finest-computer-use:end -->"

            if start_delim in policy_text and end_delim in policy_text:
                policy_block = policy_text[policy_text.index(start_delim):policy_text.index(end_delim) + len(end_delim)]
            else:
                policy_block = f"{start_delim}\n{policy_text.strip()}\n{end_delim}"

            existing_text = ""
            if os.path.exists(target_gemini_md):
                with open(target_gemini_md, "r", encoding="utf-8") as f:
                    existing_text = f.read()

            if start_delim in existing_text and end_delim in existing_text:
                p_start = existing_text.index(start_delim)
                p_end = existing_text.index(end_delim) + len(end_delim)
                new_text = existing_text[:p_start] + policy_block + existing_text[p_end:]
            else:
                new_text = (existing_text.rstrip() + "\n\n" + policy_block + "\n").lstrip()

            os.makedirs(os.path.dirname(target_gemini_md), exist_ok=True)
            with open(target_gemini_md, "w", encoding="utf-8") as f:
                f.write(new_text)
            print(f"   Updated {target_gemini_md} with managed safety policy block.")

        # 6. Configure hooks.json
        print("\n6. Configuring hooks.json...")
        os.makedirs(os.path.dirname(target_hooks_json), exist_ok=True)
        hooks_data = {}
        if os.path.exists(target_hooks_json):
            try:
                with open(target_hooks_json, "r", encoding="utf-8") as f:
                    hooks_data = json.load(f)
            except Exception:
                hooks_data = {}

        installed_safe_interact = os.path.join(target_scripts_dir, "safe_interact.py")
        hooks_data["computer-use-safety"] = {
            "enabled": True,
            "PreToolUse": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"python3 {installed_safe_interact}"
                        }
                    ]
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"python3 {installed_safe_interact} post"
                        }
                    ]
                }
            ]
        }

        with open(target_hooks_json, "w", encoding="utf-8") as f:
            json.dump(hooks_data, f, indent=2)
        print(f"   Registered PreToolUse & PostToolUse in {target_hooks_json}")

        # 7. Health Check Verification
        print("\n7. Running healthcheck verification on installed runtime...")
        hc_script = os.path.join(target_scripts_dir, "firewall_healthcheck.py")
        hc_cmd = [sys.executable, hc_script, f"--home={home}"]
        env_hc = os.environ.copy()
        env_hc["GEMINI_HOME"] = home
        res = subprocess.run(hc_cmd, env=env_hc, capture_output=True, text=True)
        print(res.stdout)
        if res.returncode != 0:
            print(res.stderr)
            raise RuntimeError(f"Installed health check failed with exit code {res.returncode}")

        print("========================================================")
        print("INSTALLATION COMPLETE AND FULLY VERIFIED")
        print("========================================================")
        return 0

    except Exception as e:
        print(f"\n[ERROR] Installation failed: {e}")
        if backup_dir:
            rollback_from_backup(backup_dir)
        return 1

def main():
    home_arg = None
    for arg in sys.argv[1:]:
        if arg.startswith("--home="):
            home_arg = arg.split("=", 1)[1]
    code = install(home_dir=home_arg)
    sys.exit(code)

if __name__ == "__main__":
    main()
