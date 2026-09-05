#!/usr/bin/env python3
"""
effect_firewall.py — Computer Use Intent / Effect Firewall State Machine.

Maintains:
1. True Task-Level Isolation: Security state, contracts, budgets, receipts, and recovery
   modes are scoped strictly to (conversation_id, task_id) under /tmp/antigravity-effect-firewall/<conv>/tasks/<task>/.
2. Monotonic Authorization Engine: Prevents silent privilege escalation (NEW AUTHORITY ⊆ USER AUTHORITY).
   - Agent can narrow scope, reduce budget, or strengthen constraints autonomously.
   - Agent CANNOT add Level 4/5 effects, increase budgets, or broaden targets without user authorization.
3. Target-bound predicate verification (observe != verify, target binding).
4. Reentrant process-level and OS-level locking (fcntl.flock).
5. Single-use commit receipts with atomic consumption.
"""

import sys
import os
import json
import time
import re
import uuid
import fcntl
import tempfile
from contextlib import contextmanager
from typing import Dict, Any, Optional, Tuple, List

# Ensure local imports work reliably
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from effect_taxonomy import (
    EffectLevel,
    classify_action_risk,
    evaluate_semantic_alignment,
    is_unknown_high_impact_control,
    inspect_shell_bypass,
    classify_browser_action_degraded
)

BASE_STATE_DIR = "/tmp/antigravity-effect-firewall"
AUDIT_LOG_PATH = "/tmp/computer_use_firewall.log"

HIGH_IMPACT_EFFECT_PREFIXES = (
    "communication.", "destructive.", "financial.", "external."
)

DEFAULT_STATE: Dict[str, Any] = {
    "task_id": "default_task",
    "conversation_id": "default",
    "user_authority": {
        "goal": "general.task",
        "authorized_effects": {}, # { effect_name: max_allowed }
        "forbidden_effects": [],
        "target_scope": {},       # { effect_name: allowed_target }
        "risk_level": "standard",
        "provenance": "user",
        "authorized_at": 0
    },
    "contract": {
        "goal": "general.task",
        "authorized_effects": {},
        "forbidden_effects": [],
        "target_scope": {},
        "risk_level": "standard"
    },
    "state": "IDLE",               # IDLE | VERIFICATION_REQUIRED | RECOVERY_MODE
    "verification_required": False,
    "verification_status": "NONE", # NONE | PENDING | VERIFIED | SKIPPED_UNRELATED | FAILED
    "last_mutation": None,
    "recovery_reason": None,
    "budgets": {},                 # { effect_name: { limit: int, used: int } }
    "active_receipts": {},         # { receipt_id: { ... } }
    "created_at": 0,
    "updated_at": 0
}

# Reentrant process-level lock tracking per (conv_id, task_id)
_TASK_LOCKS: Dict[str, Dict[str, Any]] = {}

def sanitize_id(identifier: Optional[str], default: str = "default") -> str:
    """Sanitize identifier for safe filesystem path."""
    if not identifier or not str(identifier).strip():
        return default
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', str(identifier).strip())

def get_active_task_id(conv_id: Optional[str] = None) -> str:
    """Read current active task ID for a conversation session."""
    safe_conv = sanitize_id(conv_id, "default")
    active_file = os.path.join(BASE_STATE_DIR, safe_conv, "active_task.txt")
    if os.path.exists(active_file):
        try:
            with open(active_file, "r", encoding="utf-8") as f:
                tid = f.read().strip()
                if tid:
                    return tid
        except Exception:
            pass
    return "default_task"

def set_active_task_id(conv_id: Optional[str], task_id: str) -> None:
    """Record current active task ID for a conversation session."""
    safe_conv = sanitize_id(conv_id, "default")
    conv_dir = os.path.join(BASE_STATE_DIR, safe_conv)
    os.makedirs(conv_dir, exist_ok=True)
    active_file = os.path.join(conv_dir, "active_task.txt")
    try:
        with open(active_file, "w", encoding="utf-8") as f:
            f.write(sanitize_id(task_id, "default_task"))
    except Exception:
        pass

def get_task_dir(conv_id: Optional[str] = None, task_id: Optional[str] = None) -> str:
    """Return isolated directory for specific conversation + task."""
    safe_conv = sanitize_id(conv_id, "default")
    safe_task = sanitize_id(task_id or get_active_task_id(conv_id), "default_task")
    task_dir = os.path.join(BASE_STATE_DIR, safe_conv, "tasks", safe_task)
    os.makedirs(task_dir, exist_ok=True)
    return task_dir

def get_state_path(conv_id: Optional[str] = None, task_id: Optional[str] = None) -> str:
    return os.path.join(get_task_dir(conv_id, task_id), "state.json")

def get_lock_path(conv_id: Optional[str] = None, task_id: Optional[str] = None) -> str:
    return os.path.join(get_task_dir(conv_id, task_id), "state.lock")

@contextmanager
def lock_state(conv_id: Optional[str] = None, task_id: Optional[str] = None):
    """
    Reentrant context manager acquiring an exclusive OS lock on specific task state.
    Strictly isolates concurrent tasks and processes.
    """
    safe_conv = sanitize_id(conv_id, "default")
    safe_task = sanitize_id(task_id or get_active_task_id(conv_id), "default_task")
    lock_key = f"{safe_conv}::{safe_task}"

    if lock_key not in _TASK_LOCKS:
        _TASK_LOCKS[lock_key] = {"depth": 0, "fd": None}

    entry = _TASK_LOCKS[lock_key]
    if entry["depth"] == 0:
        lock_path = get_lock_path(conv_id, safe_task)
        fd = open(lock_path, "w")
        fcntl.flock(fd, fcntl.LOCK_EX)
        entry["fd"] = fd

    entry["depth"] += 1
    try:
        yield
    finally:
        entry["depth"] -= 1
        if entry["depth"] == 0:
            if entry["fd"] is not None:
                try:
                    fcntl.flock(entry["fd"], fcntl.LOCK_UN)
                except Exception:
                    pass
                try:
                    entry["fd"].close()
                except Exception:
                    pass
                entry["fd"] = None

def load_firewall_state(conv_id: Optional[str] = None, task_id: Optional[str] = None) -> Dict[str, Any]:
    """Load current firewall state for specific conversation + task."""
    state_path = get_state_path(conv_id, task_id)
    safe_conv = sanitize_id(conv_id, "default")
    safe_task = sanitize_id(task_id or get_active_task_id(conv_id), "default_task")

    if not os.path.exists(state_path):
        fresh = json.loads(json.dumps(DEFAULT_STATE))
        fresh["conversation_id"] = safe_conv
        fresh["task_id"] = safe_task
        fresh["created_at"] = time.time()
        fresh["updated_at"] = time.time()
        return fresh
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        fresh = json.loads(json.dumps(DEFAULT_STATE))
        fresh["conversation_id"] = safe_conv
        fresh["task_id"] = safe_task
        return fresh

def save_firewall_state(state: Dict[str, Any], conv_id: Optional[str] = None, task_id: Optional[str] = None) -> None:
    """Safely persist state using atomic file replacement within task dir."""
    safe_conv = sanitize_id(conv_id, "default")
    safe_task = sanitize_id(task_id or state.get("task_id"), "default_task")
    task_dir = get_task_dir(safe_conv, safe_task)
    state_path = get_state_path(safe_conv, safe_task)
    state["updated_at"] = time.time()

    try:
        fd, temp_path = tempfile.mkstemp(dir=task_dir, prefix="fw_state_", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        os.replace(temp_path, state_path)
    except Exception as e:
        sys.stderr.write(f"[FirewallState Error]: Failed to save state for ({safe_conv}, {safe_task}): {e}\n")

def audit_log(event: Dict[str, Any], conv_id: Optional[str] = None, task_id: Optional[str] = None) -> None:
    """Append structured JSON audit event without sensitive payload content."""
    try:
        event["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        event["conversation_id"] = sanitize_id(conv_id, "default")
        event["task_id"] = sanitize_id(task_id or get_active_task_id(conv_id), "default_task")
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception:
        pass

# ----------------- MONOTONIC AUTHORIZATION LOGIC -----------------

def is_high_impact_effect(effect_name: str) -> bool:
    """Check if an effect category represents a Level 4 or Level 5 high-impact action."""
    return any(effect_name.startswith(p) for p in HIGH_IMPACT_EFFECT_PREFIXES)

def is_target_narrowing_or_equal(user_target: Any, agent_target: Any) -> bool:
    """
    Validate that agent_target is equal to or a strictly narrower subset of user_target.
    Returns True if valid narrowing or equal; False if broadening.
    """
    if user_target is None or user_target == "" or user_target == "*":
        return True

    if agent_target is None or agent_target == "":
        return True

    user_str = str(user_target).strip().lower()
    agent_str = str(agent_target).strip().lower()

    if agent_str == user_str:
        return True

    # Broadening to wildcard or all is strictly forbidden
    if agent_str in ["*", "all", "any"] and user_str not in ["*", "all", "any"]:
        return False

    # Check set membership (comma/space separated lists)
    user_items = set(x.strip() for x in re.split(r'[,;|\s]+', user_str) if x.strip())
    agent_items = set(x.strip() for x in re.split(r'[,;|\s]+', agent_str) if x.strip())
    if agent_items and user_items and agent_items.issubset(user_items):
        return True

    # Check path prefix / directory narrowing (e.g., /tmp/mock_folder/ -> /tmp/mock_folder/file.txt)
    clean_user = user_str.rstrip('*').rstrip('/')
    if agent_str.startswith(clean_user + "/") or agent_str.startswith(clean_user + "_"):
        return True

    # Check conversation / thread sub-scope narrowing (e.g., conversation_A -> conversation_A/thread_1)
    if agent_str.startswith(user_str + "/") or agent_str.startswith(user_str + ":") or agent_str.startswith(user_str + "_"):
        return True

    return False

def validate_monotonic_contract_update(
    existing_state: Dict[str, Any],
    new_auth: Dict[str, int],
    new_forb: List[str],
    new_target_scope: Dict[str, Any],
    provenance: str
) -> Tuple[bool, Optional[str]]:
    """
    Enforce monotonic authorization: Agent may narrow authority, but may NOT silently expand
    high-impact (Level 4/5) authority without explicit user authorization.
    Returns (is_valid, rejection_reason).
    """
    # User-originated authorization is the source of truth; user can always expand or update
    if provenance == "user":
        return (True, None)

    user_auth = existing_state.get("user_authority", {})
    user_allowed = user_auth.get("authorized_effects", {})
    user_forbidden = set(user_auth.get("forbidden_effects", []))
    user_targets = user_auth.get("target_scope", {})

    # Rule 1: Agent CANNOT add new Level 4/5 effects not authorized by the user
    for eff in new_auth:
        if is_high_impact_effect(eff):
            if eff not in user_allowed:
                return (
                    False,
                    f"Monotonicity Violation: Agent cannot autonomously add new Level 4/5 effect '{eff}' without user authorization."
                )

    # Rule 2: Agent CANNOT increase budgets beyond the user-authorized maximum
    for eff, limit in new_auth.items():
        if is_high_impact_effect(eff):
            user_max = user_allowed.get(eff, 0)
            if limit > user_max:
                return (
                    False,
                    f"Monotonicity Violation: Agent cannot autonomously increase budget for '{eff}' from {user_max} to {limit}."
                )

    # Rule 3: Agent CANNOT broaden target scopes beyond user-authorized bounds
    for eff, agent_tgt in new_target_scope.items():
        if is_high_impact_effect(eff) and eff in user_targets:
            user_tgt = user_targets[eff]
            if not is_target_narrowing_or_equal(user_tgt, agent_tgt):
                return (
                    False,
                    f"Monotonicity Violation: Agent cannot broaden target scope for '{eff}' from '{user_tgt}' to '{agent_tgt}'."
                )

    # Rule 4: Agent CANNOT un-forbid effects that the user explicitly prohibited
    new_forb_set = set(new_forb)
    for forb_eff in user_forbidden:
        if forb_eff not in new_forb_set:
            return (
                False,
                f"Monotonicity Violation: Agent cannot remove user-forbidden effect '{forb_eff}' from contract constraints."
            )

    return (True, None)

# ----------------- CONTRACT & TASK MANAGEMENT -----------------

def init_task_contract(
    goal: str,
    authorized_effects: Dict[str, int],
    forbidden_effects: Optional[List[str]] = None,
    risk_level: str = "standard",
    target_scope: Optional[Dict[str, Any]] = None,
    provenance: str = "user",
    conv_id: Optional[str] = None,
    task_id: Optional[str] = None
) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    """
    Initialize or update Task Effect Contract with monotonic authorization validation
    and strict task-level state isolation.
    Returns (success, state, error_message).
    """
    safe_conv = sanitize_id(conv_id, "default")
    safe_task = sanitize_id(task_id, f"task_{int(time.time())}")
    target_scope = target_scope or {}
    forbidden_effects = forbidden_effects or []

    with lock_state(safe_conv, safe_task):
        state = load_firewall_state(safe_conv, safe_task)

        # Monotonicity check against existing user authority if updated autonomously by agent
        if state.get("user_authority", {}).get("authorized_at", 0) > 0:
            is_valid, reason = validate_monotonic_contract_update(
                state, authorized_effects, forbidden_effects, target_scope, provenance
            )
            if not is_valid:
                audit_log({
                    "event": "monotonic_contract_update_rejected",
                    "reason": reason,
                    "proposed_goal": goal,
                    "provenance": provenance
                }, safe_conv, safe_task)
                return False, state, reason

        # Update authority baseline if user-authorized
        if provenance == "user":
            state["user_authority"] = {
                "goal": goal,
                "authorized_effects": authorized_effects.copy(),
                "forbidden_effects": list(forbidden_effects),
                "target_scope": target_scope.copy(),
                "risk_level": risk_level,
                "provenance": "user",
                "authorized_at": time.time()
            }

        # Apply active contract
        state["task_id"] = safe_task
        state["conversation_id"] = safe_conv
        state["contract"] = {
            "goal": goal,
            "authorized_effects": authorized_effects.copy(),
            "forbidden_effects": list(forbidden_effects),
            "target_scope": target_scope.copy(),
            "risk_level": risk_level
        }
        state["state"] = "IDLE"
        state["verification_required"] = False
        state["verification_status"] = "NONE"
        state["recovery_reason"] = None
        state["last_mutation"] = None

        # Recompute budgets respecting used count if effect existed
        new_budgets = {}
        old_budgets = state.get("budgets", {})
        for eff, limit in authorized_effects.items():
            used = old_budgets.get(eff, {}).get("used", 0) if provenance != "user" else 0
            new_budgets[eff] = {"limit": limit, "used": used}
        state["budgets"] = new_budgets

        set_active_task_id(safe_conv, safe_task)
        save_firewall_state(state, safe_conv, safe_task)

        audit_log({
            "event": "contract_initialized",
            "goal": goal,
            "authorized_effects": authorized_effects,
            "forbidden_effects": forbidden_effects,
            "target_scope": target_scope,
            "provenance": provenance
        }, safe_conv, safe_task)

        return True, state, None

def auto_create_contract_from_intent(
    intent: str,
    target_scope: Optional[Dict[str, Any]] = None,
    conv_id: Optional[str] = None,
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """Derive user-authorized Task Effect Contract automatically from natural language intent."""
    intent_lower = intent.lower()

    if any(k in intent_lower for k in ["send text", "send message", "text message", "chat message"]):
        scope = target_scope or {"communication.send_text": "mock_chat"}
        _, state, _ = init_task_contract(
            goal="communication.send_text",
            authorized_effects={"communication.send_text": 1},
            forbidden_effects=["communication.send_voice", "communication.send_file", "communication.call"],
            risk_level="standard",
            target_scope=scope,
            provenance="user",
            conv_id=conv_id,
            task_id=task_id
        )
        return state
    elif any(k in intent_lower for k in ["voice message", "send voice", "audio note", "record audio"]):
        scope = target_scope or {"communication.send_voice": "mock_chat"}
        _, state, _ = init_task_contract(
            goal="communication.send_voice",
            authorized_effects={"communication.send_voice": 1},
            forbidden_effects=["communication.send_text", "communication.send_file"],
            risk_level="standard",
            target_scope=scope,
            provenance="user",
            conv_id=conv_id,
            task_id=task_id
        )
        return state
    elif any(k in intent_lower for k in ["delete", "remove item", "trash"]):
        scope = target_scope or {"destructive.delete": "mock_item"}
        _, state, _ = init_task_contract(
            goal="destructive.delete",
            authorized_effects={"destructive.delete": 1},
            forbidden_effects=["financial.purchase", "communication.send_text"],
            risk_level="destructive",
            target_scope=scope,
            provenance="user",
            conv_id=conv_id,
            task_id=task_id
        )
        return state
    elif any(k in intent_lower for k in ["purchase", "buy", "pay", "checkout"]):
        scope = target_scope or {"financial.purchase": "mock_cart"}
        _, state, _ = init_task_contract(
            goal="financial.purchase",
            authorized_effects={"financial.purchase": 1},
            forbidden_effects=["destructive.delete"],
            risk_level="financial",
            target_scope=scope,
            provenance="user",
            conv_id=conv_id,
            task_id=task_id
        )
        return state
    else:
        _, state, _ = init_task_contract(
            goal="general.exploration",
            authorized_effects={},
            forbidden_effects=["destructive.delete", "financial.purchase", "communication.send_voice"],
            risk_level="standard",
            target_scope={},
            provenance="user",
            conv_id=conv_id,
            task_id=task_id
        )
        return state

# ----------------- RECOVERY & RECEIPTS -----------------

def trigger_recovery_mode(reason: str, conv_id: Optional[str] = None, task_id: Optional[str] = None) -> None:
    """Transition specific task into RECOVERY_MODE without affecting other tasks."""
    safe_conv = sanitize_id(conv_id, "default")
    safe_task = sanitize_id(task_id or get_active_task_id(conv_id), "default_task")

    with lock_state(safe_conv, safe_task):
        state = load_firewall_state(safe_conv, safe_task)
        state["state"] = "RECOVERY_MODE"
        state["recovery_reason"] = reason
        state["verification_status"] = "FAILED"
        save_firewall_state(state, safe_conv, safe_task)
        audit_log({
            "event": "recovery_triggered",
            "reason": reason
        }, safe_conv, safe_task)

def resolve_recovery_mode(conv_id: Optional[str] = None, task_id: Optional[str] = None) -> None:
    """Clear RECOVERY_MODE for specific task after safe state verification."""
    safe_conv = sanitize_id(conv_id, "default")
    safe_task = sanitize_id(task_id or get_active_task_id(conv_id), "default_task")

    with lock_state(safe_conv, safe_task):
        state = load_firewall_state(safe_conv, safe_task)
        state["state"] = "IDLE"
        state["recovery_reason"] = None
        state["verification_required"] = False
        state["verification_status"] = "VERIFIED"
        save_firewall_state(state, safe_conv, safe_task)
        audit_log({
            "event": "recovery_resolved"
        }, safe_conv, safe_task)

def issue_commit_receipt(
    effect: str,
    target: str,
    app: str = "",
    window: str = "",
    snapshot_id: str = "",
    ttl_seconds: int = 30,
    conv_id: Optional[str] = None,
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """Generate a single-use commit receipt bound strictly to (conv_id, task_id)."""
    safe_conv = sanitize_id(conv_id, "default")
    safe_task = sanitize_id(task_id or get_active_task_id(conv_id), "default_task")

    with lock_state(safe_conv, safe_task):
        state = load_firewall_state(safe_conv, safe_task)
        receipt_id = f"rcpt_{uuid.uuid4().hex[:12]}"
        receipt = {
            "receipt_id": receipt_id,
            "conversation_id": safe_conv,
            "task_id": safe_task,
            "effect": effect,
            "app": app,
            "window": window,
            "target": target,
            "snapshot_id": snapshot_id,
            "created_at": time.time(),
            "expires_at": time.time() + ttl_seconds,
            "used": False
        }
        if "active_receipts" not in state:
            state["active_receipts"] = {}
        state["active_receipts"][receipt_id] = receipt
        save_firewall_state(state, safe_conv, safe_task)
        audit_log({
            "event": "receipt_issued",
            "receipt_id": receipt_id,
            "effect": effect,
            "target": target,
            "app": app
        }, safe_conv, safe_task)
        return receipt

def consume_commit_receipt(
    effect: str,
    target: str,
    app: str = "",
    receipt_id: Optional[str] = None,
    conv_id: Optional[str] = None,
    task_id: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Atomically consume a single-use commit receipt strictly within the task boundary.
    Cross-task consumption attempts fail immediately.
    """
    safe_conv = sanitize_id(conv_id, "default")
    safe_task = sanitize_id(task_id or get_active_task_id(conv_id), "default_task")

    with lock_state(safe_conv, safe_task):
        state = load_firewall_state(safe_conv, safe_task)
        receipts = state.get("active_receipts", {})

        target_receipt = None
        target_rcpt_id = receipt_id

        if target_rcpt_id and target_rcpt_id in receipts:
            target_receipt = receipts[target_rcpt_id]
        else:
            now = time.time()
            for r_id, r in receipts.items():
                if not r.get("used", False) and r.get("expires_at", 0) >= now:
                    if r.get("effect") == effect:
                        if not target or r.get("target") == target:
                            target_receipt = r
                            target_rcpt_id = r_id
                            break

        if not target_receipt:
            return False, "No valid active commit receipt found for proposed effect"

        if target_receipt.get("used", False):
            return False, "Commit receipt has already been consumed (single-use barrier)"

        if time.time() > target_receipt.get("expires_at", 0):
            return False, "Commit receipt has expired"

        # Task and session binding verification
        if target_receipt.get("task_id") != safe_task or target_receipt.get("conversation_id") != safe_conv:
            return False, "Commit receipt belongs to a different task or conversation session"

        if target_receipt.get("effect") != effect:
            return False, f"Commit receipt authorizes '{target_receipt.get('effect')}', not '{effect}'"

        if target_receipt.get("app") and app and target_receipt.get("app").lower() != app.lower():
            return False, f"Commit receipt bound to app '{target_receipt.get('app')}', not '{app}'"

        # Atomically consume
        target_receipt["used"] = True
        target_receipt["consumed_at"] = time.time()
        receipts[target_rcpt_id] = target_receipt
        state["active_receipts"] = receipts
        save_firewall_state(state, safe_conv, safe_task)

        audit_log({
            "event": "receipt_consumed",
            "receipt_id": target_rcpt_id,
            "effect": effect,
            "target": target
        }, safe_conv, safe_task)
        return True, None

# ----------------- PRE/POST FIREWALL CHECKS -----------------

def pre_tool_firewall_check(
    tool_name: str,
    args: Dict[str, Any],
    target_meta: Optional[Dict[str, str]] = None,
    conv_id: Optional[str] = None,
    task_id: Optional[str] = None
) -> Tuple[str, Optional[str]]:
    """
    Main PreToolUse firewall evaluation scoped strictly to (conv_id, task_id).
    """
    safe_conv = sanitize_id(conv_id, "default")
    safe_task = sanitize_id(task_id or get_active_task_id(conv_id), "default_task")

    with lock_state(safe_conv, safe_task):
        state = load_firewall_state(safe_conv, safe_task)
        current_mode = state.get("state", "IDLE")
        contract = state.get("contract", {})
        budgets = state.get("budgets", {})
        target_meta = target_meta or {}

        # Shell bypass inspection
        if tool_name == "run_command":
            cmd = args.get("CommandLine", "")
            is_bypass, level, effect_cat, details = inspect_shell_bypass(cmd)
            if is_bypass:
                tool_name = "click" if "click" in cmd.lower() else "press"
                args = {"on": details or "", "keys": ["Return"] if "return" in cmd.lower() else []}
            else:
                return ("allow", None)

        level, effect_category = classify_action_risk(tool_name, args)

        # Extract target identifiers
        target_id = str(args.get("on", "")) or str(args.get("uid", "")) or str(target_meta.get("identifier", ""))
        target_label = str(args.get("query", "")) or str(args.get("text", "")) or str(target_meta.get("label", "")) or str(args.get("button", ""))
        target_help = str(target_meta.get("help", ""))
        app_target = str(args.get("app", "") or args.get("app_target", ""))

        # 1. Recovery Mode Gating
        if current_mode == "RECOVERY_MODE":
            is_recovery_action = (
                level == EffectLevel.LEVEL_0_OBSERVATION or
                any(w in f"{target_id} {target_label} {target_help}".lower() for w in ["cancel", "undo", "stop", "close", "back", "abort", "dismiss"]) or
                (tool_name == "press" and any(k in ["escape", "esc"] for k in args.get("keys", [])))
            )
            if not is_recovery_action:
                audit_log({
                    "decision": "deny",
                    "rule": "recovery_mode",
                    "tool": tool_name,
                    "reason": state.get("recovery_reason")
                }, safe_conv, safe_task)
                return (
                    "deny",
                    f"BLOCKED [Firewall Recovery Mode]: Task in recovery mode ({state.get('recovery_reason')}). "
                    "Only observation, cancel, undo, or safe recovery actions are permitted until safe baseline is restored."
                )

        # 2. Mutation Barrier & Target-Bound Verification
        if state.get("verification_required", False):
            last_mut = state.get("last_mutation", {})
            mut_app = str(last_mut.get("app", "")).strip().lower()

            if level == EffectLevel.LEVEL_0_OBSERVATION:
                obs_app = str(args.get("app", "") or args.get("app_target", "") or args.get("process", "")).strip().lower()

                # Unrelated app observation does NOT clear barrier
                if obs_app and mut_app and obs_app != mut_app:
                    state["verification_status"] = "SKIPPED_UNRELATED"
                    save_firewall_state(state, safe_conv, safe_task)
                    audit_log({
                        "event": "verification_skipped_unrelated_target",
                        "obs_app": obs_app,
                        "mut_app": mut_app
                    }, safe_conv, safe_task)
                    return ("allow", None)

                # Bound observation: evaluate expected state
                has_conflict = (
                    args.get("conflict_detected", False) or
                    args.get("recording_active", False) or
                    "recording active" in str(args).lower() or
                    "unexpected" in str(args).lower()
                )
                if has_conflict:
                    state["state"] = "RECOVERY_MODE"
                    state["recovery_reason"] = f"Conflict detected: unexpected state following {last_mut.get('effect')}"
                    state["verification_status"] = "FAILED"
                    save_firewall_state(state, safe_conv, safe_task)
                    audit_log({
                        "event": "recovery_triggered",
                        "reason": state["recovery_reason"]
                    }, safe_conv, safe_task)
                    return ("allow", None)
                else:
                    state["verification_required"] = False
                    state["verification_status"] = "VERIFIED"
                    save_firewall_state(state, safe_conv, safe_task)
                    audit_log({
                        "event": "mutation_verified",
                        "last_mutation": last_mut
                    }, safe_conv, safe_task)
                    return ("allow", None)

            elif level >= EffectLevel.LEVEL_3_PERSISTENT_MUTATION:
                audit_log({
                    "decision": "deny",
                    "rule": "mutation_barrier",
                    "tool": tool_name,
                    "target": target_id
                }, safe_conv, safe_task)
                return (
                    "deny",
                    "BLOCKED [Mutation Barrier]: Verification required for previous mutation before attempting another "
                    "Level 3+ mutation. Observe the target UI state first to confirm expected outcome."
                )

        if level == EffectLevel.LEVEL_0_OBSERVATION:
            return ("allow", None)

        # 3. Fail-Closed on Unknown High-Impact Controls
        is_high_impact_task = (
            contract.get("risk_level") in ["destructive", "sensitive", "external", "financial"] or
            any(g.startswith(("destructive.", "financial.")) for g in [contract.get("goal", "")])
        )
        effective_level = EffectLevel.LEVEL_5_DESTRUCTIVE_SENSITIVE if is_high_impact_task else level

        if is_unknown_high_impact_control(effective_level, target_id, target_label):
            audit_log({
                "decision": "deny",
                "rule": "unknown_high_impact",
                "target": target_id
            }, safe_conv, safe_task)
            return (
                "deny",
                f"BLOCKED [Fail Closed]: Unknown or ambiguous control ('{target_id}') during high-impact "
                f"action/task. Semantic evidence is insufficient to guarantee authorized effects."
            )

        if level in [EffectLevel.LEVEL_1_NAVIGATION, EffectLevel.LEVEL_2_LOCAL_MUTATION]:
            return ("allow", None)

        # 4. Forbidden Effects
        forbidden = contract.get("forbidden_effects", [])
        if effect_category in forbidden:
            audit_log({
                "decision": "deny",
                "rule": "forbidden_effect",
                "effect": effect_category
            }, safe_conv, safe_task)
            return (
                "deny",
                f"BLOCKED [Authorized Effects Only]: Proposed effect '{effect_category}' is explicitly forbidden by the Task Effect Contract."
            )

        # 5. Semantic Alignment
        goal = contract.get("goal", "")
        is_aligned, mismatch_reason = evaluate_semantic_alignment(goal, target_id, target_label, target_help)
        if not is_aligned:
            audit_log({
                "decision": "deny",
                "rule": "semantic_mismatch",
                "intended": goal,
                "target": target_id,
                "reason": mismatch_reason
            }, safe_conv, safe_task)
            return ("deny", f"BLOCKED [Semantic Firewall]: {mismatch_reason}")

        # 6. Side-Effect Budgets
        if effect_category in budgets:
            budget_entry = budgets[effect_category]
            if budget_entry["used"] >= budget_entry["limit"]:
                audit_log({
                    "decision": "deny",
                    "rule": "budget_exhausted",
                    "effect": effect_category,
                    "used": budget_entry["used"],
                    "limit": budget_entry["limit"]
                }, safe_conv, safe_task)
                return (
                    "deny",
                    f"BLOCKED [Side-Effect Budget]: Budget exhausted for effect '{effect_category}' "
                    f"(limit: {budget_entry['limit']}, used: {budget_entry['used']}). "
                    "Prevents unintended duplicate actions or transmissions."
                )

        audit_log({
            "decision": "allow",
            "tool": tool_name,
            "level": int(level),
            "effect": effect_category,
            "target": target_id
        }, safe_conv, safe_task)
        return ("allow", None)

def post_tool_firewall_update(
    tool_name: str,
    args: Dict[str, Any],
    error: Optional[str] = None,
    conv_id: Optional[str] = None,
    task_id: Optional[str] = None
) -> None:
    """Process PostToolUse event to update budgets, commit barrier, and state machine."""
    safe_conv = sanitize_id(conv_id, "default")
    safe_task = sanitize_id(task_id or get_active_task_id(conv_id), "default_task")

    with lock_state(safe_conv, safe_task):
        state = load_firewall_state(safe_conv, safe_task)
        level, effect_category = classify_action_risk(tool_name, args)

        if level >= EffectLevel.LEVEL_3_PERSISTENT_MUTATION:
            app_target = str(args.get("app", "") or args.get("app_target", "") or "").strip()
            target_id = str(args.get("on", "") or args.get("uid", "") or args.get("button", "") or "")

            state["verification_required"] = True
            state["verification_status"] = "PENDING"
            state["last_mutation"] = {
                "tool": tool_name,
                "effect": effect_category,
                "target": target_id,
                "app": app_target,
                "timestamp": time.time(),
                "expected_predicates": {
                    "recording_active": False,
                    "no_unexpected_external_effect": True
                }
            }

            if not error and effect_category in state.get("budgets", {}):
                state["budgets"][effect_category]["used"] += 1

            save_firewall_state(state, safe_conv, safe_task)
            audit_log({
                "event": "mutation_dispatched",
                "tool": tool_name,
                "effect": effect_category,
                "budgets": state.get("budgets")
            }, safe_conv, safe_task)
