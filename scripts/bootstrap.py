#!/usr/bin/env python3
"""
bootstrap.py — One-Command Onboarding and Readiness Orchestrator for Finest Computer Use.

Orchestration Flow:
  1. Platform & Environment Pre-flight (macOS 15+, Python 3.9+, Architecture)
  2. Antigravity Discovery (App bundle, CLI, ~/.gemini root)
  3. Peekaboo Discovery (Binary discovery, version verification, installation guidance)
  4. macOS TCC Permissions Check (Screen Recording & Accessibility via Peekaboo)
  5. Antigravity MCP Configuration (Idempotent merger into mcp_config.json)
  6. Finest Computer Use Safety Layer (Install runtime, policy, hooks via install.py)
  7. Post-Installation Verification & System Doctor
  8. Reload / Restart Guidance

Modes:
  default         Interactive human-friendly setup and verification
  --check         Non-interactive diagnostic check only (exits 0=ready, 1=action required, 2=error)
  --dry-run       Shows what would be installed/configured without modifying disk
  --json          Emits structured machine-readable status
  --home=<path>   Override target home directory for isolated testing
"""

import sys
import os
import json
import shutil
import platform
import subprocess
from typing import Optional, Dict, Any, Tuple

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS_DIR = os.path.join(REPO_DIR, "scripts")
SRC_DIR = os.path.join(REPO_DIR, "src")
sys.path.insert(0, SCRIPTS_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from doctor import SystemDoctor
from finest_computer_use.discovery import discover_antigravity as unified_discover_ag, is_valid_app_bundle

class BootstrapOrchestrator:
    def __init__(self, home_dir: Optional[str] = None, dry_run: bool = False, skip_mcp: bool = False, skip_doctor: bool = False, allow_non_darwin: bool = False):
        self.home = home_dir or os.environ.get("GEMINI_HOME") or os.path.expanduser("~")
        self.dry_run = dry_run
        self.skip_mcp = skip_mcp
        self.skip_doctor = skip_doctor or os.environ.get("FINEST_SKIP_DOCTOR") == "1"
        self.allow_non_darwin = allow_non_darwin or os.environ.get("FINEST_ALLOW_NON_DARWIN") == "1"
        self.gemini_dir = os.path.join(self.home, ".gemini")
        self.config_dir = os.path.join(self.gemini_dir, "config")
        self.mcp_config_path = os.path.join(self.config_dir, "mcp_config.json")
        self.antigravity_mcp_path = os.path.join(self.gemini_dir, "antigravity", "mcp_config.json")
        self.backup_dir = os.path.join(self.gemini_dir, "backup")

    def print_banner(self):
        print("=================================================================")
        print("        FINEST COMPUTER USE SAFETY — ONBOARDING BOOTSTRAP        ")
        print("=================================================================")
        if self.dry_run:
            print("  MODE: DRY-RUN (Simulating changes, no files will be modified)  ")
            print("-----------------------------------------------------------------")

    def preflight_checks(self) -> Tuple[bool, str]:
        # 1. Platform check
        system = platform.system()
        arch = platform.machine()
        if system != "Darwin":
            if not self.allow_non_darwin:
                return False, f"Unsupported operating system: {system}. Finest Computer Use on desktop requires macOS (pass --allow-non-darwin for testing/CI)."
            if sys.version_info < (3, 9):
                py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
                return False, f"Unsupported Python version: {py_ver}. Requires Python >= 3.9."
            return True, f"{system} ({arch}) portable testing mode, Python {sys.version_info.major}.{sys.version_info.minor} OK"

        mac_ver = platform.mac_ver()[0]
        try:
            major = int(mac_ver.split(".")[0])
        except (ValueError, IndexError):
            major = 0

        if major < 15:
            return False, (
                f"Unsupported macOS version: {mac_ver}. "
                f"Peekaboo 4.3+ and modern ScreenCaptureKit automation require macOS 15.0+ (Sequoia)."
            )

        # 2. Python check
        if sys.version_info < (3, 9):
            py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
            return False, f"Unsupported Python version: {py_ver}. Requires Python >= 3.9."

        return True, f"macOS {mac_ver} ({arch}), Python {sys.version_info.major}.{sys.version_info.minor} OK"

    def _is_valid_app_bundle(self, app_path: str) -> bool:
        """Verify that an app bundle has the expected macOS structure with an executable."""
        return is_valid_app_bundle(app_path)

    def discover_antigravity(self) -> Tuple[bool, str]:
        discovery = unified_discover_ag(self.home, allow_simulated=(self.allow_non_darwin or self.dry_run))
        if discovery.installed_confirmed:
            return True, discovery.status_summary

        if discovery.config_found:
            if self.allow_non_darwin or self.dry_run:
                return True, "Antigravity configuration present (simulated in portable/dry-run mode)"
            return False, "Antigravity configuration directory exists (~/.gemini), but application bundle or CLI was not confirmed. Please install Antigravity."

        if self.allow_non_darwin or self.dry_run:
            return True, "Antigravity simulated (portable/dry-run mode)"

        msg = (
            "Antigravity application not found in /Applications or PATH.\n"
            "  Please install Antigravity before proceeding:\n"
            "  https://antigravity.google"
        )
        return False, msg

    def discover_peekaboo(self) -> Tuple[Optional[str], Optional[str]]:
        candidates = [
            shutil.which("peekaboo"),
            "/opt/homebrew/bin/peekaboo",
            "/usr/local/bin/peekaboo"
        ]
        peekaboo_bin = next((c for c in candidates if c and os.path.exists(c) and os.access(c, os.X_OK)), None)
        if not peekaboo_bin:
            if self.allow_non_darwin or self.dry_run:
                return "/opt/homebrew/bin/peekaboo", "Peekaboo placeholder (portable/dry-run mode)"
            has_brew = shutil.which("brew") is not None
            install_cmd = "brew install steipete/tap/peekaboo" if has_brew else "https://github.com/openclaw/Peekaboo#installation"
            msg = (
                "Peekaboo CLI is not installed or not in PATH.\n"
                f"  Install command: {install_cmd}"
            )
            return None, msg

        try:
            res = subprocess.run([peekaboo_bin, "--version"], capture_output=True, text=True, timeout=5)
            ver = res.stdout.strip() or res.stderr.strip()
            return peekaboo_bin, ver
        except Exception as e:
            return peekaboo_bin, f"Error querying version: {e}"

    def configure_mcp(self, peekaboo_bin: str) -> Tuple[bool, str]:
        """Idempotently register Peekaboo in canonical Antigravity mcp_config.json while preserving all existing servers and keys."""
        if self.skip_mcp:
            return True, "Skipped by --skip-mcp flag."

        os.makedirs(self.config_dir, exist_ok=True)
        target_file = self.mcp_config_path

        existing_data: Dict[str, Any] = {"mcpServers": {}}
        backup_path = None
        if os.path.exists(target_file):
            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except Exception as e:
                return False, f"Could not parse existing {target_file}: {e}"

        servers = existing_data.setdefault("mcpServers", {})
        existing_peekaboo = servers.get("peekaboo")

        desired_entry = {
            "command": peekaboo_bin,
            "args": ["mcp", "--allow-foreground"]
        }

        # Case A: No existing peekaboo -> add Finest-managed entry
        if existing_peekaboo is None:
            entry_to_write = dict(desired_entry)
            entry_to_write["_finest_managed"] = True
        else:
            # Case B: Check if identical entry (ignoring management metadata)
            stripped_existing = {k: v for k, v in existing_peekaboo.items() if k not in ("_finest_managed", "managedBy")}
            if stripped_existing == desired_entry:
                return True, "Peekaboo MCP already configured identically."

            # Case C/F: Check if provably legacy Finest-managed
            is_legacy_finest = existing_peekaboo.get("_finest_managed") is True or existing_peekaboo.get("managedBy") == "finest"
            if is_legacy_finest:
                entry_to_write = dict(desired_entry)
                entry_to_write["_finest_managed"] = True
            else:
                # Case D & E: Custom user entry differs -> PRESERVE and emit ACTION REQUIRED
                diff_details = []
                curr_cmd = existing_peekaboo.get("command")
                curr_args = existing_peekaboo.get("args")
                if curr_cmd != desired_entry["command"]:
                    diff_details.append(f"command='{curr_cmd}' vs expected '{desired_entry['command']}'")
                if curr_args != desired_entry["args"]:
                    diff_details.append(f"args={curr_args} vs expected {desired_entry['args']}")
                extra_keys = [k for k in existing_peekaboo.keys() if k not in ("command", "args")]
                if extra_keys:
                    diff_details.append(f"custom keys={extra_keys}")

                return False, (
                    f"ACTION REQUIRED: Existing Peekaboo MCP configuration differs from Finest-managed configuration.\n"
                    f"  Detected: {', '.join(diff_details)}\n"
                    f"  Existing configuration was preserved intact in {target_file}."
                )

        if self.dry_run:
            return True, f"[DRY-RUN] Would update {target_file} to register Peekaboo MCP (command: {peekaboo_bin})."

        # Backup existing mcp config
        if os.path.exists(target_file):
            os.makedirs(self.backup_dir, exist_ok=True)
            backup_path = os.path.join(self.backup_dir, f"mcp_config_backup_{os.getpid()}.json")
            try:
                shutil.copy2(target_file, backup_path)
            except Exception as e:
                return False, f"Failed to create backup of {target_file}: {e}"

        servers["peekaboo"] = entry_to_write

        # Atomic replacement with fsync and post-write validation
        tmp_target = f"{target_file}.tmp.{os.getpid()}"
        try:
            with open(tmp_target, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_target, target_file)

            # Validate written file
            with open(target_file, "r", encoding="utf-8") as f:
                verified_data = json.load(f)
            if "peekaboo" not in verified_data.get("mcpServers", {}):
                raise ValueError("Verification failed: peekaboo entry missing after write")

            return True, f"Successfully registered Peekaboo MCP in {target_file}."
        except Exception as e:
            if backup_path and os.path.exists(backup_path):
                try:
                    shutil.copy2(backup_path, target_file)
                except Exception:
                    pass
            if os.path.exists(tmp_target):
                try:
                    os.remove(tmp_target)
                except Exception:
                    pass
            return False, f"Failed to write updated {target_file}: {e}"

    def install_safety_layer(self) -> Tuple[bool, str]:
        """Invoke install.py to stage, compile, deploy, and verify the safety runtime."""
        if self.dry_run:
            return True, "[DRY-RUN] Would execute scripts/install.py to deploy runtime, policy, and hooks."

        install_script = os.path.join(SCRIPTS_DIR, "install.py")
        env = os.environ.copy()
        env["HOME"] = self.home

        try:
            res = subprocess.run([sys.executable, install_script], env=env, capture_output=True, text=True, timeout=30)
            if res.returncode == 0:
                return True, "Finest Computer Use Safety Layer installed and verified."
            else:
                return False, f"Installation failed:\n{res.stderr or res.stdout}"
        except Exception as e:
            return False, f"Failed to run installer: {e}"

    def run_bootstrap(self) -> int:
        self.print_banner()

        # Step 1: Preflight
        print("\n1. Verifying System & Platform Requirements...")
        ok, msg = self.preflight_checks()
        if not ok:
            print(f"  [ERROR] {msg}")
            return 2
        print(f"  [PASS] {msg}")

        # Step 2: Antigravity Discovery
        print("\n2. Discovering Antigravity...")
        ok, msg = self.discover_antigravity()
        if not ok:
            print(f"  [ERROR] {msg}")
            return 2
        print(f"  [PASS] {msg}")

        # Step 3: Peekaboo Discovery
        print("\n3. Discovering Peekaboo Desktop Automation...")
        peekaboo_bin, p_msg = self.discover_peekaboo()
        if not peekaboo_bin:
            print(f"  [ACTION REQUIRED] {p_msg}")
            print("\n  After installing Peekaboo, re-run 'python3 scripts/bootstrap.py'.")
            return 1
        print(f"  [PASS] Peekaboo binary found: {peekaboo_bin}")
        print(f"         Version: {p_msg}")

        # Step 4: TCC Permissions
        print("\n4. Checking macOS Accessibility & Screen Recording Permissions...")
        doctor = SystemDoctor(home_dir=self.home)
        doctor.check_tcc(peekaboo_bin)
        tcc_issues = [c for c in doctor.checks if c.status == "ACTION REQUIRED"]
        if tcc_issues:
            print("  [ACTION REQUIRED] One or more macOS permissions are missing:")
            for issue in tcc_issues:
                print(f"    - {issue.name}: {issue.message}")
                print(f"      Action: {issue.action}")
            print("\n  Please grant the permissions above in System Settings, then re-run bootstrap.")
            # Note: We can continue with configuration even if TCC is pending, but notify clearly.

        # Step 5: Configure MCP Server
        print("\n5. Configuring Peekaboo MCP in Antigravity...")
        ok, mcp_msg = self.configure_mcp(peekaboo_bin)
        if not ok:
            print(f"  [ERROR] {mcp_msg}")
            return 2
        print(f"  [PASS] {mcp_msg}")

        # Step 6: Install Safety Layer
        print("\n6. Installing Finest Computer Use Safety Layer...")
        ok, s_msg = self.install_safety_layer()
        if not ok:
            print(f"  [ERROR] {s_msg}")
            return 2
        print(f"  [PASS] {s_msg}")

        # Step 7: System Doctor & Verification
        if self.dry_run:
            print("\n7. System Doctor Simulation...")
            print("  [DRY-RUN] Post-install doctor check skipped during dry-run.")
            print("\n=================================================================")
            print("   BOOTSTRAP DRY-RUN COMPLETE — NO FILES WERE MODIFIED           ")
            print("=================================================================\n")
            return 0

        if self.skip_doctor:
            print("\n7. System Doctor Verification...")
            print("  [SKIP] Post-install doctor check skipped (--skip-doctor).")
            print("\n=================================================================")
            print("   BOOTSTRAP CONFIGURATION COMPLETE                              ")
            print("=================================================================\n")
            return 0

        print("\n7. Running Post-Installation System Doctor...")
        doc = SystemDoctor(home_dir=self.home)
        exit_code = doc.run_all()
        doc.report(json_output=False)

        # Step 8: Next steps / Reload guidance
        if exit_code == 0:
            print("\n=================================================================")
            print("   BOOTSTRAP COMPLETE — YOUR MAC IS FULLY CONFIGURED & SECURED   ")
            print("=================================================================")
            print("  Next Steps:")
            print("  1. If Antigravity was running, restart Antigravity to load the")
            print("     new Peekaboo MCP server and safety hooks.")
            print("  2. Test normal functionality with: python3 scripts/smoke_test.py")
            print("=================================================================\n")
        else:
            print("\n  Bootstrap completed with items requiring action. See Doctor output above.\n")

        return exit_code

def main():
    dry_run = "--dry-run" in sys.argv
    check_mode = "--check" in sys.argv
    json_mode = "--json" in sys.argv
    skip_mcp = "--skip-mcp" in sys.argv
    skip_doctor = "--skip-doctor" in sys.argv or os.environ.get("FINEST_SKIP_DOCTOR") == "1"
    allow_non_darwin = "--allow-non-darwin" in sys.argv or os.environ.get("FINEST_ALLOW_NON_DARWIN") == "1"
    home_arg = None
    for arg in sys.argv[1:]:
        if arg.startswith("--home="):
            home_arg = arg.split("=", 1)[1]

    if check_mode:
        doc = SystemDoctor(home_dir=home_arg)
        code = doc.run_all()
        if not check_mode or json_mode:
            doc.report(json_output=json_mode)
        sys.exit(code)

    orchestrator = BootstrapOrchestrator(home_dir=home_arg, dry_run=dry_run, skip_mcp=skip_mcp, skip_doctor=skip_doctor, allow_non_darwin=allow_non_darwin)
    code = orchestrator.run_bootstrap()
    sys.exit(code)

if __name__ == "__main__":
    main()
