#!/usr/bin/env python3
"""
safe_interact.py — Resilient Computer Use Safety Router & Effect Firewall Bootstrap.

Architecture:
1. Minimal Resilient Bootstrap Router: Pure Python stdlib, zero heavy dependencies on startup.
2. Fast-Path Triage: Benign developer commands, file ops, and non-Peekaboo tools pass immediately (< 20ms).
3. Fail-Safe Graceful Degradation:
   - Read-only native tools and benign navigation remain allowed (anti-bricking).
   - Browser actions in degraded mode are classified by action: read-only/nav ALLOWED; mutations DENIED.
   - High-impact mutations, unanchored clicks, and Level 4/5 actions are DENIED (anti-fail-open).
4. True Task-Level Isolation: State, budgets, contracts, and receipts keyed by (conversation_id, task_id).
5. Monotonic Authorization: Prevents silent privilege escalation (NEW AUTHORITY ⊆ USER AUTHORITY).
6. Focus Restoration Guard: Respects USER ACTIVITY WINS.
"""

import sys
import os
import json
import re
import subprocess
import time
from typing import Optional, Dict, Any, Tuple

# Tools that are completely unrelated to Computer Use / GUI mutations (Instant Fast-Path)
NATIVE_FASTPATH_TOOLS = {
    "view_file", "write_to_file", "replace_file_content", "list_dir",
    "grep_search", "find_by_name", "read_url_content", "search_web",
    "ask_question", "invoke_subagent", "define_subagent", "manage_subagents",
    "schedule", "manage_task", "send_message", "generate_image",
    "list_resources", "read_resource"
}

# Observation tools that are safe to run in degraded mode (Notice: browser is NOT included here)
READ_ONLY_PEEKABOO_TOOLS = {
    "see", "inspect_ui", "capture", "image", "permissions", "verify_state"
}

GUI_AUTOMATION_INDICATORS = [
    "peekaboo", "osascript", "system events", "cliclick", "screencapture", "cgestate"
]

DEGRADED_LOG_PATH = "/tmp/computer_use_degraded.log"
PREHOOK_LOG_PATH = "/tmp/pretooluse_hook.log"

def log_degraded_event(failing_module: str, exc_msg: str, tool_name: str, decision: str) -> None:
    """Log degraded mode event without sensitive payloads."""
    try:
        event = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "failing_module": failing_module,
            "exception": exc_msg,
            "tool": tool_name,
            "decision": decision
        }
        with open(DEGRADED_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception:
        pass

def get_current_frontmost_app() -> Optional[str]:
    """Return the name of the currently active/frontmost application."""
    script = 'tell application "System Events" to get name of first application process whose frontmost is true'
    try:
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=2)
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return None

def safe_restore_focus(previous_app: str, agent_target_app: str) -> bool:
    """Focus restoration respecting 'USER ACTIVITY WINS'."""
    current_app = get_current_frontmost_app()
    if not current_app:
        return False

    if current_app.lower() == agent_target_app.lower():
        subprocess.run(["osascript", "-e", f'tell application "{previous_app}" to activate'], timeout=2)
        return True
    else:
        sys.stderr.write(
            f"[FocusGuard] User activity detected (current frontmost: '{current_app}', agent target: '{agent_target_app}'). "
            f"Skipping focus restoration to '{previous_app}'. User activity wins.\n"
        )
        return False

def inspect_peekaboo_physical_safety(tool_name: str, args: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    """Validate physical/concurrency guardrails. Always enforced even in degraded safety mode."""
    # Rule 1: Physical mouse movement is strictly prohibited
    if tool_name == "move":
        return (
            "deny",
            "BLOCKED [PreToolUse Safety]: Physical mouse movement ('move') is prohibited under Non-Invasive First policy. "
            "Use semantic background actions (set_value, click on: elem_id) instead."
        )

    # Rule 2: Unanchored coordinate clicks
    if tool_name == "click":
        has_coords = "coords" in args and bool(args["coords"])
        has_elem = ("on" in args and bool(args["on"])) or ("query" in args and bool(args["query"]))

        if has_coords and not has_elem:
            is_foreground = bool(args.get("foreground", False)) or args.get("background") is False
            has_snapshot = bool(args.get("snapshot")) or bool(args.get("coordinate_reference"))
            has_pid = bool(args.get("pid"))

            if not is_foreground and not has_snapshot:
                return (
                    "deny",
                    "BLOCKED [PreToolUse Safety]: Background coordinate click without snapshot or coordinate_reference. "
                    "Unanchored coordinates are unsafe during concurrent use. Capture a fresh snapshot first."
                )

            if is_foreground and not (has_snapshot or has_pid):
                return (
                    "deny",
                    "BLOCKED [PreToolUse Safety]: Unanchored foreground coordinate click ('click' with coords but without snapshot, "
                    "coordinate_reference, or pid). You must obtain a fresh snapshot and anchor your coordinate action."
                )

    # Rule 3: Targetless global keyboard injection
    if tool_name in ["type", "press"]:
        has_target_app = bool(args.get("app")) or bool(args.get("app_target")) or bool(args.get("pid"))
        has_target_elem = bool(args.get("on"))

        if not has_target_app and not has_target_elem:
            return (
                "deny",
                f"BLOCKED [PreToolUse Safety]: Targetless global keyboard input ('{tool_name}' without target app, pid, or element). "
                "Specify target application or element to prevent accidental typing into user's active window."
            )

    return ("allow", None)

def inspect_cli_physical_safety(cmd: str) -> Tuple[str, Optional[str]]:
    """Inspect shell commands for unsafe peekaboo CLI invocations."""
    if "peekaboo" not in cmd:
        return ("allow", None)

    tokens = cmd.split()
    if "move" in tokens:
        idx = tokens.index("peekaboo") if "peekaboo" in tokens else -1
        if idx != -1 and idx + 1 < len(tokens) and tokens[idx + 1] == "move":
            return (
                "deny",
                "BLOCKED [PreToolUse Safety]: 'peekaboo move' physically moves the cursor and is prohibited under Non-Invasive First policy."
            )

    if "click" in tokens and ("--at" in tokens or "-a" in tokens):
        has_anchor = any(flag in tokens for flag in ["--snapshot", "-s", "--app", "--window", "--window-id", "--pid"])
        if not has_anchor:
            return (
                "deny",
                "BLOCKED [PreToolUse Safety]: Unanchored global click 'peekaboo click --at X,Y' without --snapshot, --app, or --window anchor."
            )

    if ("press" in tokens or "type" in tokens):
        subcmd = "press" if "press" in tokens else "type"
        has_target = any(flag in tokens for flag in ["--app", "--pid", "--on"])
        if not has_target:
            return (
                "deny",
                f"BLOCKED [PreToolUse Safety]: Targetless global keyboard input 'peekaboo {subcmd}' without --app or --pid."
            )

    return ("allow", None)

def fallback_classify_browser_degraded(args: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    """Bootstrap standalone fallback for degraded browser classification."""
    action = args.get("action", "")
    mcp_tool = args.get("mcp_tool", "")
    read_only_actions = {
        "status", "connect", "disconnect", "list_pages", "select_page",
        "wait_for", "snapshot", "console", "network", "screenshot", "performance_trace"
    }
    nav_actions = {"navigate", "new_page", "hover"}

    if action in read_only_actions or action in nav_actions:
        return ("allow", None)
    if action == "call" and any(k in mcp_tool for k in ["snapshot", "screenshot", "list", "get", "navigate"]):
        return ("allow", None)

    return (
        "deny",
        "BLOCKED [Degraded Mode]: Effect Firewall unavailable; browser mutation cannot be safely effect-classified in degraded safety mode."
    )

def handle_degraded_mode(
    tool_type: str,
    tool_name: str,
    args: Dict[str, Any],
    err_msg: str
) -> Tuple[str, Optional[str]]:
    """
    Fail-Safe Degraded Mode Decision:
    - ALLOW low-risk read-only tools and benign navigation.
    - Classify browser actions specifically: read-only/nav ALLOWED; mutative DENIED.
    - DENY high-impact mutations (clicks, commits, deletes, purchases, external communications).
    """
    # Browser action specific classification in degraded mode
    if tool_name == "browser":
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from effect_taxonomy import classify_browser_action_degraded
            dec, reason = classify_browser_action_degraded(args)
        except Exception:
            dec, reason = fallback_classify_browser_degraded(args)

        log_degraded_event("effect_taxonomy", err_msg, f"browser::{args.get('action')}", dec)
        return (dec, reason)

    # Pure observation is allowed for non-browser observation tools
    if tool_name in READ_ONLY_PEEKABOO_TOOLS:
        log_degraded_event("effect_firewall", err_msg, tool_name, "allow")
        return ("allow", None)

    # Low-risk navigation
    if tool_name == "scroll" or (tool_name == "app" and args.get("action") in ["list", "focus", "switch"]):
        log_degraded_event("effect_firewall", err_msg, tool_name, "allow")
        return ("allow", None)

    # High-impact mutations are hard denied in degraded mode
    log_degraded_event("effect_firewall", err_msg, tool_name, "deny")
    return (
        "deny",
        f"BLOCKED [Degraded Mode]: Effect Firewall unavailable; high-impact mutation '{tool_name}' denied in degraded safety mode."
    )

def process_hook_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main PreToolUse router:
    1. Fast-path check for unrelated/native tools.
    2. Physical guardrail check.
    3. Advanced Effect Firewall check with task isolation & degraded fallback.
    """
    tool_call = payload.get("toolCall", {})
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args", {})
    conv_id = (
        payload.get("conversationId") or
        payload.get("conversation_id") or
        os.environ.get("ANTIGRAVITY_CONVERSATION_ID") or
        "default"
    )
    task_id = (
        payload.get("taskId") or
        payload.get("task_id") or
        os.environ.get("ANTIGRAVITY_TASK_ID") or
        None
    )

    # --- FAST PATH 1: Unrelated Native Tools ---
    if tool_name in NATIVE_FASTPATH_TOOLS:
        return {"decision": "allow"}

    # --- FAST PATH 2: Non-Peekaboo MCP Tools ---
    if tool_name == "call_mcp_tool":
        server = args.get("ServerName", "").lower()
        if server != "peekaboo":
            return {"decision": "allow"}

    # --- FAST PATH 3: Benign Developer Shell Commands ---
    if tool_name == "run_command":
        cmd = args.get("CommandLine", "")
        cmd_lower = cmd.lower()
        has_gui = any(ind in cmd_lower for ind in GUI_AUTOMATION_INDICATORS)
        if not has_gui:
            return {"decision": "allow"}

    # Identify Computer Use tool and arguments
    mcp_tool = ""
    mcp_args = {}
    is_cli_run = False

    if tool_name == "call_mcp_tool":
        mcp_tool = args.get("ToolName", "")
        mcp_args = args.get("Arguments", {})
    elif tool_name.startswith("mcp_peekaboo_"):
        mcp_tool = tool_name.replace("mcp_peekaboo_", "")
        mcp_args = args
    elif tool_name == "run_command":
        is_cli_run = True
        mcp_tool = "run_command"
        mcp_args = args
    else:
        return {"decision": "allow"}

    # Step 1: Physical / Concurrency Safety Guardrails (Always active)
    if is_cli_run:
        decision, reason = inspect_cli_physical_safety(mcp_args.get("CommandLine", ""))
    else:
        decision, reason = inspect_peekaboo_physical_safety(mcp_tool, mcp_args)

    if decision != "allow":
        return {"decision": decision, "reason": reason}

    # Step 2: Load Advanced Effect Firewall (with Fail-Safe Degraded Mode)
    force_degraded = bool(os.environ.get("SIMULATE_FIREWALL_FAILURE") or os.environ.get("ANTIGRAVITY_FIREWALL_FORCE_DEGRADED"))
    if force_degraded:
        decision, reason = handle_degraded_mode(tool_name, mcp_tool, mcp_args, "Simulated module failure via environment flag")
        return {"decision": decision, "reason": reason}

    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from effect_taxonomy import classify_action_risk, inspect_shell_bypass
        from effect_firewall import pre_tool_firewall_check

        decision, reason = pre_tool_firewall_check(mcp_tool, mcp_args, conv_id=conv_id, task_id=task_id)
    except Exception as exc:
        decision, reason = handle_degraded_mode(tool_name, mcp_tool, mcp_args, f"Import/Execution Error: {exc}")

    # Audit logging
    try:
        with open(PREHOOK_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ')}] tool={tool_name}/{mcp_tool} conv={conv_id} task={task_id} decision={decision} reason={reason}\n")
    except Exception:
        pass

    response = {"decision": decision}
    if reason:
        response["reason"] = reason
    return response

def process_post_tool_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Process PostToolUse hook payload and update firewall state."""
    tool_call = payload.get("toolCall", {})
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args", {})
    error = payload.get("error")
    conv_id = (
        payload.get("conversationId") or
        payload.get("conversation_id") or
        os.environ.get("ANTIGRAVITY_CONVERSATION_ID") or
        "default"
    )
    task_id = (
        payload.get("taskId") or
        payload.get("task_id") or
        os.environ.get("ANTIGRAVITY_TASK_ID") or
        None
    )

    if tool_name in NATIVE_FASTPATH_TOOLS:
        return {}

    mcp_tool = ""
    mcp_args = {}
    if tool_name == "call_mcp_tool":
        server = args.get("ServerName", "").lower()
        if server == "peekaboo":
            mcp_tool = args.get("ToolName", "")
            mcp_args = args.get("Arguments", {})
    elif tool_name.startswith("mcp_peekaboo_"):
        mcp_tool = tool_name.replace("mcp_peekaboo_", "")
        mcp_args = args
    elif tool_name == "run_command":
        cmd = args.get("CommandLine", "")
        if any(ind in cmd.lower() for ind in GUI_AUTOMATION_INDICATORS):
            mcp_tool = "run_command"
            mcp_args = args

    if mcp_tool:
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from effect_firewall import post_tool_firewall_update
            post_tool_firewall_update(mcp_tool, mcp_args, error, conv_id=conv_id, task_id=task_id)
        except Exception as e:
            log_degraded_event("effect_firewall_post", str(e), mcp_tool, "post_update_failed")

    return {}

def main():
    if len(sys.argv) > 1:
        subcmd = sys.argv[1]
        if subcmd == "post":
            pass
        elif subcmd == "contract":
            # safe_interact.py contract <goal> <auth_json> [forb_json] [risk_level] [conv_id] [task_id] [provenance] [target_scope_json]
            goal = sys.argv[2]
            auth = json.loads(sys.argv[3])
            forb = json.loads(sys.argv[4]) if len(sys.argv) > 4 else []
            risk = sys.argv[5] if len(sys.argv) > 5 else "standard"
            conv_id = sys.argv[6] if len(sys.argv) > 6 else "default"
            task_id = sys.argv[7] if len(sys.argv) > 7 else None
            prov = sys.argv[8] if len(sys.argv) > 8 else "user"
            tgt_scope = json.loads(sys.argv[9]) if len(sys.argv) > 9 else {}
            from effect_firewall import init_task_contract
            ok, res, err = init_task_contract(
                goal, auth, forb, risk_level=risk, target_scope=tgt_scope,
                provenance=prov, conv_id=conv_id, task_id=task_id
            )
            print(json.dumps({"success": ok, "state": res, "error": err}, indent=2))
            sys.exit(0 if ok else 1)
        elif subcmd == "auto_contract":
            # safe_interact.py auto_contract <intent_text> [conv_id] [task_id]
            intent = sys.argv[2]
            conv_id = sys.argv[3] if len(sys.argv) > 3 else "default"
            task_id = sys.argv[4] if len(sys.argv) > 4 else None
            from effect_firewall import auto_create_contract_from_intent
            res = auto_create_contract_from_intent(intent, conv_id=conv_id, task_id=task_id)
            print(json.dumps(res, indent=2))
            sys.exit(0)
        elif subcmd == "receipt":
            # safe_interact.py receipt <effect> <target> [app] [conv_id] [task_id]
            eff = sys.argv[2]
            tgt = sys.argv[3]
            app = sys.argv[4] if len(sys.argv) > 4 else ""
            conv_id = sys.argv[5] if len(sys.argv) > 5 else "default"
            task_id = sys.argv[6] if len(sys.argv) > 6 else None
            from effect_firewall import issue_commit_receipt
            rcpt = issue_commit_receipt(eff, tgt, app=app, conv_id=conv_id, task_id=task_id)
            print(json.dumps(rcpt, indent=2))
            sys.exit(0)
        elif subcmd == "recovery":
            reason = sys.argv[2] if len(sys.argv) > 2 else "Manual recovery trigger"
            conv_id = sys.argv[3] if len(sys.argv) > 3 else "default"
            task_id = sys.argv[4] if len(sys.argv) > 4 else None
            from effect_firewall import trigger_recovery_mode
            trigger_recovery_mode(reason, conv_id=conv_id, task_id=task_id)
            print(f"Recovery mode activated for ({conv_id}, {task_id}): {reason}")
            sys.exit(0)
        elif subcmd == "resolve":
            conv_id = sys.argv[2] if len(sys.argv) > 2 else "default"
            task_id = sys.argv[3] if len(sys.argv) > 3 else None
            from effect_firewall import resolve_recovery_mode
            resolve_recovery_mode(conv_id=conv_id, task_id=task_id)
            print(f"Recovery mode resolved for ({conv_id}, {task_id}).")
            sys.exit(0)
        elif subcmd == "status":
            conv_id = sys.argv[2] if len(sys.argv) > 2 else "default"
            task_id = sys.argv[3] if len(sys.argv) > 3 else None
            from effect_firewall import load_firewall_state
            print(json.dumps(load_firewall_state(conv_id=conv_id, task_id=task_id), indent=2))
            sys.exit(0)

    if sys.stdin.isatty():
        print("Safe Computer Use Interaction Guardrail & Effect Firewall ready.")
        sys.exit(0)

    try:
        raw = sys.stdin.read()
        if not raw.strip():
            print(json.dumps({}))
            sys.exit(0)

        payload = json.loads(raw)
        if len(sys.argv) > 1 and sys.argv[1] == "post":
            result = process_post_tool_payload(payload)
        else:
            result = process_hook_payload(payload)
        print(json.dumps(result))
        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"[SafeHook Bootstrap Error]: {e}\n")
        print(json.dumps({"decision": "deny", "reason": "Protection exception: fail closed"}))
        sys.exit(0)

if __name__ == "__main__":
    main()
