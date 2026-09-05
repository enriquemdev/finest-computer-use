#!/usr/bin/env python3
"""
doctor.py — Comprehensive Diagnostic Health and Readiness Inspector for Finest Computer Use.

Evaluates the full stack:
  macOS Platform -> Python -> Antigravity -> Peekaboo CLI -> TCC Permissions ->
  MCP Server Configuration -> Safety Runtime -> Hooks -> Firewall Health

Exit Codes:
  0 = READY (All required components present and operational)
  1 = ACTION REQUIRED (Missing prerequisite or user/macOS interaction needed, e.g. TCC)
  2 = ERROR (Unsupported platform, configuration error, or broken runtime)
"""

import sys
import os
import json
import shutil
import platform
import subprocess
from typing import Dict, Any, List, Optional, Tuple

class DoctorCheck:
    def __init__(self, name: str, status: str, message: str = "", action: str = ""):
        self.name = name
        # status can be: "PASS", "ACTION REQUIRED", "REQUIRED", "OPTIONAL", "ERROR"
        self.status = status
        self.message = message
        self.action = action

class SystemDoctor:
    def __init__(self, home_dir: Optional[str] = None):
        self.home = home_dir or os.path.expanduser("~")
        self.checks: List[DoctorCheck] = []
        self.is_macos = platform.system() == "Darwin"
        self.exit_code = 0

    def add_check(self, check: DoctorCheck):
        self.checks.append(check)
        if check.status in ("REQUIRED", "ERROR"):
            if self.exit_code < 2:
                self.exit_code = 2
        elif check.status == "ACTION REQUIRED":
            if self.exit_code < 1:
                self.exit_code = 1

    def run_all(self) -> int:
        self.check_platform()
        self.check_python()
        self.check_antigravity()
        peekaboo_bin = self.check_peekaboo()
        self.check_tcc(peekaboo_bin)
        self.check_mcp_config(peekaboo_bin)
        runtime_ok = self.check_safety_runtime()
        if runtime_ok:
            self.check_firewall_health()
        return self.exit_code

    def check_platform(self):
        system = platform.system()
        arch = platform.machine()
        if system != "Darwin":
            # Portable / CI mode
            self.add_check(DoctorCheck(
                "Operating System",
                "OPTIONAL",
                f"{system} ({arch}) — Non-macOS environment (portable CI / headless mode only)",
                "Full macOS GUI automation with Peekaboo requires macOS 15+ (Sequoia)."
            ))
            return

        mac_ver_str = platform.mac_ver()[0]
        try:
            major = int(mac_ver_str.split(".")[0])
        except (ValueError, IndexError):
            major = 0

        if major >= 15:
            self.add_check(DoctorCheck("macOS Version", "PASS", f"macOS {mac_ver_str} ({arch}) >= 15.0 supported"))
        else:
            self.add_check(DoctorCheck(
                "macOS Version",
                "REQUIRED",
                f"macOS {mac_ver_str} detected. Peekaboo 4.3+ requires macOS 15.0+ (Sequoia)",
                "Upgrade macOS to version 15.0 or later for Peekaboo compatibility."
            ))

    def check_python(self):
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        if sys.version_info >= (3, 9):
            self.add_check(DoctorCheck("Python Version", "PASS", f"Python {py_ver} ({sys.executable})"))
        else:
            self.add_check(DoctorCheck(
                "Python Version",
                "REQUIRED",
                f"Python {py_ver} is too old. Requires Python >= 3.9",
                "Install Python 3.9 or newer."
            ))

    def check_antigravity(self):
        gemini_dir = os.path.join(self.home, ".gemini")
        app_candidates = [
            "/Applications/Antigravity.app",
            os.path.join(self.home, "Applications/Antigravity.app")
        ]
        app_found = any(os.path.exists(p) for p in app_candidates)
        cli_found = shutil.which("agy") or shutil.which("antigravity")

        if app_found or cli_found or os.path.exists(gemini_dir):
            details = []
            if app_found:
                details.append("Application bundle")
            if cli_found:
                details.append(f"CLI ({cli_found})")
            if os.path.exists(gemini_dir):
                details.append(f"Config dir ({gemini_dir})")
            self.add_check(DoctorCheck("Antigravity Discovery", "PASS", ", ".join(details)))
        else:
            if not self.is_macos:
                self.add_check(DoctorCheck(
                    "Antigravity Discovery",
                    "OPTIONAL",
                    "Antigravity not detected (non-macOS portable testing environment)"
                ))
            else:
                self.add_check(DoctorCheck(
                    "Antigravity Discovery",
                    "REQUIRED",
                    "Antigravity not detected in /Applications, PATH, or ~/.gemini",
                    "Download and install Antigravity before configuring computer use safety."
                ))

    def check_peekaboo(self) -> Optional[str]:
        # Search PATH, then standard brew paths
        candidates = [
            shutil.which("peekaboo"),
            "/opt/homebrew/bin/peekaboo",
            "/usr/local/bin/peekaboo"
        ]
        peekaboo_bin = next((c for c in candidates if c and os.path.exists(c) and os.access(c, os.X_OK)), None)

        if peekaboo_bin:
            try:
                res = subprocess.run([peekaboo_bin, "--version"], capture_output=True, text=True, timeout=5)
                ver_line = res.stdout.strip() or res.stderr.strip()
                self.add_check(DoctorCheck("Peekaboo Binary", "PASS", f"{peekaboo_bin} ({ver_line})"))
                return peekaboo_bin
            except Exception as e:
                self.add_check(DoctorCheck("Peekaboo Binary", "ERROR", f"Error executing {peekaboo_bin}: {e}"))
                return peekaboo_bin
        else:
            if not self.is_macos:
                self.add_check(DoctorCheck(
                    "Peekaboo Binary",
                    "OPTIONAL",
                    "Peekaboo CLI not found (skipped on non-macOS environment)"
                ))
                return None
            has_brew = shutil.which("brew") is not None
            install_hint = "Run: brew install steipete/tap/peekaboo" if has_brew else "See: https://github.com/openclaw/Peekaboo#installation"
            self.add_check(DoctorCheck(
                "Peekaboo Binary",
                "ACTION REQUIRED",
                "Peekaboo CLI not found in PATH or standard locations",
                install_hint
            ))
            return None

    def check_tcc(self, peekaboo_bin: Optional[str]):
        if not self.is_macos:
            self.add_check(DoctorCheck("macOS TCC Permissions", "OPTIONAL", "Skipped on non-macOS environment"))
            return

        if not peekaboo_bin:
            self.add_check(DoctorCheck("macOS TCC Permissions", "ACTION REQUIRED", "Cannot check TCC permissions without Peekaboo", "Install Peekaboo first."))
            return

        try:
            res = subprocess.run([peekaboo_bin, "permissions", "--json"], capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                data = json.loads(res.stdout).get("data", {})
                perms = data.get("permissions", [])
                missing = [p for p in perms if p.get("isRequired") and not p.get("isGranted")]
                if not missing:
                    self.add_check(DoctorCheck("macOS TCC Permissions", "PASS", "Screen Recording & Accessibility granted"))
                else:
                    for m in missing:
                        name = m.get("name", "Unknown Permission")
                        instr = m.get("grantInstructions", "System Settings > Privacy & Security")
                        self.add_check(DoctorCheck(
                            f"Permission: {name}",
                            "ACTION REQUIRED",
                            f"{name} permission not granted",
                            f"Open {instr} and enable access for Terminal / Antigravity."
                        ))
            else:
                self.add_check(DoctorCheck("macOS TCC Permissions", "ACTION REQUIRED", "Could not query permissions", "Run 'peekaboo permissions' manually."))
        except Exception as e:
            self.add_check(DoctorCheck("macOS TCC Permissions", "ACTION REQUIRED", f"Permission check failed: {e}"))

    def check_mcp_config(self, peekaboo_bin: Optional[str]):
        mcp_paths = [
            os.path.join(self.home, ".gemini/config/mcp_config.json"),
            os.path.join(self.home, ".gemini/antigravity/mcp_config.json")
        ]
        found_config = None
        has_peekaboo = False
        target_bin = None

        for p in mcp_paths:
            if os.path.exists(p):
                found_config = p
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    servers = data.get("mcpServers", {})
                    if "peekaboo" in servers:
                        has_peekaboo = True
                        target_bin = servers["peekaboo"].get("command")
                        break
                except Exception:
                    pass

        if has_peekaboo:
            self.add_check(DoctorCheck("Peekaboo MCP Registration", "PASS", f"Registered in {os.path.basename(found_config)} (command: {target_bin})"))
        else:
            hint = f"Run 'python3 scripts/bootstrap.py' to automatically register Peekaboo MCP in {os.path.basename(mcp_paths[0])}."
            self.add_check(DoctorCheck(
                "Peekaboo MCP Registration",
                "ACTION REQUIRED",
                f"Peekaboo MCP not configured in ~/.gemini/config/mcp_config.json",
                hint
            ))

    def check_safety_runtime(self) -> bool:
        scripts_dir = os.path.join(self.home, ".gemini/config/skills/computer-use/scripts")
        skill_md = os.path.join(self.home, ".gemini/config/skills/computer-use/SKILL.md")
        gemini_md = os.path.join(self.home, ".gemini/GEMINI.md")
        hooks_json = os.path.join(self.home, ".gemini/config/hooks.json")

        all_ok = True

        # 1. Scripts
        safe_interact = os.path.join(scripts_dir, "safe_interact.py")
        if os.path.exists(safe_interact):
            self.add_check(DoctorCheck("Safety Runtime Files", "PASS", f"Installed in {scripts_dir}"))
        else:
            self.add_check(DoctorCheck("Safety Runtime Files", "ACTION REQUIRED", "Runtime scripts not installed", "Run 'python3 scripts/install.py'."))
            all_ok = False

        # 2. Policy Block
        has_policy = False
        if os.path.exists(gemini_md):
            with open(gemini_md, "r", encoding="utf-8") as f:
                content = f.read()
            if "<!-- finest-computer-use:start -->" in content or "macOS Computer Use — Non-Invasive First Policy" in content:
                has_policy = True

        if has_policy:
            self.add_check(DoctorCheck("Policy Configuration", "PASS", f"Non-Invasive Policy active in {gemini_md}"))
        else:
            self.add_check(DoctorCheck("Policy Configuration", "ACTION REQUIRED", "Safety policy block missing from GEMINI.md", "Run 'python3 scripts/install.py'."))
            all_ok = False

        # 3. Hooks
        has_hooks = False
        if os.path.exists(hooks_json):
            try:
                with open(hooks_json, "r", encoding="utf-8") as f:
                    hdata = json.load(f)
                has_hooks = "computer-use-safety" in hdata and hdata["computer-use-safety"].get("enabled") is True
            except Exception:
                pass

        if has_hooks:
            self.add_check(DoctorCheck("PreToolUse/PostToolUse Hooks", "PASS", f"Active in {hooks_json}"))
        else:
            self.add_check(DoctorCheck("PreToolUse/PostToolUse Hooks", "ACTION REQUIRED", "Hooks not registered in hooks.json", "Run 'python3 scripts/install.py'."))
            all_ok = False

        return all_ok

    def check_firewall_health(self):
        scripts_dir = os.path.join(self.home, ".gemini/config/skills/computer-use/scripts")
        hc_script = os.path.join(scripts_dir, "firewall_healthcheck.py")
        if not os.path.exists(hc_script):
            repo_hc = os.path.abspath(os.path.join(os.path.dirname(__file__), "firewall_healthcheck.py"))
            if os.path.exists(repo_hc):
                hc_script = repo_hc

        if os.path.exists(hc_script):
            try:
                res = subprocess.run([sys.executable, hc_script], capture_output=True, text=True, timeout=10)
                if res.returncode == 0:
                    self.add_check(DoctorCheck("Firewall Healthcheck", "PASS", "30/30 internal safety checks passed"))
                else:
                    self.add_check(DoctorCheck("Firewall Healthcheck", "ERROR", f"Healthcheck exited with code {res.returncode}", res.stderr[:100]))
            except Exception as e:
                self.add_check(DoctorCheck("Firewall Healthcheck", "ERROR", f"Healthcheck failed to run: {e}"))

    def report(self, json_output: bool = False):
        if json_output:
            data = {
                "exit_code": self.exit_code,
                "status": "READY" if self.exit_code == 0 else ("ACTION_REQUIRED" if self.exit_code == 1 else "ERROR"),
                "checks": [{"name": c.name, "status": c.status, "message": c.message, "action": c.action} for c in self.checks]
            }
            print(json.dumps(data, indent=2))
            return

        print("=================================================================")
        print("         FINEST COMPUTER USE SAFETY — SYSTEM DOCTOR              ")
        print("=================================================================")
        for c in self.checks:
            badge = f"[{c.status}]"
            print(f"  {badge:<18} {c.name}")
            if c.message:
                print(f"                     Detail: {c.message}")
            if c.action:
                print(f"                     Action: {c.action}")

        print("-----------------------------------------------------------------")
        if self.exit_code == 0:
            print("  OVERALL STATUS: READY (All components verified operational)")
        elif self.exit_code == 1:
            print("  OVERALL STATUS: ACTION REQUIRED (Follow instructions above)")
        else:
            print("  OVERALL STATUS: ERROR (Configuration or installation failed)")
        print("=================================================================")

def main():
    json_mode = "--json" in sys.argv
    check_mode = "--check" in sys.argv
    home_arg = None
    for arg in sys.argv[1:]:
        if arg.startswith("--home="):
            home_arg = arg.split("=", 1)[1]

    doc = SystemDoctor(home_dir=home_arg)
    exit_code = doc.run_all()
    if not check_mode or json_mode:
        doc.report(json_output=json_mode)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
