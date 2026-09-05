#!/usr/bin/env python3
"""
backup_current.py — Create timestamped backup of active Computer Use Safety installation.
"""

import sys
import os
import shutil
import time
import json
from typing import Dict, Any, Optional

def create_backup(home_dir: Optional[str] = None) -> Dict[str, Any]:
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    home = home_dir or os.environ.get("GEMINI_HOME") or os.path.expanduser("~")
    base_dir = os.path.join(home, ".gemini", "backup")
    backup_dir = os.path.join(base_dir, f"computer-use-safety-{timestamp}")
    os.makedirs(backup_dir, exist_ok=True)

    items_to_backup = [
        ("gemini_md", os.path.join(home, ".gemini", "GEMINI.md")),
        ("hooks_json", os.path.join(home, ".gemini", "config", "hooks.json")),
        ("skill_dir", os.path.join(home, ".gemini", "config", "skills", "computer-use")),
        ("mcp_config", os.path.join(home, ".gemini", "config", "mcp_config.json"))
    ]

    backed_up = {}
    for key, path in items_to_backup:
        if os.path.exists(path):
            target_name = os.path.basename(path)
            dest = os.path.join(backup_dir, target_name)
            if os.path.isdir(path):
                shutil.copytree(path, dest)
            else:
                shutil.copy2(path, dest)
            backed_up[key] = {
                "source": path,
                "backup": dest,
                "type": "directory" if os.path.isdir(path) else "file"
            }

    meta = {
        "timestamp": timestamp,
        "backup_dir": backup_dir,
        "backed_up_items": backed_up,
        "status": "success"
    }

    meta_file = os.path.join(backup_dir, "backup_manifest.json")
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return meta

def main():
    home_arg = None
    for arg in sys.argv[1:]:
        if arg.startswith("--home="):
            home_arg = arg.split("=", 1)[1]
    res = create_backup(home_dir=home_arg)
    print(f"[OK] Computer Use Safety backup created at: {res['backup_dir']}")
    print(f"     Backed up items: {list(res['backed_up_items'].keys())}")
    sys.exit(0)

if __name__ == "__main__":
    main()
