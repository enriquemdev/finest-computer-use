#!/usr/bin/env python3
"""
fresh_mac_acceptance.py — Automated Verification & Acceptance Audit for Clean / Target Macs.

Collects non-sensitive system evidence and runs non-mutating readiness checks:
  1. Operating System & Hardware (macOS version, arm64/x86_64)
  2. Antigravity Installation
  3. Peekaboo Installation & TCC Permissions
  4. MCP Configuration Integrity
  5. Safety Layer Runtime & Policy Block
  6. Standalone Firewall Healthcheck (30 checks)
  7. Runtime Smoke Test (Fast-path + Coordinate click block)

Emits a structured acceptance report for validation records.
"""

import sys
import os
import json
import platform
import subprocess
import shutil
from typing import Dict, Any

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS_DIR = os.path.join(REPO_DIR, "scripts")

# Confidence Levels for Evidence Categorization
CONFIDENCE_LEVELS = {
    "PORTABLE": "Deterministic logic / syntax / unit validation running across any OS",
    "HOST_INTEGRATION": "Non-invasive probes executed against the live host environment",
    "FIXTURE": "End-to-end installation / configuration tested inside isolated temporary directory fixtures",
    "ANTIGRAVITY_E2E": "Real tool dispatch mediated by host Antigravity PreToolUse hook lifecycle",
    "TRUE_CLEAN_MAC_E2E": "Complete execution from scratch on an unconfigured physical Mac without existing dev tools"
}

def run_acceptance() -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "mac_ver": platform.mac_ver()[0] if platform.system() == "Darwin" else "N/A",
            "arch": platform.machine(),
            "python": sys.version.split()[0]
        },
        "confidence_levels": CONFIDENCE_LEVELS,
        "checks": {},
        "e2e_status": {
            "antigravity_hook_dispatch": "NOT EXECUTED (Standalone script cannot simulate host Antigravity tool-dispatch hook lifecycle)",
            "true_clean_mac_e2e": "NOT EXECUTED (Requires physical unconfigured machine without existing development environment)"
        }
    }

    print("=================================================================")
    print("      FINEST COMPUTER USE — TARGET MAC ACCEPTANCE AUDIT          ")
    print("=================================================================")

    # 1. Platform
    is_supported_mac = False
    if platform.system() == "Darwin":
        try:
            major = int(platform.mac_ver()[0].split(".")[0])
            is_supported_mac = major >= 15
        except Exception:
            pass
    report["checks"]["macos_15_plus"] = is_supported_mac
    print(f"1. macOS Platform (>= 15.0) [HOST_INTEGRATION]: {'PASS' if is_supported_mac else 'FAIL'} ({report['platform']['mac_ver']})")

    # 2. Antigravity
    gemini_home = os.path.expanduser("~/.gemini")
    app_candidates = [
        "/Applications/Antigravity.app",
        os.path.expanduser("~/Applications/Antigravity.app")
    ]
    app_found = any(os.path.isdir(p) and os.path.exists(os.path.join(p, "Contents", "MacOS")) for p in app_candidates)
    cli_found = shutil.which("agy") is not None or shutil.which("antigravity") is not None
    agy_confirmed = app_found or cli_found
    report["checks"]["antigravity_detected"] = agy_confirmed
    print(f"2. Antigravity Installation [HOST_INTEGRATION]: {'PASS' if agy_confirmed else 'ACTION REQUIRED'}")

    # 3. Peekaboo & TCC
    peekaboo_bin = shutil.which("peekaboo") or "/opt/homebrew/bin/peekaboo"
    peekaboo_installed = os.path.exists(peekaboo_bin) and os.access(peekaboo_bin, os.X_OK)
    tcc_ok = False
    mcp_mode_ok = False
    if peekaboo_installed:
        try:
            res_mcp = subprocess.run([peekaboo_bin, "mcp", "--help"], capture_output=True, text=True, timeout=5)
            mcp_mode_ok = res_mcp.returncode == 0
            res = subprocess.run([peekaboo_bin, "permissions", "--json"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                perms = json.loads(res.stdout).get("data", {}).get("permissions", [])
                missing = [p for p in perms if p.get("isRequired") and not p.get("isGranted")]
                tcc_ok = len(missing) == 0
        except Exception:
            pass

    report["checks"]["peekaboo_installed"] = peekaboo_installed
    report["checks"]["peekaboo_mcp_support"] = mcp_mode_ok
    report["checks"]["tcc_permissions_granted"] = tcc_ok
    print(f"3. Peekaboo Binary & MCP Mode [HOST_INTEGRATION]: {'PASS' if (peekaboo_installed and mcp_mode_ok) else 'ACTION REQUIRED'} ({peekaboo_bin})")
    print(f"4. macOS TCC Permissions [HOST_INTEGRATION]: {'PASS' if tcc_ok else 'ACTION REQUIRED'}")

    # 4. MCP Configuration
    mcp_file = os.path.expanduser("~/.gemini/config/mcp_config.json")
    mcp_has_peekaboo = False
    if os.path.exists(mcp_file):
        try:
            with open(mcp_file, "r") as f:
                mdata = json.load(f)
            mcp_has_peekaboo = "peekaboo" in mdata.get("mcpServers", {})
        except Exception:
            pass
    report["checks"]["mcp_configured"] = mcp_has_peekaboo
    print(f"5. Peekaboo MCP Registered [HOST_INTEGRATION]: {'PASS' if mcp_has_peekaboo else 'ACTION REQUIRED'}")

    # 5. Safety Layer Runtime
    runtime_script = os.path.expanduser("~/.gemini/config/skills/computer-use/scripts/safe_interact.py")
    runtime_installed = os.path.exists(runtime_script)
    report["checks"]["safety_runtime_installed"] = runtime_installed
    print(f"6. Safety Runtime Files [HOST_INTEGRATION]: {'PASS' if runtime_installed else 'ACTION REQUIRED'}")

    # 6. Firewall Healthcheck
    hc_ok = False
    hc_script = os.path.join(SCRIPTS_DIR, "firewall_healthcheck.py")
    if os.path.exists(hc_script):
        res_hc = subprocess.run([sys.executable, hc_script], capture_output=True, text=True)
        hc_ok = res_hc.returncode == 0
    report["checks"]["firewall_healthcheck_30_pass"] = hc_ok
    print(f"7. Firewall Healthcheck (30/30) [PORTABLE]: {'PASS' if hc_ok else 'FAIL'}")

    # 7. Smoke Test
    smoke_ok = False
    smoke_script = os.path.join(SCRIPTS_DIR, "smoke_test.py")
    if os.path.exists(smoke_script):
        res_smoke = subprocess.run([sys.executable, smoke_script], capture_output=True, text=True)
        smoke_ok = res_smoke.returncode == 0
    report["checks"]["runtime_smoke_test"] = smoke_ok
    print(f"8. Runtime Smoke Test [HOST_INTEGRATION]: {'PASS' if smoke_ok else 'FAIL'}")

    # 8. Explicit Non-Claims
    print("\n9. Antigravity Tool Hook Dispatch [ANTIGRAVITY_E2E]:")
    print("   STATUS: NOT EXECUTED (Requires running within active Antigravity session)")
    print("10. Clean Mac E2E Acceptance [TRUE_CLEAN_MAC_E2E]:")
    print("   STATUS: TRUE CLEAN MAC E2E: NOT EXECUTED (Verified via isolated fixtures)")

    all_passed = all(report["checks"].values())
    report["all_passed"] = all_passed
    print("-----------------------------------------------------------------")
    verdict = "PASS (READY WITH DOCUMENTED MANUAL STEPS)" if all_passed else "ACTION REQUIRED (Complete prerequisites above)"
    print(f"  TARGET MAC ACCEPTANCE VERDICT: {verdict}")
    print("=================================================================")
    return report

def main():
    json_mode = "--json" in sys.argv
    rep = run_acceptance()
    if json_mode:
        print(json.dumps(rep, indent=2))
    sys.exit(0 if rep["all_passed"] else 1)

if __name__ == "__main__":
    main()
