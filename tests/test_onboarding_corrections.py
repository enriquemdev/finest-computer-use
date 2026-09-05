#!/usr/bin/env python3
"""
test_onboarding_corrections.py — Focused regression tests for onboarding gaps:
  1. MCP Configuration Handling (Canonical vs secondary preservation, malformed JSON, rollback)
  2. Antigravity Discovery Semantics (Config-only does NOT mean installed, bundle structure verification)
  3. Peekaboo Capability Readiness (MCP mode, permissions inspection, read-only observation)
  4. Evidence Semantics (Distinguish handler smoke from real Antigravity PreToolUse E2E)
  5. Version Metadata Consistency (Reconciliation across all public files)
"""

import sys
import os
import json
import stat
import shutil
import tempfile
import subprocess
import re
from typing import Dict, Any

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS_DIR = os.path.join(REPO_DIR, "scripts")
SRC_DIR = os.path.join(REPO_DIR, "src", "finest_computer_use")

sys.path.insert(0, SCRIPTS_DIR)
sys.path.insert(0, os.path.join(REPO_DIR, "src"))
sys.path.insert(0, SRC_DIR)

class OnboardingCorrectionsTestSuite:
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

    # =========================================================================
    # 1. MCP CONFIGURATION HANDLING
    # =========================================================================
    def test_mcp_canonical_preservation(self):
        print("\n--- MCP-1: Canonical MCP Preservation ---")
        fixture_home = tempfile.mkdtemp(prefix="finest_mcp1_")
        try:
            config_dir = os.path.join(fixture_home, ".gemini", "config")
            os.makedirs(config_dir, exist_ok=True)
            target = os.path.join(config_dir, "mcp_config.json")
            initial_data = {
                "mcpServers": {
                    "database-tools": {
                        "command": "db-mcp",
                        "args": ["--read-only"]
                    }
                },
                "customTopLevel": {"env": "production", "version": 1}
            }
            with open(target, "w") as f:
                json.dump(initial_data, f, indent=2)

            from bootstrap import BootstrapOrchestrator
            orch = BootstrapOrchestrator(home_dir=fixture_home, allow_non_darwin=True)
            ok, msg = orch.configure_mcp("/usr/local/bin/peekaboo")
            self.record("configure_mcp succeeded", ok, msg)

            with open(target, "r") as f:
                updated = json.load(f)

            self.record("database-tools preserved", "database-tools" in updated.get("mcpServers", {}))
            self.record("customTopLevel preserved", updated.get("customTopLevel") == {"env": "production", "version": 1})
            self.record("peekaboo added", "peekaboo" in updated.get("mcpServers", {}))
            self.record("peekaboo entry correct", updated["mcpServers"]["peekaboo"].get("command") == "/usr/local/bin/peekaboo")
        finally:
            shutil.rmtree(fixture_home, ignore_errors=True)

    def test_mcp_secondary_legacy_preservation(self):
        print("\n--- MCP-2: Secondary / Legacy MCP File Preservation ---")
        fixture_home = tempfile.mkdtemp(prefix="finest_mcp2_")
        try:
            # Canonical has server-A
            canonical_dir = os.path.join(fixture_home, ".gemini", "config")
            os.makedirs(canonical_dir, exist_ok=True)
            canonical_file = os.path.join(canonical_dir, "mcp_config.json")
            with open(canonical_file, "w") as f:
                json.dump({"mcpServers": {"server-A": {"command": "cmdA"}}}, f, indent=2)

            # Secondary existing file has server-B
            secondary_dir = os.path.join(fixture_home, ".gemini", "antigravity")
            os.makedirs(secondary_dir, exist_ok=True)
            secondary_file = os.path.join(secondary_dir, "mcp_config.json")
            secondary_initial = {"mcpServers": {"server-B": {"command": "cmdB"}}, "notes": "do not overwrite"}
            with open(secondary_file, "w") as f:
                json.dump(secondary_initial, f, indent=2)

            from bootstrap import BootstrapOrchestrator
            orch = BootstrapOrchestrator(home_dir=fixture_home, allow_non_darwin=True)
            ok, msg = orch.configure_mcp("/usr/local/bin/peekaboo")
            self.record("configure_mcp executed", ok, msg)

            with open(canonical_file, "r") as f:
                can_data = json.load(f)
            with open(secondary_file, "r") as f:
                sec_data = json.load(f)

            self.record("Canonical has server-A", "server-A" in can_data.get("mcpServers", {}))
            self.record("Canonical has peekaboo", "peekaboo" in can_data.get("mcpServers", {}))
            # CRITICAL: Secondary MUST NOT have lost server-B or notes!
            self.record("Secondary file did NOT lose server-B", "server-B" in sec_data.get("mcpServers", {}), f"sec_servers={sec_data.get('mcpServers')}")
            self.record("Secondary file did NOT lose custom keys", sec_data.get("notes") == "do not overwrite")
        finally:
            shutil.rmtree(fixture_home, ignore_errors=True)

    def test_mcp_malformed_json_handling(self):
        print("\n--- MCP-3: Malformed MCP Configuration Handling ---")
        fixture_home = tempfile.mkdtemp(prefix="finest_mcp3_")
        try:
            config_dir = os.path.join(fixture_home, ".gemini", "config")
            os.makedirs(config_dir, exist_ok=True)
            target = os.path.join(config_dir, "mcp_config.json")
            broken_content = "{\n  \"mcpServers\": {\n    broken json"
            with open(target, "w") as f:
                f.write(broken_content)

            from bootstrap import BootstrapOrchestrator
            orch = BootstrapOrchestrator(home_dir=fixture_home, allow_non_darwin=True)
            ok, msg = orch.configure_mcp("/usr/local/bin/peekaboo")

            self.record("Malformed JSON rejected gracefully", ok is False)
            self.record("Descriptive parse error emitted", "parse" in msg.lower() or "json" in msg.lower(), msg)
            with open(target, "r") as f:
                content_after = f.read()
            self.record("Malformed file preserved intact without destructive overwrite", content_after == broken_content)
        finally:
            shutil.rmtree(fixture_home, ignore_errors=True)

    # =========================================================================
    # 2. ANTIGRAVITY DISCOVERY SEMANTICS
    # =========================================================================
    def test_antigravity_config_only_false_positive(self):
        print("\n--- AG-1: Config-Only Does NOT Equal Antigravity Installed ---")
        fixture_home = tempfile.mkdtemp(prefix="finest_ag1_")
        try:
            # Only ~/.gemini exists, NO /Applications/Antigravity.app and NO agy in PATH
            os.makedirs(os.path.join(fixture_home, ".gemini", "config"), exist_ok=True)

            from doctor import SystemDoctor
            doc = SystemDoctor(home_dir=fixture_home)
            doc.check_antigravity()

            # Find Antigravity Discovery check
            ag_checks = [c for c in doc.checks if "Antigravity" in c.name]
            self.record("Doctor has Antigravity check", len(ag_checks) > 0)
            if ag_checks:
                check = ag_checks[0]
                # If only config dir exists without app or CLI, it MUST NOT report PASS!
                # It should report ACTION REQUIRED or REQUIRED or OPTIONAL/NOT CONFIRMED
                self.record("Config-only does NOT report PASS", check.status != "PASS", f"Status was: {check.status}, details: {check.message}")
        finally:
            shutil.rmtree(fixture_home, ignore_errors=True)

    def test_antigravity_fake_app_bundle_rejected(self):
        print("\n--- AG-4: Fake App Bundle Without Valid Structure Rejected ---")
        fixture_home = tempfile.mkdtemp(prefix="finest_ag4_")
        try:
            fake_app = os.path.join(fixture_home, "Applications", "Antigravity.app")
            os.makedirs(fake_app, exist_ok=True) # Empty directory, no Contents/MacOS

            from doctor import SystemDoctor
            doc = SystemDoctor(home_dir=fixture_home)
            doc.check_antigravity()
            ag_checks = [c for c in doc.checks if "Antigravity" in c.name]
            if ag_checks:
                check = ag_checks[0]
                # Empty directory named Antigravity.app without executable must not count as valid bundle
                is_valid = "Application bundle" in check.message
                self.record("Fake app directory without binary rejected", not is_valid, check.message)
        finally:
            shutil.rmtree(fixture_home, ignore_errors=True)

    def test_antigravity_valid_app_bundle_accepted(self):
        print("\n--- AG-2: Valid App Bundle Structure Accepted ---")
        fixture_home = tempfile.mkdtemp(prefix="finest_ag2_")
        try:
            app_dir = os.path.join(fixture_home, "Applications", "Antigravity.app", "Contents", "MacOS")
            os.makedirs(app_dir, exist_ok=True)
            bin_path = os.path.join(app_dir, "Antigravity")
            with open(bin_path, "w") as f:
                f.write("#!/bin/sh\nexit 0\n")
            os.chmod(bin_path, stat.S_IRWXU)

            from doctor import SystemDoctor
            doc = SystemDoctor(home_dir=fixture_home)
            doc.check_antigravity()
            ag_checks = [c for c in doc.checks if "Antigravity" in c.name]
            if ag_checks:
                check = ag_checks[0]
                self.record("Valid app bundle accepted", check.status == "PASS" and "Application bundle" in check.message, check.message)
        finally:
            shutil.rmtree(fixture_home, ignore_errors=True)

    # =========================================================================
    # 3. PEEKABOO CAPABILITY READINESS
    # =========================================================================
    def test_peekaboo_missing_mcp_capability(self):
        print("\n--- PK-2: Executable Missing Required MCP Mode Is NOT Ready ---")
        tmp_dir = tempfile.mkdtemp(prefix="finest_pk2_")
        try:
            fake_peekaboo = os.path.join(tmp_dir, "peekaboo")
            # Binary that responds to --version, but rejects 'mcp'
            script_code = (
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "if '--version' in sys.argv:\n"
                "    print('Peekaboo 1.0.0')\n"
                "    sys.exit(0)\n"
                "if 'mcp' in sys.argv:\n"
                "    print('Unknown subcommand mcp', file=sys.stderr)\n"
                "    sys.exit(1)\n"
                "sys.exit(0)\n"
            )
            with open(fake_peekaboo, "w") as f:
                f.write(script_code)
            os.chmod(fake_peekaboo, stat.S_IRWXU)

            from doctor import SystemDoctor
            doc = SystemDoctor()
            # Test capability probe
            mcp_cap = doc.probe_peekaboo_mcp(fake_peekaboo) if hasattr(doc, "probe_peekaboo_mcp") else None
            self.record("Doctor probes MCP capability", hasattr(doc, "probe_peekaboo_mcp"))
            if mcp_cap is not None:
                self.record("Missing MCP capability detected as False", mcp_cap is False)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_peekaboo_read_only_observation_probe(self):
        print("\n--- PK-5: Doctor Validates Read-Only Observation Capability ---")
        from doctor import SystemDoctor
        doc = SystemDoctor()
        self.record("Doctor has read-only observation probe", hasattr(doc, "probe_peekaboo_observation"))

    # =========================================================================
    # 4. EVIDENCE SEMANTICS & SMOKE TEST
    # =========================================================================
    def test_smoke_test_evidence_distinction(self):
        print("\n--- Evidence Semantics: Smoke Test Output Labels ---")
        smoke_script = os.path.join(SCRIPTS_DIR, "smoke_test.py")
        with open(smoke_script, "r") as f:
            content = f.read()

        # It must NOT label direct safe_interact.py invocation as 'Antigravity Hook E2E: PASS'
        self.record("Smoke test distinguishes handler smoke from Antigravity E2E",
                    "Standalone PreToolUse Handler" in content or "Hook Handler Smoke" in content or "safe_interact" in content)

        # It must explicitly mark real Antigravity PreToolUse E2E as NOT EXECUTED if run standalone
        self.record("Smoke test reports NOT EXECUTED for real Antigravity hook when run standalone",
                    "NOT EXECUTED" in content)

    def test_fresh_mac_acceptance_evidence_levels(self):
        print("\n--- Evidence Semantics: Fresh Mac Acceptance Confidence Levels ---")
        acc_script = os.path.join(SCRIPTS_DIR, "fresh_mac_acceptance.py")
        with open(acc_script, "r") as f:
            content = f.read()

        self.record("Acceptance script defines confidence levels",
                    "confidence_level" in content or "HOST_INTEGRATION" in content or "PORTABLE" in content)
        self.record("Acceptance script retains TRUE CLEAN MAC: NOT EXECUTED",
                    "TRUE CLEAN MAC" in content and "NOT EXECUTED" in content)

    # =========================================================================
    # 5. VERSION CONSISTENCY RECONCILIATION
    # =========================================================================
    def test_version_consistency_automated(self):
        print("\n--- Version Consistency: Authoritative Surfaces ---")
        # 1. VERSION
        with open(os.path.join(REPO_DIR, "VERSION"), "r") as f:
            ver_file = f.read().strip()

        # 2. pyproject.toml
        with open(os.path.join(REPO_DIR, "pyproject.toml"), "r") as f:
            pyproject_text = f.read()
        m_pyproj = re.search(r'version\s*=\s*"([^"]+)"', pyproject_text)
        pyproj_ver = m_pyproj.group(1) if m_pyproj else None

        # 3. MANIFEST.json
        with open(os.path.join(REPO_DIR, "MANIFEST.json"), "r") as f:
            manifest_data = json.load(f)
        manifest_ver = manifest_data.get("version")

        # 4. README.md badge and title
        with open(os.path.join(REPO_DIR, "README.md"), "r") as f:
            readme_text = f.read()
        m_badge = re.search(r'badge/version-([0-9\.]+)-blue', readme_text)
        badge_ver = m_badge.group(1) if m_badge else None

        print(f"  VERSION file: {ver_file}")
        print(f"  pyproject.toml: {pyproj_ver}")
        print(f"  MANIFEST.json: {manifest_ver}")
        print(f"  README badge: {badge_ver}")

        self.record("VERSION matches pyproject.toml", ver_file == pyproj_ver, f"{ver_file} vs {pyproj_ver}")
        self.record("VERSION matches MANIFEST.json", ver_file == manifest_ver, f"{ver_file} vs {manifest_ver}")
        self.record("VERSION matches README badge", ver_file == badge_ver, f"{ver_file} vs {badge_ver}")

    # =========================================================================
    # 6. MCP CONFLICT PROTECTION (v1.1.2)
    # =========================================================================
    def test_mcp_conflict_protection(self):
        print("\n--- MCP-CONFLICT: Existing Custom Peekaboo MCP Conflict Protection ---")
        fixture_home = tempfile.mkdtemp(prefix="finest_mcp_conflict_")
        try:
            config_dir = os.path.join(fixture_home, ".gemini", "config")
            os.makedirs(config_dir, exist_ok=True)
            target = os.path.join(config_dir, "mcp_config.json")
            from bootstrap import BootstrapOrchestrator

            # Case A: No existing peekaboo
            with open(target, "w") as f:
                json.dump({"mcpServers": {}}, f)
            orch = BootstrapOrchestrator(home_dir=fixture_home, allow_non_darwin=True)
            ok, msg = orch.configure_mcp("/usr/local/bin/peekaboo")
            self.record("Case A: No existing Peekaboo -> Added", ok is True)

            # Case B: Identical entry -> no-op
            ok2, msg2 = orch.configure_mcp("/usr/local/bin/peekaboo")
            self.record("Case B: Identical entry -> No-op", ok2 is True and "identically" in msg2.lower())

            # Case C: Custom command path
            custom_entry = {
                "command": "/opt/custom/peekaboo",
                "args": ["mcp", "--allow-foreground"]
            }
            with open(target, "w") as f:
                json.dump({"mcpServers": {"peekaboo": custom_entry}}, f)
            ok3, msg3 = orch.configure_mcp("/usr/local/bin/peekaboo")
            self.record("Case C: Custom command path -> ACTION REQUIRED", ok3 is False and "ACTION REQUIRED" in msg3, msg3)
            with open(target, "r") as f:
                content3 = json.load(f)
            self.record("Case C: Custom entry preserved unchanged", content3["mcpServers"]["peekaboo"] == custom_entry)

            # Case D: Custom args
            custom_args_entry = {
                "command": "/usr/local/bin/peekaboo",
                "args": ["mcp", "--custom-option"]
            }
            with open(target, "w") as f:
                json.dump({"mcpServers": {"peekaboo": custom_args_entry}}, f)
            ok4, msg4 = orch.configure_mcp("/usr/local/bin/peekaboo")
            self.record("Case D: Custom args -> ACTION REQUIRED", ok4 is False and "ACTION REQUIRED" in msg4)
            with open(target, "r") as f:
                content4 = json.load(f)
            self.record("Case D: Custom args preserved unchanged", content4["mcpServers"]["peekaboo"] == custom_args_entry)

            # Case E: Custom env or other keys
            custom_env_entry = {
                "command": "/usr/local/bin/peekaboo",
                "args": ["mcp", "--allow-foreground"],
                "env": {"PEEKABOO_PORT": "9090"}
            }
            with open(target, "w") as f:
                json.dump({"mcpServers": {"peekaboo": custom_env_entry}}, f)
            ok5, msg5 = orch.configure_mcp("/usr/local/bin/peekaboo")
            self.record("Case E: Custom env -> ACTION REQUIRED", ok5 is False and "ACTION REQUIRED" in msg5)
            with open(target, "r") as f:
                content5 = json.load(f)
            self.record("Case E: Custom env preserved unchanged", content5["mcpServers"]["peekaboo"] == custom_env_entry)

            # Case F: Legacy Finest-owned entry migrated
            legacy_entry = {
                "command": "/usr/local/bin/peekaboo",
                "args": ["mcp"],
                "_finest_managed": True
            }
            with open(target, "w") as f:
                json.dump({"mcpServers": {"peekaboo": legacy_entry}}, f)
            ok6, msg6 = orch.configure_mcp("/usr/local/bin/peekaboo")
            self.record("Case F: Legacy Finest-owned entry -> Migrated", ok6 is True)
            with open(target, "r") as f:
                content6 = json.load(f)
            self.record("Case F: Args upgraded to include --allow-foreground", content6["mcpServers"]["peekaboo"]["args"] == ["mcp", "--allow-foreground"])
        finally:
            shutil.rmtree(fixture_home, ignore_errors=True)

    # =========================================================================
    # 7. CANONICAL VS LEGACY MCP DOCTOR SEMANTICS (v1.1.2)
    # =========================================================================
    def test_doctor_canonical_vs_legacy_semantics(self):
        print("\n--- DOC-MCP: Canonical vs Legacy Doctor Semantics ---")
        fixture_home = tempfile.mkdtemp(prefix="finest_doc_mcp_")
        try:
            from doctor import SystemDoctor
            can_dir = os.path.join(fixture_home, ".gemini", "config")
            leg_dir = os.path.join(fixture_home, ".gemini", "antigravity")
            os.makedirs(can_dir, exist_ok=True)
            os.makedirs(leg_dir, exist_ok=True)
            can_file = os.path.join(can_dir, "mcp_config.json")
            leg_file = os.path.join(leg_dir, "mcp_config.json")

            # DOC-MCP-1: Canonical valid -> PASS
            with open(can_file, "w") as f:
                json.dump({"mcpServers": {"peekaboo": {"command": "/usr/local/bin/peekaboo"}}}, f)
            doc1 = SystemDoctor(home_dir=fixture_home)
            doc1.check_mcp_config("/usr/local/bin/peekaboo")
            check1 = next((c for c in doc1.checks if "Peekaboo MCP" in c.name), None)
            self.record("DOC-MCP-1: Canonical valid -> PASS", check1 and check1.status == "PASS")

            # DOC-MCP-2: Canonical absent, legacy valid -> ACTION REQUIRED
            os.remove(can_file)
            with open(leg_file, "w") as f:
                json.dump({"mcpServers": {"peekaboo": {"command": "/usr/local/bin/peekaboo"}}}, f)
            doc2 = SystemDoctor(home_dir=fixture_home)
            doc2.check_mcp_config("/usr/local/bin/peekaboo")
            check2 = next((c for c in doc2.checks if "Peekaboo MCP" in c.name), None)
            self.record("DOC-MCP-2: Canonical absent, legacy valid -> ACTION REQUIRED",
                        check2 and check2.status == "ACTION REQUIRED" and "legacy" in check2.message.lower(),
                        getattr(check2, "message", ""))

            # DOC-MCP-3: Canonical and legacy symlink-equivalent -> PASS
            with open(can_file, "w") as f:
                json.dump({"mcpServers": {"peekaboo": {"command": "/usr/local/bin/peekaboo"}}}, f)
            os.remove(leg_file)
            os.symlink(can_file, leg_file)
            doc3 = SystemDoctor(home_dir=fixture_home)
            doc3.check_mcp_config("/usr/local/bin/peekaboo")
            check3 = next((c for c in doc3.checks if "Peekaboo MCP" in c.name), None)
            self.record("DOC-MCP-3: Symlinked legacy -> PASS", check3 and check3.status == "PASS")

            # DOC-MCP-4: Canonical malformed, legacy valid -> ERROR / ACTION REQUIRED
            os.remove(leg_file)
            with open(leg_file, "w") as f:
                json.dump({"mcpServers": {"peekaboo": {"command": "/usr/local/bin/peekaboo"}}}, f)
            with open(can_file, "w") as f:
                f.write("{invalid json")
            doc4 = SystemDoctor(home_dir=fixture_home)
            doc4.check_mcp_config("/usr/local/bin/peekaboo")
            check4 = next((c for c in doc4.checks if "Peekaboo MCP" in c.name), None)
            self.record("DOC-MCP-4: Malformed canonical -> ERROR/ACTION REQUIRED",
                        check4 and check4.status in ("ERROR", "ACTION REQUIRED"))

            # DOC-MCP-5: Both independent and canonical valid -> PASS based on canonical
            with open(can_file, "w") as f:
                json.dump({"mcpServers": {"peekaboo": {"command": "/usr/local/bin/peekaboo"}}}, f)
            with open(leg_file, "w") as f:
                json.dump({"mcpServers": {"other": {"command": "other"}}}, f)
            doc5 = SystemDoctor(home_dir=fixture_home)
            doc5.check_mcp_config("/usr/local/bin/peekaboo")
            check5 = next((c for c in doc5.checks if "Peekaboo MCP" in c.name), None)
            self.record("DOC-MCP-5: Independent files, canonical valid -> PASS",
                        check5 and check5.status == "PASS" and "canonical" in check5.message.lower())
        finally:
            shutil.rmtree(fixture_home, ignore_errors=True)

    # =========================================================================
    # 8. UNIFIED ANTIGRAVITY DISCOVERY (v1.1.2)
    # =========================================================================
    def test_unified_antigravity_discovery(self):
        print("\n--- DISC: Unified Antigravity Discovery Module ---")
        fixture_home = tempfile.mkdtemp(prefix="finest_disc_")
        try:
            import importlib
            discovery = importlib.import_module("finest_computer_use.discovery")
            self.record("Unified discovery module exists", hasattr(discovery, "discover_antigravity"))

            # DISC-1: Only ~/.gemini
            os.makedirs(os.path.join(fixture_home, ".gemini"), exist_ok=True)
            res1 = discovery.discover_antigravity(home_dir=fixture_home)
            self.record("DISC-1: Only ~/.gemini -> installed_confirmed is False", res1.installed_confirmed is False)

            # DISC-2: Valid app bundle
            app_macos = os.path.join(fixture_home, "Applications", "Antigravity.app", "Contents", "MacOS")
            os.makedirs(app_macos, exist_ok=True)
            app_bin = os.path.join(app_macos, "Antigravity")
            with open(app_bin, "w") as f:
                f.write("#!/bin/sh\nexit 0\n")
            os.chmod(app_bin, stat.S_IRWXU)
            res2 = discovery.discover_antigravity(home_dir=fixture_home)
            self.record("DISC-2: Valid app bundle -> installed_confirmed is True", res2.installed_confirmed is True)

            # DISC-3: Valid CLI only
            shutil.rmtree(os.path.join(fixture_home, "Applications"))
            bin_dir = os.path.join(fixture_home, "bin")
            os.makedirs(bin_dir, exist_ok=True)
            cli_bin = os.path.join(bin_dir, "agy")
            with open(cli_bin, "w") as f:
                f.write("#!/bin/sh\nexit 0\n")
            os.chmod(cli_bin, stat.S_IRWXU)
            res3 = discovery.discover_antigravity(home_dir=fixture_home)
            self.record("DISC-3: Valid CLI only -> installed_confirmed is True", res3.installed_confirmed is True)

            # DISC-4: Fake app bundle with empty Contents/MacOS
            shutil.rmtree(bin_dir)
            fake_macos = os.path.join(fixture_home, "Applications", "Antigravity.app", "Contents", "MacOS")
            os.makedirs(fake_macos, exist_ok=True)
            res4 = discovery.discover_antigravity(home_dir=fixture_home)
            self.record("DISC-4: Fake app bundle with empty MacOS -> installed_confirmed is False", res4.installed_confirmed is False)

            # DISC-5: Config + valid app
            with open(os.path.join(fake_macos, "Antigravity"), "w") as f:
                f.write("#!/bin/sh\nexit 0\n")
            os.chmod(os.path.join(fake_macos, "Antigravity"), stat.S_IRWXU)
            res5 = discovery.discover_antigravity(home_dir=fixture_home)
            self.record("DISC-5: Config + valid app -> installed_confirmed is True", res5.installed_confirmed is True)

            # DISC-6: Callers consistency
            from bootstrap import BootstrapOrchestrator
            from doctor import SystemDoctor
            b_orch = BootstrapOrchestrator(home_dir=fixture_home, allow_non_darwin=True)
            b_ok, _ = b_orch.discover_antigravity()
            doc = SystemDoctor(home_dir=fixture_home)
            doc.check_antigravity()
            doc_ag = next((c for c in doc.checks if "Antigravity" in c.name), None)
            self.record("DISC-6: Bootstrap and Doctor agree on valid app", b_ok is True and doc_ag and doc_ag.status == "PASS")
        finally:
            shutil.rmtree(fixture_home, ignore_errors=True)

    # =========================================================================
    # 9. TRUTHFUL SMOKE & ACCEPTANCE SEMANTICS (v1.1.2)
    # =========================================================================
    def test_smoke_and_acceptance_truthful_semantics(self):
        print("\n--- SMOKE-TRUTH: Truthful Smoke and Acceptance Semantics ---")
        smoke_script = os.path.join(SCRIPTS_DIR, "smoke_test.py")
        acc_script = os.path.join(SCRIPTS_DIR, "fresh_mac_acceptance.py")

        with open(smoke_script, "r") as f:
            smoke_src = f.read()

        self.record("Smoke test does not claim 'ALL RUNTIME GUARDS FUNCTIONING'",
                    "ALL RUNTIME GUARDS FUNCTIONING" not in smoke_src)
        self.record("Smoke test does not claim '4/4' pass",
                    "4/4" not in smoke_src)
        self.record("Smoke test uses 'PASS WITH MANUAL E2E PENDING'",
                    "PASS WITH MANUAL E2E PENDING" in smoke_src or "PASS WITH MANUAL EVIDENCE PENDING" in smoke_src)

        with open(acc_script, "r") as f:
            acc_src = f.read()

        self.record("Acceptance script does not claim 'ALL TESTS PASSED'",
                    "ALL TESTS PASSED" not in acc_src and "all_passed" not in acc_src.lower().replace("report[\"all_passed\"]", ""))
        self.record("Acceptance script verdict includes MANUAL EVIDENCE PENDING",
                    "MANUAL EVIDENCE PENDING" in acc_src or "MANUAL STEPS PENDING" in acc_src)

    def summary(self) -> bool:
        print("\n=================================================================")
        print(f"ONBOARDING CORRECTIONS SUMMARY: {self.passed} PASSED, {self.failed} FAILED")
        print("=================================================================")
        return self.failed == 0

def main():
    suite = OnboardingCorrectionsTestSuite()
    suite.test_mcp_canonical_preservation()
    suite.test_mcp_secondary_legacy_preservation()
    suite.test_mcp_malformed_json_handling()
    suite.test_antigravity_config_only_false_positive()
    suite.test_antigravity_fake_app_bundle_rejected()
    suite.test_antigravity_valid_app_bundle_accepted()
    suite.test_peekaboo_missing_mcp_capability()
    suite.test_peekaboo_read_only_observation_probe()
    suite.test_smoke_test_evidence_distinction()
    suite.test_fresh_mac_acceptance_evidence_levels()
    suite.test_version_consistency_automated()
    # v1.1.2 new regression suites
    suite.test_mcp_conflict_protection()
    suite.test_doctor_canonical_vs_legacy_semantics()
    suite.test_unified_antigravity_discovery()
    suite.test_smoke_and_acceptance_truthful_semantics()
    ok = suite.summary()
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
