#!/usr/bin/env python3
"""
uninstall.py — Clean Uninstaller for Computer Use Safety.

Safely:
1. Removes managed policy block from ~/.gemini/GEMINI.md
2. Removes hooks entry from ~/.gemini/config/hooks.json
3. Removes installed scripts from ~/.gemini/config/skills/computer-use/scripts/
4. Preserves backups in ~/.gemini/backup/
"""

import sys
import os
import json
from typing import Optional

def uninstall(home_dir: Optional[str] = None):
    home = home_dir or os.environ.get("GEMINI_HOME") or os.path.expanduser("~")
    target_scripts_dir = os.path.join(home, ".gemini/config/skills/computer-use/scripts")
    target_skill_md = os.path.join(home, ".gemini/config/skills/computer-use/SKILL.md")
    target_gemini_md = os.path.join(home, ".gemini/GEMINI.md")
    target_hooks_json = os.path.join(home, ".gemini/config/hooks.json")

    print("========================================================")
    print("UNINSTALLING FINEST COMPUTER USE SAFETY")
    print("========================================================")

    # 1. Unregister hooks
    if os.path.exists(target_hooks_json):
        try:
            with open(target_hooks_json, "r", encoding="utf-8") as f:
                hooks_data = json.load(f)
            if "computer-use-safety" in hooks_data:
                del hooks_data["computer-use-safety"]
                with open(target_hooks_json, "w", encoding="utf-8") as f:
                    json.dump(hooks_data, f, indent=2)
                print(f"[OK] Unregistered computer-use-safety from {target_hooks_json}")
        except Exception as e:
            print(f"[WARN] Error updating hooks.json: {e}")

    # 2. Clean GEMINI.md managed block
    if os.path.exists(target_gemini_md):
        try:
            with open(target_gemini_md, "r", encoding="utf-8") as f:
                content = f.read()
            start_delim = "<!-- finest-computer-use:start -->"
            end_delim = "<!-- finest-computer-use:end -->"
            if start_delim in content and end_delim in content:
                p_start = content.index(start_delim)
                p_end = content.index(end_delim) + len(end_delim)
                clean_content = content[:p_start].rstrip() + "\n\n" + content[p_end:].lstrip()
                clean_content = clean_content.strip() + "\n"
                with open(target_gemini_md, "w", encoding="utf-8") as f:
                    f.write(clean_content)
                print(f"[OK] Removed managed safety block from {target_gemini_md}")
        except Exception as e:
            print(f"[WARN] Error cleaning GEMINI.md: {e}")

    # 3. Clean installed runtime files
    if os.path.exists(target_scripts_dir):
        modules = [
            "safe_interact.py", "effect_firewall.py", "effect_taxonomy.py",
            "deploy_firewall.py", "firewall_healthcheck.py", "run_firewall_regression.py"
        ]
        for mod in modules:
            fpath = os.path.join(target_scripts_dir, mod)
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                    print(f"[OK] Removed {fpath}")
                except Exception as e:
                    print(f"[WARN] Failed to remove {fpath}: {e}")

    print("========================================================")
    print("UNINSTALLATION COMPLETE (Backups preserved in ~/.gemini/backup/)")
    print("========================================================")

def main():
    home_arg = None
    for arg in sys.argv[1:]:
        if arg.startswith("--home="):
            home_arg = arg.split("=", 1)[1]
    uninstall(home_dir=home_arg)

if __name__ == "__main__":
    main()
