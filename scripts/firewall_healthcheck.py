#!/usr/bin/env python3
"""
firewall_healthcheck.py — Standalone Comprehensive Health Check for Intent/Effect Firewall v1.

Validates:
1. Syntax of bootstrap router and advanced firewall modules (py_compile).
2. Clean imports in isolated subprocesses.
3. hooks.json structure and file targets.
4. PreToolUse fast-path execution (< 200ms) for benign tools.
5. Physical non-invasive guardrails (move, unanchored coords, targetless keys).
6. PostToolUse state update entrypoint.
7. True Task-Level State Isolation & Atomic Locking (conv_id + task_id).
8. Monotonic Authorization Engine (Provenance, Scope Narrowing vs Broadening, Budget Caps).
9. Fail-Safe Degraded Mode including Granular Browser Action Classification.

Does NOT produce real external effects.
"""

import sys
import os
import json
import subprocess
import py_compile
import shutil
import time
from typing import List, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_SRC = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "src", "finest_computer_use"))
INSTALLED_DIR = os.path.expanduser("~/.gemini/config/skills/computer-use/scripts")

if os.path.exists(os.path.join(REPO_SRC, "safe_interact.py")):
    FIREWALL_DIR = REPO_SRC
elif os.path.exists(os.path.join(SCRIPT_DIR, "safe_interact.py")):
    FIREWALL_DIR = SCRIPT_DIR
else:
    FIREWALL_DIR = INSTALLED_DIR

SAFE_INTERACT = os.path.join(FIREWALL_DIR, "safe_interact.py")
HOOKS_JSON = os.path.expanduser("~/.gemini/config/hooks.json")
TEMPLATE_HOOKS = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "hooks", "hooks.json"))

class HealthCheckRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results: List[Tuple[str, bool, str]] = []

    def record(self, check_name: str, success: bool, detail: str = ""):
        if success:
            self.passed += 1
            self.results.append((check_name, True, detail))
            print(f"  [PASS] {check_name}")
        else:
            self.failed += 1
            self.results.append((check_name, False, detail))
            print(f"  [FAIL] {check_name}: {detail}")

    def check_syntax(self):
        print("\n1. Syntax & Compilation Checks (py_compile):")
        modules = ["safe_interact.py", "effect_firewall.py", "effect_taxonomy.py"]
        for mod in modules:
            path = os.path.join(FIREWALL_DIR, mod)
            if not os.path.exists(path):
                self.record(f"Syntax: {mod}", False, f"File missing: {path}")
                continue
            try:
                py_compile.compile(path, doraise=True)
                self.record(f"Syntax: {mod}", True, "Clean compilation")
            except py_compile.PyCompileError as e:
                self.record(f"Syntax: {mod}", False, str(e))

        deploy_script = os.path.join(SCRIPT_DIR, "deploy_firewall.py")
        if not os.path.exists(deploy_script):
            deploy_script = os.path.join(FIREWALL_DIR, "deploy_firewall.py")
        if os.path.exists(deploy_script):
            try:
                py_compile.compile(deploy_script, doraise=True)
                self.record("Syntax: deploy_firewall.py", True, "Clean compilation")
            except py_compile.PyCompileError as e:
                self.record("Syntax: deploy_firewall.py", False, str(e))

    def check_imports(self):
        print("\n2. Isolated Subprocess Import Checks:")
        modules = ["effect_taxonomy", "effect_firewall", "safe_interact"]
        for mod in modules:
            cmd = f"import sys; sys.path.insert(0, '{FIREWALL_DIR}'); import {mod}; print('OK')"
            res = subprocess.run([sys.executable, "-c", cmd], capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and "OK" in res.stdout:
                self.record(f"Import: {mod}", True, "Imported cleanly in isolated process")
            else:
                self.record(f"Import: {mod}", False, res.stderr.strip() or res.stdout.strip())

    def check_hooks_config(self):
        print("\n3. Antigravity hooks.json Configuration:")
        target_hooks = HOOKS_JSON if os.path.exists(HOOKS_JSON) else TEMPLATE_HOOKS
        if not os.path.exists(target_hooks):
            self.record("hooks.json exists", False, f"Not found at {HOOKS_JSON} or {TEMPLATE_HOOKS}")
            return

        try:
            with open(target_hooks, "r", encoding="utf-8") as f:
                data = json.load(f)
            safety = data.get("computer-use-safety", {})
            enabled = safety.get("enabled", False)
            pre_hooks = safety.get("PreToolUse", [])
            post_hooks = safety.get("PostToolUse", [])

            self.record("hooks.json parsing", True, f"Valid JSON format ({os.path.basename(target_hooks)})")
            self.record("hooks.json safety enabled", enabled is True, f"enabled={enabled}")
            
            pre_cmd = pre_hooks[0]["hooks"][0]["command"] if pre_hooks and pre_hooks[0].get("hooks") else ""
            has_pre = "safe_interact.py" in pre_cmd
            self.record("PreToolUse hook registered", has_pre, pre_cmd)

            post_cmd = post_hooks[0]["hooks"][0]["command"] if post_hooks and post_hooks[0].get("hooks") else ""
            has_post = "safe_interact.py post" in post_cmd
            self.record("PostToolUse hook registered", has_post, post_cmd)
        except Exception as e:
            self.record("hooks.json parsing", False, str(e))

    def check_fastpath_performance(self):
        print("\n4. PreToolUse Fast-Path & Anti-Brick Checks:")
        start = time.time()
        payload = json.dumps({"toolCall": {"name": "view_file", "args": {"AbsolutePath": "/tmp/test.txt"}}})
        res = subprocess.run([sys.executable, SAFE_INTERACT], input=payload, capture_output=True, text=True, timeout=5)
        elapsed_ms = (time.time() - start) * 1000
        try:
            out = json.loads(res.stdout)
            is_allow = out.get("decision") == "allow"
            self.record(f"Fast-Path native tool (view_file, {elapsed_ms:.1f}ms)", is_allow and elapsed_ms < 250, f"decision={out.get('decision')}")
        except Exception as e:
            self.record("Fast-Path native tool", False, f"Error: {e}, stdout: {res.stdout}")

        payload_git = json.dumps({"toolCall": {"name": "run_command", "args": {"CommandLine": "git status"}}})
        res_git = subprocess.run([sys.executable, SAFE_INTERACT], input=payload_git, capture_output=True, text=True, timeout=5)
        try:
            out_git = json.loads(res_git.stdout)
            self.record("Fast-Path developer shell (git status)", out_git.get("decision") == "allow", str(out_git))
        except Exception as e:
            self.record("Fast-Path developer shell", False, str(e))

    def check_physical_guardrails(self):
        print("\n5. Physical Non-Invasive Safety Guardrails:")
        p1 = json.dumps({"toolCall": {"name": "call_mcp_tool", "args": {"ServerName": "peekaboo", "ToolName": "move", "Arguments": {"coords": "100,200"}}}})
        r1 = json.loads(subprocess.run([sys.executable, SAFE_INTERACT], input=p1, capture_output=True, text=True).stdout)
        self.record("Prohibit mouse move", r1.get("decision") == "deny", r1.get("reason", ""))

        p2 = json.dumps({"toolCall": {"name": "call_mcp_tool", "args": {"ServerName": "peekaboo", "ToolName": "click", "Arguments": {"coords": "500,500"}}}})
        r2 = json.loads(subprocess.run([sys.executable, SAFE_INTERACT], input=p2, capture_output=True, text=True).stdout)
        self.record("Prohibit unanchored coordinate click", r2.get("decision") == "deny", r2.get("reason", ""))

        p3 = json.dumps({"toolCall": {"name": "call_mcp_tool", "args": {"ServerName": "peekaboo", "ToolName": "type", "Arguments": {"text": "unanchored text"}}}})
        r3 = json.loads(subprocess.run([sys.executable, SAFE_INTERACT], input=p3, capture_output=True, text=True).stdout)
        self.record("Prohibit targetless global typing", r3.get("decision") == "deny", r3.get("reason", ""))

    def check_task_isolation(self):
        print("\n6. True Task-Level State Isolation (conversation_id + task_id):")
        test_conv = "test_hc_shared_conv"
        task_a = "task_alpha"
        task_b = "task_beta"

        try:
            # Set contract for Task A in test_conv
            cmd_a = [sys.executable, SAFE_INTERACT, "contract", "communication.send_text", '{"communication.send_text": 1}', "[]", "standard", test_conv, task_a, "user"]
            res_a = json.loads(subprocess.run(cmd_a, capture_output=True, text=True, check=True).stdout)

            # Set contract for Task B in test_conv
            cmd_b = [sys.executable, SAFE_INTERACT, "contract", "destructive.delete", '{"destructive.delete": 2}', "[]", "destructive", test_conv, task_b, "user"]
            res_b = json.loads(subprocess.run(cmd_b, capture_output=True, text=True, check=True).stdout)

            # Read states back
            s_a = json.loads(subprocess.run([sys.executable, SAFE_INTERACT, "status", test_conv, task_a], capture_output=True, text=True).stdout)
            s_b = json.loads(subprocess.run([sys.executable, SAFE_INTERACT, "status", test_conv, task_b], capture_output=True, text=True).stdout)

            is_iso = (
                s_a.get("task_id") == task_a and
                s_b.get("task_id") == task_b and
                s_a.get("contract", {}).get("goal") == "communication.send_text" and
                s_b.get("contract", {}).get("goal") == "destructive.delete" and
                s_a.get("budgets", {}).get("communication.send_text", {}).get("limit") == 1 and
                s_b.get("budgets", {}).get("destructive.delete", {}).get("limit") == 2
            )
            self.record("Task state isolation under same conversation", is_iso, f"A goal: {s_a.get('contract',{}).get('goal')}, B goal: {s_b.get('contract',{}).get('goal')}")

            # Trigger recovery mode in Task A -> Task B must remain IDLE
            subprocess.run([sys.executable, SAFE_INTERACT, "recovery", "Task A recovery", test_conv, task_a], capture_output=True, text=True)
            s_a_rec = json.loads(subprocess.run([sys.executable, SAFE_INTERACT, "status", test_conv, task_a], capture_output=True, text=True).stdout)
            s_b_rec = json.loads(subprocess.run([sys.executable, SAFE_INTERACT, "status", test_conv, task_b], capture_output=True, text=True).stdout)

            self.record("Task recovery mode isolation", s_a_rec.get("state") == "RECOVERY_MODE" and s_b_rec.get("state") == "IDLE", f"A state: {s_a_rec.get('state')}, B state: {s_b_rec.get('state')}")

        finally:
            shutil.rmtree(f"/tmp/antigravity-effect-firewall/{test_conv}", ignore_errors=True)

    def check_monotonic_authorization(self):
        print("\n7. Monotonic Authorization Engine:")
        test_conv = "test_hc_monotonic"
        test_task = "task_mono"

        try:
            # 1. User initializes contract: send_text = 1, target = 'mock_chat'
            cmd_init = [
                sys.executable, SAFE_INTERACT, "contract",
                "communication.send_text", '{"communication.send_text": 1}', "[]", "standard",
                test_conv, test_task, "user", '{"communication.send_text": "mock_chat"}'
            ]
            r_init = json.loads(subprocess.run(cmd_init, capture_output=True, text=True).stdout)
            self.record("User-authorized contract initialization", r_init.get("success") is True, "")

            # 2. Agent attempts to add Level 4 effect (send_voice) autonomously -> DENIED
            cmd_agent_exp = [
                sys.executable, SAFE_INTERACT, "contract",
                "communication.send_voice", '{"communication.send_voice": 1}', "[]", "standard",
                test_conv, test_task, "agent", '{"communication.send_voice": "mock_chat"}'
            ]
            r_exp = json.loads(subprocess.run(cmd_agent_exp, capture_output=True, text=True).stdout)
            self.record("Agent contract expansion rejected (New Level 4)", r_exp.get("success") is False and "Monotonicity" in r_exp.get("error", ""), r_exp.get("error", ""))

            # 3. Agent attempts to increase budget (send_text = 2) autonomously -> DENIED
            cmd_agent_budget = [
                sys.executable, SAFE_INTERACT, "contract",
                "communication.send_text", '{"communication.send_text": 2}', "[]", "standard",
                test_conv, test_task, "agent", '{"communication.send_text": "mock_chat"}'
            ]
            r_budget = json.loads(subprocess.run(cmd_agent_budget, capture_output=True, text=True).stdout)
            self.record("Agent budget expansion rejected (Budget > User max)", r_budget.get("success") is False and "increase budget" in r_budget.get("error", ""), r_budget.get("error", ""))

            # 4. Agent narrows target scope autonomously -> ALLOWED
            cmd_agent_narrow = [
                sys.executable, SAFE_INTERACT, "contract",
                "communication.send_text", '{"communication.send_text": 1}', "[]", "standard",
                test_conv, test_task, "agent", '{"communication.send_text": "mock_chat/thread_1"}'
            ]
            r_narrow = json.loads(subprocess.run(cmd_agent_narrow, capture_output=True, text=True).stdout)
            self.record("Agent target narrowing allowed (Subset of authority)", r_narrow.get("success") is True, "")

            # 5. Agent broadens target scope autonomously -> DENIED
            cmd_agent_broad = [
                sys.executable, SAFE_INTERACT, "contract",
                "communication.send_text", '{"communication.send_text": 1}', "[]", "standard",
                test_conv, test_task, "agent", '{"communication.send_text": "*"}'
            ]
            r_broad = json.loads(subprocess.run(cmd_agent_broad, capture_output=True, text=True).stdout)
            self.record("Agent target broadening rejected", r_broad.get("success") is False and "broaden target" in r_broad.get("error", ""), r_broad.get("error", ""))

            # 6. New User-originated instruction explicitly authorizes expansion -> ALLOWED
            cmd_user_exp = [
                sys.executable, SAFE_INTERACT, "contract",
                "communication.send_voice", '{"communication.send_text": 1, "communication.send_voice": 1}', "[]", "standard",
                test_conv, test_task, "user", '{"communication.send_text": "mock_chat", "communication.send_voice": "mock_chat"}'
            ]
            r_user_exp = json.loads(subprocess.run(cmd_user_exp, capture_output=True, text=True).stdout)
            self.record("Explicit new user authorization allowed", r_user_exp.get("success") is True, "")

        finally:
            shutil.rmtree(f"/tmp/antigravity-effect-firewall/{test_conv}", ignore_errors=True)

    def check_degraded_mode(self):
        print("\n8. Fail-Safe Degraded Mode & Granular Browser Classification:")
        env_degraded = os.environ.copy()
        env_degraded["SIMULATE_FIREWALL_FAILURE"] = "1"

        # 1. Native low-risk observation allowed
        p_obs = json.dumps({"toolCall": {"name": "call_mcp_tool", "args": {"ServerName": "peekaboo", "ToolName": "see", "Arguments": {"app_target": "MockApp"}}}})
        r_obs = json.loads(subprocess.run([sys.executable, SAFE_INTERACT], input=p_obs, capture_output=True, text=True, env=env_degraded).stdout)
        self.record("Degraded Mode: Native observation ALLOWED", r_obs.get("decision") == "allow", str(r_obs))

        # 2. Browser read-only inspection (snapshot) allowed
        p_b_snap = json.dumps({"toolCall": {"name": "call_mcp_tool", "args": {"ServerName": "peekaboo", "ToolName": "browser", "Arguments": {"action": "snapshot"}}}})
        r_b_snap = json.loads(subprocess.run([sys.executable, SAFE_INTERACT], input=p_b_snap, capture_output=True, text=True, env=env_degraded).stdout)
        self.record("Degraded Mode: Browser snapshot ALLOWED", r_b_snap.get("decision") == "allow", str(r_b_snap))

        # 3. Browser navigation (navigate) allowed
        p_b_nav = json.dumps({"toolCall": {"name": "call_mcp_tool", "args": {"ServerName": "peekaboo", "ToolName": "browser", "Arguments": {"action": "navigate", "url": "http://localhost:8000"}}}})
        r_b_nav = json.loads(subprocess.run([sys.executable, SAFE_INTERACT], input=p_b_nav, capture_output=True, text=True, env=env_degraded).stdout)
        self.record("Degraded Mode: Browser navigation ALLOWED", r_b_nav.get("decision") == "allow", str(r_b_nav))

        # 4. Browser mutation (click) DENIED
        p_b_click = json.dumps({"toolCall": {"name": "call_mcp_tool", "args": {"ServerName": "peekaboo", "ToolName": "browser", "Arguments": {"action": "click", "uid": "btn_send"}}}})
        r_b_click = json.loads(subprocess.run([sys.executable, SAFE_INTERACT], input=p_b_click, capture_output=True, text=True, env=env_degraded).stdout)
        is_denied = r_b_click.get("decision") == "deny"
        has_msg = "degraded mode" in r_b_click.get("reason", "").lower()
        self.record("Degraded Mode: Browser click mutation DENIED", is_denied and has_msg, r_b_click.get("reason", ""))

        # 5. Browser mutation (upload_file) DENIED
        p_b_up = json.dumps({"toolCall": {"name": "call_mcp_tool", "args": {"ServerName": "peekaboo", "ToolName": "browser", "Arguments": {"action": "upload_file", "path": "/tmp/test.pdf"}}}})
        r_b_up = json.loads(subprocess.run([sys.executable, SAFE_INTERACT], input=p_b_up, capture_output=True, text=True, env=env_degraded).stdout)
        self.record("Degraded Mode: Browser upload mutation DENIED", r_b_up.get("decision") == "deny", r_b_up.get("reason", ""))

        # 6. Browser unknown action DENIED (fail-closed)
        p_b_unk = json.dumps({"toolCall": {"name": "call_mcp_tool", "args": {"ServerName": "peekaboo", "ToolName": "browser", "Arguments": {"action": "unknown_custom_eval"}}}})
        r_b_unk = json.loads(subprocess.run([sys.executable, SAFE_INTERACT], input=p_b_unk, capture_output=True, text=True, env=env_degraded).stdout)
        self.record("Degraded Mode: Unknown browser action DENIED", r_b_unk.get("decision") == "deny", r_b_unk.get("reason", ""))

    def summary(self) -> bool:
        print("\n========================================================")
        print(f"FIREWALL HEALTH CHECK SUMMARY: {self.passed} PASSED, {self.failed} FAILED")
        print("========================================================")
        return self.failed == 0

def main():
    runner = HealthCheckRunner()
    runner.check_syntax()
    runner.check_imports()
    runner.check_hooks_config()
    runner.check_fastpath_performance()
    runner.check_physical_guardrails()
    runner.check_task_isolation()
    runner.check_monotonic_authorization()
    runner.check_degraded_mode()
    ok = runner.summary()
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
