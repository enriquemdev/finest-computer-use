#!/usr/bin/env python3
"""
test_fresh_install.py — Clean-Machine Onboarding & Lifecycle Test Suite.

Validates Level 2 Clean Environment Simulation:
  1. Virgin / Fresh Home Installation (Zero preexisting files -> Fully operational)
  2. Dry-run Mode (Zero filesystem mutations)
  3. Bootstrap Idempotence (Second run creates zero duplicate configurations)
  4. Preexisting User Configuration Preservation (GEMINI.md, unrelated MCPs, custom hooks)
  5. Safe Uninstallation & Rollback (Removes managed files, preserves user config)
  6. Failure Injection & Recovery (Invalid syntax staging, broken candidate rollback)
  7. System Doctor Exit Codes (0=Ready, 1=Action Required, 2=Error)
"""

import sys
import os
import json
import shutil
import platform
import tempfile
import subprocess
from typing import Dict, Any

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS_DIR = os.path.join(REPO_DIR, "scripts")

BOOTSTRAP_SCRIPT = os.path.join(SCRIPTS_DIR, "bootstrap.py")
INSTALL_SCRIPT = os.path.join(SCRIPTS_DIR, "install.py")
UNINSTALL_SCRIPT = os.path.join(SCRIPTS_DIR, "uninstall.py")
DOCTOR_SCRIPT = os.path.join(SCRIPTS_DIR, "doctor.py")
DEPLOY_SCRIPT = os.path.join(SCRIPTS_DIR, "deploy_firewall.py")

class FreshInstallTestSuite:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    def record(self, test_name: str, success: bool, detail: str = ""):
        if success:
            self.passed += 1
            print(f"  [PASS] {test_name}")
        else:
            self.failed += 1
            print(f"  [FAIL] {test_name}: {detail}")
            assert success, f"{test_name} failed: {detail}"

    def _get_env(self, fixture_home: str) -> Dict[str, str]:
        env = os.environ.copy()
        env["HOME"] = fixture_home
        env["FINEST_ALLOW_NON_DARWIN"] = "1"
        return env

    def test_dry_run_zero_mutation(self):
        print("\n1. Testing Bootstrap Dry-Run (Zero Filesystem Mutation)...")
        fixture_home = tempfile.mkdtemp(prefix="finest_dryrun_")
        try:
            env = self._get_env(fixture_home)
            # Run dry-run
            res = subprocess.run([sys.executable, BOOTSTRAP_SCRIPT, "--dry-run", f"--home={fixture_home}"], env=env, capture_output=True, text=True)
            self.record("Dry-run execution exit code 0", res.returncode == 0, res.stderr)

            # Confirm .gemini was not created or modified with real files
            gemini_dir = os.path.join(fixture_home, ".gemini")
            skills_dir = os.path.join(gemini_dir, "config", "skills")
            self.record("Dry-run created no skills directory", not os.path.exists(skills_dir), skills_dir)
            self.record("Dry-run created no GEMINI.md", not os.path.exists(os.path.join(gemini_dir, "GEMINI.md")))
        finally:
            shutil.rmtree(fixture_home, ignore_errors=True)

    def test_clean_home_install(self):
        print("\n2. Testing Clean-Machine Bootstrap Installation...")
        fixture_home = tempfile.mkdtemp(prefix="finest_clean_")
        try:
            env = self._get_env(fixture_home)
            # Pre-seed Antigravity config directory so bootstrap identifies Antigravity
            os.makedirs(os.path.join(fixture_home, ".gemini", "config"), exist_ok=True)

            res = subprocess.run([sys.executable, BOOTSTRAP_SCRIPT, f"--home={fixture_home}"], env=env, capture_output=True, text=True)
            self.record("Clean bootstrap run exit code 0", res.returncode == 0, res.stderr or res.stdout)

            # Check MCP config
            mcp_file = os.path.join(fixture_home, ".gemini/config/mcp_config.json")
            self.record("mcp_config.json created", os.path.exists(mcp_file))
            with open(mcp_file, "r") as f:
                mcp_data = json.load(f)
            self.record("peekaboo registered in mcpServers", "peekaboo" in mcp_data.get("mcpServers", {}))

            # Check GEMINI.md
            gemini_md = os.path.join(fixture_home, ".gemini/GEMINI.md")
            self.record("GEMINI.md created", os.path.exists(gemini_md))
            with open(gemini_md, "r") as f:
                g_content = f.read()
            self.record("Managed policy block in GEMINI.md", "<!-- finest-computer-use:start -->" in g_content)

            # Check hooks.json
            hooks_json = os.path.join(fixture_home, ".gemini/config/hooks.json")
            self.record("hooks.json created", os.path.exists(hooks_json))
            with open(hooks_json, "r") as f:
                h_data = json.load(f)
            self.record("computer-use-safety registered in hooks.json", "computer-use-safety" in h_data)

            # Check runtime files
            scripts_dir = os.path.join(fixture_home, ".gemini/config/skills/computer-use/scripts")
            self.record("safe_interact.py installed", os.path.exists(os.path.join(scripts_dir, "safe_interact.py")))
            self.record("effect_firewall.py installed", os.path.exists(os.path.join(scripts_dir, "effect_firewall.py")))

            # Run doctor on new fixture
            res_doc = subprocess.run([sys.executable, DOCTOR_SCRIPT, f"--home={fixture_home}", "--check"], env=env, capture_output=True, text=True)
            expected_codes = (0,) if (platform.system() == "Darwin" and shutil.which("peekaboo")) else (0, 1)
            self.record("Doctor check on clean install passes (no critical errors)", res_doc.returncode in expected_codes, f"code={res_doc.returncode}")
        finally:
            shutil.rmtree(fixture_home, ignore_errors=True)

    def test_bootstrap_idempotence(self):
        print("\n3. Testing Bootstrap Idempotence...")
        fixture_home = tempfile.mkdtemp(prefix="finest_idempotent_")
        try:
            env = self._get_env(fixture_home)
            os.makedirs(os.path.join(fixture_home, ".gemini", "config"), exist_ok=True)

            # Run 1
            subprocess.run([sys.executable, BOOTSTRAP_SCRIPT, f"--home={fixture_home}"], env=env, check=True, capture_output=True)
            # Run 2
            res2 = subprocess.run([sys.executable, BOOTSTRAP_SCRIPT, f"--home={fixture_home}"], env=env, capture_output=True, text=True)
            self.record("Second bootstrap run succeeds", res2.returncode == 0, res2.stderr)

            # Verify no duplicates
            gemini_md = os.path.join(fixture_home, ".gemini/GEMINI.md")
            with open(gemini_md, "r") as f:
                g_content = f.read()
            count_managed = g_content.count("<!-- finest-computer-use:start -->")
            self.record("Exactly one managed block in GEMINI.md", count_managed == 1, f"count={count_managed}")

            hooks_json = os.path.join(fixture_home, ".gemini/config/hooks.json")
            with open(hooks_json, "r") as f:
                h_data = json.load(f)
            safety_keys = [k for k in h_data.keys() if k == "computer-use-safety"]
            self.record("Exactly one safety section in hooks.json", len(safety_keys) == 1, f"keys={safety_keys}")

            mcp_file = os.path.join(fixture_home, ".gemini/config/mcp_config.json")
            with open(mcp_file, "r") as f:
                m_data = json.load(f)
            self.record("Exactly one peekaboo entry in mcp_config.json", list(m_data.get("mcpServers", {}).keys()).count("peekaboo") == 1)
        finally:
            shutil.rmtree(fixture_home, ignore_errors=True)

    def test_preexisting_config_preservation(self):
        print("\n4. Testing Preexisting User Configuration Preservation...")
        fixture_home = tempfile.mkdtemp(prefix="finest_preserve_")
        try:
            env = self._get_env(fixture_home)
            os.makedirs(os.path.join(fixture_home, ".gemini", "config"), exist_ok=True)

            # 1. Seed preexisting GEMINI.md with user instructions
            user_instructions = "# User Instructions\n- Be concise.\n- Always write tests.\n"
            gemini_md = os.path.join(fixture_home, ".gemini/GEMINI.md")
            with open(gemini_md, "w") as f:
                f.write(user_instructions)

            # 2. Seed preexisting mcp_config.json with unrelated server
            unrelated_mcp = {
                "mcpServers": {
                    "database-tools": {
                        "command": "db-mcp",
                        "args": ["--read-only"]
                    }
                }
            }
            mcp_file = os.path.join(fixture_home, ".gemini/config/mcp_config.json")
            with open(mcp_file, "w") as f:
                json.dump(unrelated_mcp, f, indent=2)

            # 3. Seed preexisting hooks.json with unrelated hook
            unrelated_hooks = {
                "linter-hook": {
                    "enabled": True,
                    "PreToolUse": [{"matcher": "edit"}]
                }
            }
            hooks_file = os.path.join(fixture_home, ".gemini/config/hooks.json")
            with open(hooks_file, "w") as f:
                json.dump(unrelated_hooks, f, indent=2)

            # Run bootstrap
            subprocess.run([sys.executable, BOOTSTRAP_SCRIPT, f"--home={fixture_home}"], env=env, check=True, capture_output=True)

            # Verify preservation
            with open(gemini_md, "r") as f:
                g_text = f.read()
            self.record("Preexisting user instructions preserved in GEMINI.md", "Always write tests." in g_text)
            self.record("Safety block appended to GEMINI.md", "<!-- finest-computer-use:start -->" in g_text)

            with open(mcp_file, "r") as f:
                m_curr = json.load(f)
            self.record("Unrelated MCP server preserved", "database-tools" in m_curr.get("mcpServers", {}))
            self.record("Peekaboo MCP merged alongside unrelated MCP", "peekaboo" in m_curr.get("mcpServers", {}))

            with open(hooks_file, "r") as f:
                h_curr = json.load(f)
            self.record("Unrelated hook preserved", "linter-hook" in h_curr)
            self.record("Safety hook merged alongside unrelated hook", "computer-use-safety" in h_curr)

            # 4. Run uninstaller and verify complete restoration
            print("\n5. Testing Safe Uninstallation & Config Preservation...")
            res_un = subprocess.run([sys.executable, UNINSTALL_SCRIPT, f"--home={fixture_home}"], env=env, capture_output=True, text=True)
            self.record("Uninstall exit code 0", res_un.returncode == 0, res_un.stderr)

            with open(gemini_md, "r") as f:
                g_un = f.read()
            self.record("Managed safety block removed from GEMINI.md", "<!-- finest-computer-use:start -->" not in g_un)
            self.record("Preexisting user instructions remain after uninstall", "Always write tests." in g_un)

            with open(hooks_file, "r") as f:
                h_un = json.load(f)
            self.record("Safety hooks removed from hooks.json", "computer-use-safety" not in h_un)
            self.record("Unrelated hook remains after uninstall", "linter-hook" in h_un)
        finally:
            shutil.rmtree(fixture_home, ignore_errors=True)

    def test_failure_injection_and_rollback(self):
        print("\n6. Testing Failure Injection & Staged Rollback...")
        stage_dir = tempfile.mkdtemp(prefix="finest_stage_test_")
        try:
            sys.path.insert(0, SCRIPTS_DIR)
            from deploy_firewall import deploy_module
            src_fw = os.path.join(REPO_DIR, "src/finest_computer_use/effect_firewall.py")
            shutil.copy2(src_fw, os.path.join(stage_dir, "effect_firewall.py"))
            with open(src_fw, "r") as f:
                good_code = f.read()

            # Deploy broken syntax candidate
            broken_syntax = "def broken():\n    return 1\n   bad indent"
            ok, msg = deploy_module("effect_firewall.py", broken_syntax, target_dir=stage_dir, run_healthcheck=False)
            self.record("Staging catches syntax error", ok is False)
            self.record("Staging rejection message is descriptive", "STAGING FAILED: Syntax" in msg)

            with open(os.path.join(stage_dir, "effect_firewall.py"), "r") as f:
                current_code = f.read()
            self.record("Good module preserved intact after syntax error", current_code == good_code)
        finally:
            shutil.rmtree(stage_dir, ignore_errors=True)

    def summary(self) -> bool:
        print("\n=================================================================")
        print(f"FRESH INSTALL HARNESS SUMMARY: {self.passed} PASSED, {self.failed} FAILED")
        print("=================================================================")
        return self.failed == 0

def main():
    suite = FreshInstallTestSuite()
    suite.test_dry_run_zero_mutation()
    suite.test_clean_home_install()
    suite.test_bootstrap_idempotence()
    suite.test_preexisting_config_preservation()
    suite.test_failure_injection_and_rollback()
    ok = suite.summary()
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
