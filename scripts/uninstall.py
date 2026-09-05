#!/usr/bin/env python3
"""
uninstall.py — Clean Uninstaller for Computer Use Safety v1.

Safely:
1. Removes managed policy block from ~/.gemini/GEMINI.md
2. Removes hooks entry from ~/.gemini/config/hooks.json
3. Removes installed scripts from ~/.gemini/config/skills/computer-use/scripts/
4. Preserves backups in ~/.gemini/backup/
"""

import sys
import os
import json

TARGET_SCRIPTS_DIR = os.path.expanduser("~/.gemini/config/skills/computer-use/scripts")
TARGET_SKILL_MD = os.path.expanduser("~/.gemini/config/skills/computer-use/SKILL.md")
TARGET_GEMINI_MD = os.path.expanduser("~/.gemini/GEMINI.md")
TARGET_HOOKS_JSON = os.path.expanduser("~/.gemini/config/hooks.json")

def uninstall():
    print("========================================================")
    print("UNINSTALLING FINEST COMPUTER USE SAFETY v1")
    print("========================================================")

    # 1. Unregister hooks
    if os.path.exists(TARGET_HOOKS_JSON):
        try:
            with open(TARGET_HOOKS_JSON, "r", encoding="utf-8") as f:
                hooks_data = json.load(f)
            if "computer-use-safety" in hooks_data:
                del hooks_data["computer-use-safety"]
                with open(TARGET_HOOKS_JSON, "w", encoding="utf-8") as f:
                    json.dump(hooks_data, f, indent=2)
                print(f"[OK] Unregistered computer-use-safety from {TARGET_HOOKS_JSON}")
        except Exception as e:
            print(f"[WARN] Error updating hooks.json: {e}")

    # 2. Clean GEMINI.md managed block
    if os.path.exists(TARGET_GEMINI_MD):
        try:
            with open(TARGET_GEMINI_MD, "r", encoding="utf-8") as f:
                content = f.read()
            start_delim = "<!-- finest-computer-use:start -->"
            end_delim = "<!-- finest-computer-use:end -->"
            if start_delim in content and end_delim in content:
                p_start = content.index(start_delim)
                p_end = content.index(end_delim) + len(end_delim)
                clean_content = content[:p_start].rstrip() + "\n\n" + content[p_end:].lstrip()
                clean_content = clean_content.strip() + "\n"
                with open(TARGET_GEMINI_MD, "w", encoding="utf-8") as f:
                    f.write(clean_content)
                print(f"[OK] Removed managed safety block from {TARGET_GEMINI_MD}")
        except Exception as e:
            print(f"[WARN] Error cleaning GEMINI.md: {e}")

    # 3. Clean installed runtime files
    if os.path.exists(TARGET_SCRIPTS_DIR):
        modules = [
            "safe_interact.py", "effect_firewall.py", "effect_taxonomy.py",
            "deploy_firewall.py", "firewall_healthcheck.py", "run_firewall_regression.py"
        ]
        for mod in modules:
            fpath = os.path.join(TARGET_SCRIPTS_DIR, mod)
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                    print(f"[OK] Removed {fpath}")
                except Exception as e:
                    print(f"[WARN] Failed to remove {fpath}: {e}")

    print("========================================================")
    print("UNINSTALLATION COMPLETE (Backups preserved in ~/.gemini/backup/)")
    print("========================================================")

if __name__ == "__main__":
    uninstall()
