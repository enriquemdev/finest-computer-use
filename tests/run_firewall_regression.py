#!/usr/bin/env python3
"""
run_firewall_regression.py — Comprehensive Intent/Effect Firewall Regression Suite (v1 Freeze).

Covers 35 tests:
- Tests A–K: Foundation tests (Semantic mismatch, Adjacent effects, Budgets, Barrier,
  Recovery mode, Fail-closed, Exploration, Shell bypass, DOM classification, WhatsApp fixture).
- Test L: E2E Natural-Language Contract Generation.
- Test M: True E2E Mock UI Semantic Mismatch.
- Test N: True E2E Mutation Barrier + Unrelated vs Target-Bound Observation.
- Test O: True E2E Unexpected-State Recovery & Safe Baseline.
- Test P: Fail-Safe Degraded Mode (Anti-Brick + Anti-Fail-Open).
- Test Q: Multi-Session Concurrency Isolation.
- Test R: Daily Developer Autonomy & Zero Friction Preservation.
- Test S: Monotonic Authorization — Unauthorized Contract Expansion (New Level 4).
- Test T: Monotonic Authorization — Budget Expansion Blocked.
- Test U: Monotonic Authorization — Target Broadening Blocked.
- Test V: Monotonic Authorization — Authorized Target Narrowing Allowed.
- Test W: Monotonic Authorization — Explicit New User Authorization Allowed.
- Test X: True Task-Level Isolation — Same Conversation Multi-Task Independence.
- Test Y: True Task-Level Isolation — Cross-Task Receipt Theft Blocked.
- Test Z: True Task-Level Isolation — Cross-Task Verification Leak Blocked.
- Test AA: True Task-Level Isolation — Cross-Task Recovery Leak Blocked.
- Test AB: Degraded Browser — Read-Only Inspection Allowed.
- Test AC: Degraded Browser — Reversible Navigation Allowed.
- Test AD: Degraded Browser — Send Mutation Denied.
- Test AE: Degraded Browser — Purchase/Delete Mutation Denied.
- Test AF: Degraded Browser — Unknown Mutation Denied (Fail-Closed).
- True E2E Test 1: Full Monotonic Authorization Pipeline.
- True E2E Test 2: Full Same-Conversation Multi-Task Execution.
- True E2E Test 3: Full Degraded Browser Action-Level Classification.
"""

import sys
import os
import json
import subprocess
import time
import shutil

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_SRC = os.path.abspath(os.path.join(TESTS_DIR, "..", "src", "finest_computer_use"))
INSTALLED_DIR = os.path.expanduser("~/.gemini/config/skills/computer-use/scripts")

if os.path.exists(os.path.join(REPO_SRC, "safe_interact.py")):
    SCRIPT_DIR = REPO_SRC
elif os.path.exists(os.path.join(TESTS_DIR, "safe_interact.py")):
    SCRIPT_DIR = TESTS_DIR
else:
    SCRIPT_DIR = INSTALLED_DIR

SAFE_INTERACT = os.path.join(SCRIPT_DIR, "safe_interact.py")
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from effect_firewall import (
    init_task_contract,
    auto_create_contract_from_intent,
    trigger_recovery_mode,
    resolve_recovery_mode,
    load_firewall_state,
    save_firewall_state,
    issue_commit_receipt,
    consume_commit_receipt,
    get_task_dir
)
from effect_taxonomy import (
    EffectLevel,
    classify_action_risk,
    evaluate_semantic_alignment,
    is_unknown_high_impact_control,
    inspect_shell_bypass,
    classify_browser_action_degraded
)

def run_pre_hook(tool_call: dict, conv_id: str = "default", task_id: str = None, env: dict = None) -> dict:
    """Run real safe_interact.py PreToolUse hook via subprocess."""
    payload_dict = {"toolCall": tool_call, "conversationId": conv_id}
    if task_id:
        payload_dict["taskId"] = task_id
    payload = json.dumps(payload_dict)
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    res = subprocess.run(
        [sys.executable, SAFE_INTERACT],
        input=payload,
        text=True,
        capture_output=True,
        env=run_env
    )
    try:
        return json.loads(res.stdout)
    except Exception as e:
        return {"error": f"Failed to parse hook output: {res.stdout}, err={e}"}

def run_post_hook(tool_call: dict, error: str = None, conv_id: str = "default", task_id: str = None) -> dict:
    """Run real safe_interact.py PostToolUse hook via subprocess."""
    payload_dict = {"toolCall": tool_call, "error": error, "conversationId": conv_id}
    if task_id:
        payload_dict["taskId"] = task_id
    payload = json.dumps(payload_dict)
    res = subprocess.run(
        [sys.executable, SAFE_INTERACT, "post"],
        input=payload,
        text=True,
        capture_output=True
    )
    try:
        return json.loads(res.stdout)
    except Exception:
        return {}

# ----------------- FOUNDATION TESTS A-R -----------------

def test_a_semantic_mismatch():
    print("\n--- Test A: Semantic Mismatch (send_text vs voice_message) ---")
    init_task_contract("communication.send_text", {"communication.send_text": 1})
    tool_call = {
        "name": "call_mcp_tool",
        "args": {
            "ServerName": "peekaboo",
            "ToolName": "click",
            "Arguments": {"on": "ChatBar_VoiceMessageButton", "query": "Record voice message"}
        }
    }
    res = run_pre_hook(tool_call)
    assert res.get("decision") == "deny", f"Expected deny, got {res}"
    assert "Semantic Mismatch" in res.get("reason", "") or "voice" in res.get("reason", "").lower()
    print("Test A: PASS")

def test_b_unauthorized_adjacent_effect():
    print("\n--- Test B: Unauthorized Adjacent Effect (submit_text vs upload_file) ---")
    init_task_contract(
        "communication.send_text",
        {"communication.send_text": 1},
        forbidden_effects=["communication.send_file", "communication.send_voice"]
    )
    tool_call = {
        "name": "call_mcp_tool",
        "args": {
            "ServerName": "peekaboo",
            "ToolName": "click",
            "Arguments": {"on": "Attachment_UploadButton", "query": "Attach Document"}
        }
    }
    res = run_pre_hook(tool_call)
    assert res.get("decision") == "deny", f"Expected deny, got {res}"
    print("Test B: PASS")

def test_c_effect_budget():
    print("\n--- Test C: Side-Effect Budget (Limit = 1) ---")
    init_task_contract("communication.send_text", {"communication.send_text": 1})
    tool_call = {
        "name": "call_mcp_tool",
        "args": {
            "ServerName": "peekaboo",
            "ToolName": "click",
            "Arguments": {"on": "SendMessageButton", "query": "Send", "app": "MockApp"}
        }
    }
    res1 = run_pre_hook(tool_call)
    assert res1.get("decision") == "allow"
    run_post_hook(tool_call)

    run_pre_hook({
        "name": "call_mcp_tool",
        "args": {"ServerName": "peekaboo", "ToolName": "see", "Arguments": {"app": "MockApp"}}
    })

    res2 = run_pre_hook(tool_call)
    assert res2.get("decision") == "deny"
    assert "Budget exhausted" in res2.get("reason", "")
    print("Test C: PASS")

def test_d_verification_barrier():
    print("\n--- Test D: Mutation Barrier (Observe -> Mutate -> Verify) ---")
    init_task_contract("communication.send_text", {"communication.send_text": 5})
    tool_call = {
        "name": "call_mcp_tool",
        "args": {
            "ServerName": "peekaboo",
            "ToolName": "click",
            "Arguments": {"on": "SendMessageButton", "query": "Send", "app": "MockApp"}
        }
    }
    res1 = run_pre_hook(tool_call)
    assert res1.get("decision") == "allow"
    run_post_hook(tool_call)

    res2 = run_pre_hook(tool_call)
    assert res2.get("decision") == "deny"
    assert "Mutation Barrier" in res2.get("reason", "")

    obs_call = {
        "name": "call_mcp_tool",
        "args": {"ServerName": "peekaboo", "ToolName": "see", "Arguments": {"app": "MockApp"}}
    }
    res_obs = run_pre_hook(obs_call)
    assert res_obs.get("decision") == "allow"

    res3 = run_pre_hook(tool_call)
    assert res3.get("decision") == "allow"
    print("Test D: PASS")

def test_e_unexpected_state():
    print("\n--- Test E: Unexpected State Transition (Recovery Mode Gating) ---")
    init_task_contract("communication.send_text", {"communication.send_text": 1})
    trigger_recovery_mode("Unexpected state: Voice recording active")
    state = load_firewall_state()
    assert state.get("state") == "RECOVERY_MODE"

    commit_call = {
        "name": "call_mcp_tool",
        "args": {
            "ServerName": "peekaboo",
            "ToolName": "press",
            "Arguments": {"keys": ["Return"], "app": "ChatApp"}
        }
    }
    res = run_pre_hook(commit_call)
    assert res.get("decision") == "deny"
    assert "Recovery Mode" in res.get("reason", "")
    print("Test E: PASS")

def test_f_recovery():
    print("\n--- Test F: Recovery Mode Operations ---")
    state = load_firewall_state()
    assert state.get("state") == "RECOVERY_MODE"

    obs_call = {
        "name": "call_mcp_tool",
        "args": {"ServerName": "peekaboo", "ToolName": "see", "Arguments": {"app": "ChatApp"}}
    }
    assert run_pre_hook(obs_call).get("decision") == "allow"

    cancel_call = {
        "name": "call_mcp_tool",
        "args": {
            "ServerName": "peekaboo",
            "ToolName": "click",
            "Arguments": {"on": "btn_cancel_recording", "query": "Cancel recording"}
        }
    }
    assert run_pre_hook(cancel_call).get("decision") == "allow"

    resolve_recovery_mode()
    assert load_firewall_state().get("state") == "IDLE"
    print("Test F: PASS")

def test_g_unknown_high_impact():
    print("\n--- Test G: Unknown High-Impact Control (Fail-Closed) ---")
    init_task_contract("destructive.delete", {"destructive.delete": 1})
    is_unknown = is_unknown_high_impact_control(EffectLevel.LEVEL_5_DESTRUCTIVE_SENSITIVE, "elem_49", "")
    assert is_unknown is True
    print("Test G: PASS")

def test_h_unknown_low_risk():
    print("\n--- Test H: Unknown Low-Risk Control (Permissive Exploration) ---")
    init_task_contract("navigation.general", {})
    nav_call = {
        "name": "call_mcp_tool",
        "args": {
            "ServerName": "peekaboo",
            "ToolName": "scroll",
            "Arguments": {"direction": "down", "amount": 3}
        }
    }
    assert run_pre_hook(nav_call).get("decision") == "allow"
    print("Test H: PASS")

def test_i_shell_bypass():
    print("\n--- Test I: Shell / AppleScript Bypass Detection ---")
    init_task_contract("communication.send_text", {"communication.send_text": 1})
    bypass_cmd = 'osascript -e \'tell application "System Events" to click button "VoiceMessage" of window 1\''
    is_bypass, level, cat, details = inspect_shell_bypass(bypass_cmd)
    assert is_bypass is True
    assert cat == "communication.send_voice"

    res = run_pre_hook({"name": "run_command", "args": {"CommandLine": bypass_cmd}})
    assert res.get("decision") == "deny"
    assert "voice" in res.get("reason", "").lower()
    print("Test I: PASS")

def test_j_browser_external_effect():
    print("\n--- Test J: Browser / DOM Effect Classification ---")
    level_open, _ = classify_action_risk("click", {"on": "btn_open", "query": "Open"})
    level_send, _ = classify_action_risk("click", {"on": "btn_send_text", "query": "Send Text"})
    level_del, _ = classify_action_risk("click", {"on": "btn_delete_item", "query": "Delete Item"})
    level_buy, _ = classify_action_risk("click", {"on": "btn_purchase", "query": "Complete Purchase"})

    assert level_open == EffectLevel.LEVEL_1_NAVIGATION
    assert level_send == EffectLevel.LEVEL_4_EXTERNAL_SIDE_EFFECT
    assert level_del == EffectLevel.LEVEL_5_DESTRUCTIVE_SENSITIVE
    assert level_buy == EffectLevel.LEVEL_5_DESTRUCTIVE_SENSITIVE
    print("Test J: PASS")

def test_whatsapp_fixture():
    print("\n--- WhatsApp Incident Fixture ---")
    init_task_contract("communication.send_text", {"communication.send_text": 1})
    voice_click = {
        "name": "call_mcp_tool",
        "args": {
            "ServerName": "peekaboo",
            "ToolName": "click",
            "Arguments": {"on": "ChatBar_VoiceMessageButton", "query": "Voice Message"}
        }
    }
    assert run_pre_hook(voice_click).get("decision") == "deny"

    trigger_recovery_mode("Unexpected state: ChatBar recording UI active")
    return_key = {
        "name": "call_mcp_tool",
        "args": {
            "ServerName": "peekaboo",
            "ToolName": "press",
            "Arguments": {"app": "WhatsApp", "keys": ["Return"]}
        }
    }
    assert run_pre_hook(return_key).get("decision") == "deny"

    cancel_action = {
        "name": "call_mcp_tool",
        "args": {
            "ServerName": "peekaboo",
            "ToolName": "click",
            "Arguments": {"on": "ChatBar_CancelVoiceRecording", "query": "Cancel"}
        }
    }
    assert run_pre_hook(cancel_action).get("decision") == "allow"
    resolve_recovery_mode()
    print("WhatsApp Incident Fixture: PASS")

def test_l_e2e_natural_language_contract():
    print("\n--- Test L: E2E Natural Language Task Effect Contract ---")
    conv_id = "test_e2e_contract_gen"
    try:
        user_intent = "Send the text message in the chat"
        contract_state = auto_create_contract_from_intent(user_intent, conv_id=conv_id)
        assert contract_state.get("contract", {}).get("goal") == "communication.send_text"
        assert contract_state.get("budgets", {}).get("communication.send_text", {}).get("limit") == 1

        allowed_tool = {
            "name": "call_mcp_tool",
            "args": {
                "ServerName": "peekaboo",
                "ToolName": "click",
                "Arguments": {"on": "btn_send_text", "query": "Send Text", "app": "MockApp"}
            }
        }
        res_allow = run_pre_hook(allowed_tool, conv_id=conv_id)
        assert res_allow.get("decision") == "allow"
        print("Test L: PASS")
    finally:
        shutil.rmtree(f"/tmp/antigravity-effect-firewall/{conv_id}", ignore_errors=True)

def test_m_mock_ui_semantic_mismatch_e2e():
    print("\n--- Test M: True E2E Mock UI Semantic Mismatch ---")
    conv_id = "test_mock_ui_mismatch"
    try:
        auto_create_contract_from_intent("Send the text message in the mock interface", conv_id=conv_id)
        proposed_action = {
            "name": "call_mcp_tool",
            "args": {
                "ServerName": "peekaboo",
                "ToolName": "click",
                "Arguments": {"on": "btn_send_voice", "query": "Record Voice Message", "app": "MockApp"}
            }
        }
        res = run_pre_hook(proposed_action, conv_id=conv_id)
        assert res.get("decision") == "deny"
        assert "forbidden" in res.get("reason", "").lower() or "semantic mismatch" in res.get("reason", "").lower() or "voice" in res.get("reason", "").lower()
        print("Test M: PASS")
    finally:
        shutil.rmtree(f"/tmp/antigravity-effect-firewall/{conv_id}", ignore_errors=True)

def test_n_mock_ui_mutation_barrier_and_unrelated_obs_e2e():
    print("\n--- Test N: Mutation Barrier & Target-Bound Observation Verification ---")
    conv_id = "test_target_bound_barrier"
    try:
        init_task_contract("communication.send_text", {"communication.send_text": 3}, conv_id=conv_id)
        send_tool = {
            "name": "call_mcp_tool",
            "args": {
                "ServerName": "peekaboo",
                "ToolName": "click",
                "Arguments": {"on": "btn_send_text", "query": "Send Text", "app": "MockApp"}
            }
        }
        res1 = run_pre_hook(send_tool, conv_id=conv_id)
        assert res1.get("decision") == "allow"
        run_post_hook(send_tool, conv_id=conv_id)

        # 2nd mutation before observation blocked
        res2 = run_pre_hook(send_tool, conv_id=conv_id)
        assert res2.get("decision") == "deny"
        assert "Mutation Barrier" in res2.get("reason", "")

        # Unrelated observation does NOT clear barrier
        unrelated_obs = {
            "name": "call_mcp_tool",
            "args": {"ServerName": "peekaboo", "ToolName": "see", "Arguments": {"app": "System Settings"}}
        }
        res_unrelated = run_pre_hook(unrelated_obs, conv_id=conv_id)
        assert res_unrelated.get("decision") == "allow"

        # Still blocked
        res3 = run_pre_hook(send_tool, conv_id=conv_id)
        assert res3.get("decision") == "deny"

        # Target-bound observation clears barrier
        target_obs = {
            "name": "call_mcp_tool",
            "args": {"ServerName": "peekaboo", "ToolName": "see", "Arguments": {"app": "MockApp"}}
        }
        res_target = run_pre_hook(target_obs, conv_id=conv_id)
        assert res_target.get("decision") == "allow"

        # Now allowed
        res4 = run_pre_hook(send_tool, conv_id=conv_id)
        assert res4.get("decision") == "allow"
        print("Test N: PASS")
    finally:
        shutil.rmtree(f"/tmp/antigravity-effect-firewall/{conv_id}", ignore_errors=True)

def test_o_mock_ui_unexpected_state_recovery_e2e():
    print("\n--- Test O: Unexpected State Conflict & Safe Baseline Recovery ---")
    conv_id = "test_unexpected_recovery"
    try:
        init_task_contract("communication.send_text", {"communication.send_text": 2}, conv_id=conv_id)
        send_tool = {
            "name": "call_mcp_tool",
            "args": {"ServerName": "peekaboo", "ToolName": "click", "Arguments": {"on": "btn_send_text", "query": "Send Text", "app": "MockApp"}}
        }
        run_pre_hook(send_tool, conv_id=conv_id)
        run_post_hook(send_tool, conv_id=conv_id)

        # Observation evaluates UI state and finds unexpected conflict
        obs_conflict = {
            "name": "call_mcp_tool",
            "args": {"ServerName": "peekaboo", "ToolName": "see", "Arguments": {"app": "MockApp", "recording_active": True}}
        }
        run_pre_hook(obs_conflict, conv_id=conv_id)

        # In recovery mode: mutations blocked
        r_send = run_pre_hook(send_tool, conv_id=conv_id)
        assert r_send.get("decision") == "deny"

        # Cancel allowed
        cancel_tool = {
            "name": "call_mcp_tool",
            "args": {"ServerName": "peekaboo", "ToolName": "click", "Arguments": {"on": "btn_cancel", "query": "Cancel / Stop Recording", "app": "MockApp"}}
        }
        r_cancel = run_pre_hook(cancel_tool, conv_id=conv_id)
        assert r_cancel.get("decision") == "allow"

        resolve_recovery_mode(conv_id=conv_id)
        print("Test O: PASS")
    finally:
        shutil.rmtree(f"/tmp/antigravity-effect-firewall/{conv_id}", ignore_errors=True)

def test_p_degraded_mode_e2e():
    print("\n--- Test P: Fail-Safe Degraded Mode (Anti-Brick & Anti-Fail-Open) ---")
    degraded_env = {"SIMULATE_FIREWALL_FAILURE": "1"}

    # Low risk allowed
    r_ls = run_pre_hook({"name": "run_command", "args": {"CommandLine": "ls -la"}}, env=degraded_env)
    assert r_ls.get("decision") == "allow"

    r_see = run_pre_hook({"name": "call_mcp_tool", "args": {"ServerName": "peekaboo", "ToolName": "see", "Arguments": {"app": "MockApp"}}}, env=degraded_env)
    assert r_see.get("decision") == "allow"

    # High impact denied
    r_click = run_pre_hook({"name": "call_mcp_tool", "args": {"ServerName": "peekaboo", "ToolName": "click", "Arguments": {"on": "btn_send_text", "app": "MockApp"}}}, env=degraded_env)
    assert r_click.get("decision") == "deny"
    assert "degraded safety mode" in r_click.get("reason", "").lower() or "degraded mode" in r_click.get("reason", "").lower()
    print("Test P: PASS")

def test_q_multi_session_concurrency_isolation():
    print("\n--- Test Q: Multi-Session Concurrency & State Isolation ---")
    conv_a = "session_alpha_123"
    conv_b = "session_beta_456"

    try:
        init_task_contract("communication.send_text", {"communication.send_text": 1}, conv_id=conv_a)
        init_task_contract("destructive.delete", {"destructive.delete": 2}, risk_level="destructive", conv_id=conv_b)

        rcpt_a = issue_commit_receipt("communication.send_text", "btn_send_text", app="MockApp", conv_id=conv_a)
        r_id = rcpt_a["receipt_id"]

        ok_b, msg_b = consume_commit_receipt("communication.send_text", "btn_send_text", app="MockApp", receipt_id=r_id, conv_id=conv_b)
        assert ok_b is False
        assert "different" in msg_b.lower() or "not found" in msg_b.lower() or "no valid" in msg_b.lower()

        ok_a1, _ = consume_commit_receipt("communication.send_text", "btn_send_text", app="MockApp", receipt_id=r_id, conv_id=conv_a)
        assert ok_a1 is True
        print("Test Q: PASS")
    finally:
        shutil.rmtree(f"/tmp/antigravity-effect-firewall/{conv_a}", ignore_errors=True)
        shutil.rmtree(f"/tmp/antigravity-effect-firewall/{conv_b}", ignore_errors=True)

def test_r_daily_developer_autonomy_friction():
    print("\n--- Test R: Daily Developer Autonomy & Friction Verification ---")
    developer_commands = [
        {"name": "view_file", "args": {"AbsolutePath": os.path.expanduser("~/test.py")}},
        {"name": "run_command", "args": {"CommandLine": "git status"}},
        {"name": "run_command", "args": {"CommandLine": "git diff HEAD~1"}},
        {"name": "run_command", "args": {"CommandLine": "npx --version"}},
        {"name": "run_command", "args": {"CommandLine": "npm test"}},
        {"name": "call_mcp_tool", "args": {"ServerName": "peekaboo", "ToolName": "see", "Arguments": {"app": "Calculator"}}},
        {"name": "call_mcp_tool", "args": {"ServerName": "peekaboo", "ToolName": "scroll", "Arguments": {"direction": "down", "amount": 2}}},
        {"name": "call_mcp_tool", "args": {"ServerName": "peekaboo", "ToolName": "type", "Arguments": {"app": "Notes", "text": "hello"}}}
    ]

    for tool in developer_commands:
        res = run_pre_hook(tool)
        assert res.get("decision") == "allow"

    print("Test R: PASS")

# ----------------- MONOTONIC AUTHORIZATION TESTS (S - W) -----------------

def test_s_unauthorized_contract_expansion():
    print("\n--- Test S: Monotonic Authorization — Unauthorized Contract Expansion ---")
    conv_id = "test_mono_s"
    task_id = "task_s"
    try:
        # User says: send one text message
        ok_user, _, _ = init_task_contract(
            goal="communication.send_text",
            authorized_effects={"communication.send_text": 1},
            provenance="user",
            conv_id=conv_id,
            task_id=task_id
        )
        assert ok_user is True

        # Agent decides voice would be convenient (adding new Level 4 effect autonomously)
        ok_agent, _, err = init_task_contract(
            goal="communication.send_voice",
            authorized_effects={"communication.send_text": 1, "communication.send_voice": 1},
            provenance="agent",
            conv_id=conv_id,
            task_id=task_id
        )
        assert ok_agent is False
        assert "Monotonicity Violation" in err
        assert "Level 4/5 effect 'communication.send_voice'" in err
        print(f"  - Expansion blocked: {err}")
        print("Test S: PASS")
    finally:
        shutil.rmtree(f"/tmp/antigravity-effect-firewall/{conv_id}", ignore_errors=True)

def test_t_effect_budget_expansion():
    print("\n--- Test T: Monotonic Authorization — Effect Budget Expansion Blocked ---")
    conv_id = "test_mono_t"
    task_id = "task_t"
    try:
        init_task_contract(
            goal="communication.send_text",
            authorized_effects={"communication.send_text": 1},
            provenance="user",
            conv_id=conv_id,
            task_id=task_id
        )

        # Agent attempts to increase budget from 1 to 2
        ok_agent, _, err = init_task_contract(
            goal="communication.send_text",
            authorized_effects={"communication.send_text": 2},
            provenance="agent",
            conv_id=conv_id,
            task_id=task_id
        )
        assert ok_agent is False
        assert "Monotonicity Violation" in err
        assert "increase budget" in err
        print(f"  - Budget expansion blocked: {err}")
        print("Test T: PASS")
    finally:
        shutil.rmtree(f"/tmp/antigravity-effect-firewall/{conv_id}", ignore_errors=True)

def test_u_target_broadening():
    print("\n--- Test U: Monotonic Authorization — Target Broadening Blocked ---")
    conv_id = "test_mono_u"
    task_id = "task_u"
    try:
        # User says: delete exact file /tmp/report.txt
        init_task_contract(
            goal="destructive.delete",
            authorized_effects={"destructive.delete": 1},
            target_scope={"destructive.delete": "/tmp/report.txt"},
            risk_level="destructive",
            provenance="user",
            conv_id=conv_id,
            task_id=task_id
        )

        # Agent attempts to broaden target to directory /tmp/* or all files
        ok_agent, _, err = init_task_contract(
            goal="destructive.delete",
            authorized_effects={"destructive.delete": 1},
            target_scope={"destructive.delete": "*"},
            risk_level="destructive",
            provenance="agent",
            conv_id=conv_id,
            task_id=task_id
        )
        assert ok_agent is False
        assert "Monotonicity Violation" in err
        assert "broaden target" in err
        print(f"  - Target broadening blocked: {err}")
        print("Test U: PASS")
    finally:
        shutil.rmtree(f"/tmp/antigravity-effect-firewall/{conv_id}", ignore_errors=True)

def test_v_authorized_narrowing():
    print("\n--- Test V: Monotonic Authorization — Target Narrowing Allowed ---")
    conv_id = "test_mono_v"
    task_id = "task_v"
    try:
        # User authorized directory scope
        init_task_contract(
            goal="destructive.delete",
            authorized_effects={"destructive.delete": 1},
            target_scope={"destructive.delete": "/tmp/mock_folder/*"},
            risk_level="destructive",
            provenance="user",
            conv_id=conv_id,
            task_id=task_id
        )

        # Agent narrows to exact resolved file path within directory
        ok_agent, state, _ = init_task_contract(
            goal="destructive.delete",
            authorized_effects={"destructive.delete": 1},
            target_scope={"destructive.delete": "/tmp/mock_folder/report.txt"},
            risk_level="destructive",
            provenance="agent",
            conv_id=conv_id,
            task_id=task_id
        )
        assert ok_agent is True
        assert state["contract"]["target_scope"]["destructive.delete"] == "/tmp/mock_folder/report.txt"
        print("  - Narrowing allowed: PASS")
        print("Test V: PASS")
    finally:
        shutil.rmtree(f"/tmp/antigravity-effect-firewall/{conv_id}", ignore_errors=True)

def test_w_new_user_authorization():
    print("\n--- Test W: Monotonic Authorization — New User Authorization ---")
    conv_id = "test_mono_w"
    task_id = "task_w"
    try:
        # Initial user contract
        init_task_contract(
            goal="communication.send_text",
            authorized_effects={"communication.send_text": 1},
            provenance="user",
            conv_id=conv_id,
            task_id=task_id
        )

        # Agent expansion fails
        ok_fail, _, _ = init_task_contract(
            goal="communication.send_voice",
            authorized_effects={"communication.send_text": 1, "communication.send_voice": 1},
            provenance="agent",
            conv_id=conv_id,
            task_id=task_id
        )
        assert ok_fail is False

        # User later explicitly authorizes voice note: provenance="user"
        ok_user2, state2, _ = init_task_contract(
            goal="communication.send_voice",
            authorized_effects={"communication.send_text": 1, "communication.send_voice": 1},
            provenance="user",
            conv_id=conv_id,
            task_id=task_id
        )
        assert ok_user2 is True
        assert "communication.send_voice" in state2["user_authority"]["authorized_effects"]
        print("  - New user authorization successfully updated baseline: PASS")
        print("Test W: PASS")
    finally:
        shutil.rmtree(f"/tmp/antigravity-effect-firewall/{conv_id}", ignore_errors=True)

# ----------------- TRUE TASK-LEVEL ISOLATION TESTS (X - AA) -----------------

def test_x_same_conversation_task_isolation():
    print("\n--- Test X: True Task-Level Isolation (Same Conversation) ---")
    conv_id = "conv_shared"
    task_a = "task_send"
    task_b = "task_delete_mock"

    try:
        # Initialize Task A in conv_shared
        ok_a, _, _ = init_task_contract(
            goal="communication.send_text",
            authorized_effects={"communication.send_text": 1},
            provenance="user",
            conv_id=conv_id,
            task_id=task_a
        )
        assert ok_a is True

        # Initialize Task B in conv_shared
        ok_b, _, _ = init_task_contract(
            goal="destructive.delete",
            authorized_effects={"destructive.delete": 2},
            risk_level="destructive",
            provenance="user",
            conv_id=conv_id,
            task_id=task_b
        )
        assert ok_b is True

        # Check state independence
        state_a = load_firewall_state(conv_id, task_a)
        state_b = load_firewall_state(conv_id, task_b)
        assert state_a["task_id"] == task_a
        assert state_b["task_id"] == task_b
        assert state_a["contract"]["goal"] == "communication.send_text"
        assert state_b["contract"]["goal"] == "destructive.delete"
        assert state_a["budgets"]["communication.send_text"]["limit"] == 1
        assert state_b["budgets"]["destructive.delete"]["limit"] == 2
        print("  - Independent contracts and budgets verified: PASS")
        print("Test X: PASS")
    finally:
        shutil.rmtree(f"/tmp/antigravity-effect-firewall/{conv_id}", ignore_errors=True)

def test_y_cross_task_receipt_attack():
    print("\n--- Test Y: Cross-Task Receipt Theft Blocked ---")
    conv_id = "conv_shared"
    task_a = "task_send"
    task_b = "task_delete_mock"

    try:
        init_task_contract("communication.send_text", {"communication.send_text": 1}, conv_id=conv_id, task_id=task_a)
        init_task_contract("destructive.delete", {"destructive.delete": 1}, risk_level="destructive", conv_id=conv_id, task_id=task_b)

        # Issue receipt strictly bound to Task A
        rcpt_a = issue_commit_receipt("communication.send_text", "btn_send", app="MockApp", conv_id=conv_id, task_id=task_a)
        r_id = rcpt_a["receipt_id"]

        # Task B attempts to consume Task A's receipt
        ok_b, msg_b = consume_commit_receipt("communication.send_text", "btn_send", app="MockApp", receipt_id=r_id, conv_id=conv_id, task_id=task_b)
        assert ok_b is False
        assert "not found" in msg_b.lower() or "different" in msg_b.lower() or "no valid" in msg_b.lower()
        print(f"  - Cross-task receipt theft blocked: {msg_b}")
        print("Test Y: PASS")
    finally:
        shutil.rmtree(f"/tmp/antigravity-effect-firewall/{conv_id}", ignore_errors=True)

def test_z_cross_task_verification_leak():
    print("\n--- Test Z: Cross-Task Verification Leak Blocked ---")
    conv_id = "conv_shared"
    task_a = "task_send"
    task_b = "task_nav"

    try:
        init_task_contract("communication.send_text", {"communication.send_text": 2}, conv_id=conv_id, task_id=task_a)
        init_task_contract("navigation.general", {}, conv_id=conv_id, task_id=task_b)

        send_tool = {
            "name": "call_mcp_tool",
            "args": {"ServerName": "peekaboo", "ToolName": "click", "Arguments": {"on": "btn_send", "query": "Send", "app": "MockApp"}}
        }
        # Task A dispatches mutation -> sets verification_required = True on Task A
        run_pre_hook(send_tool, conv_id=conv_id, task_id=task_a)
        run_post_hook(send_tool, conv_id=conv_id, task_id=task_a)

        assert load_firewall_state(conv_id, task_a)["verification_required"] is True

        # Task B performs its own observation on MockApp
        obs_b = {
            "name": "call_mcp_tool",
            "args": {"ServerName": "peekaboo", "ToolName": "see", "Arguments": {"app": "MockApp"}}
        }
        res_b = run_pre_hook(obs_b, conv_id=conv_id, task_id=task_b)
        assert res_b.get("decision") == "allow"

        # Task A MUST STILL have verification_required = True
        state_a_after = load_firewall_state(conv_id, task_a)
        assert state_a_after["verification_required"] is True
        print("  - Task A verification barrier untouched by Task B: PASS")
        print("Test Z: PASS")
    finally:
        shutil.rmtree(f"/tmp/antigravity-effect-firewall/{conv_id}", ignore_errors=True)

def test_aa_cross_task_recovery_leak():
    print("\n--- Test AA: Cross-Task Recovery Leak Blocked ---")
    conv_id = "conv_shared"
    task_a = "task_err"
    task_b = "task_ok"

    try:
        init_task_contract("communication.send_text", {"communication.send_text": 1}, conv_id=conv_id, task_id=task_a)
        init_task_contract("destructive.delete", {"destructive.delete": 1}, risk_level="destructive", conv_id=conv_id, task_id=task_b)

        # Trigger recovery mode in Task A
        trigger_recovery_mode("Task A unexpected failure", conv_id=conv_id, task_id=task_a)

        assert load_firewall_state(conv_id, task_a)["state"] == "RECOVERY_MODE"
        assert load_firewall_state(conv_id, task_b)["state"] == "IDLE"

        # Task B performs its own mutation -> MUST BE ALLOWED (not blocked by Task A)
        del_tool = {
            "name": "call_mcp_tool",
            "args": {"ServerName": "peekaboo", "ToolName": "click", "Arguments": {"on": "btn_delete", "query": "Delete Item", "app": "MockApp"}}
        }
        res_b = run_pre_hook(del_tool, conv_id=conv_id, task_id=task_b)
        assert res_b.get("decision") == "allow"
        print("  - Task B unblocked by Task A's recovery mode: PASS")
        print("Test AA: PASS")
    finally:
        shutil.rmtree(f"/tmp/antigravity-effect-firewall/{conv_id}", ignore_errors=True)

# ----------------- DEGRADED BROWSER CLASSIFICATION TESTS (AB - AF) -----------------

def test_ab_degraded_browser_read():
    print("\n--- Test AB: Degraded Browser Read Inspection Allowed ---")
    env = {"SIMULATE_FIREWALL_FAILURE": "1"}

    # Browser screenshot / snapshot / console / inspect
    for action in ["snapshot", "screenshot", "console", "network", "status"]:
        tool_call = {
            "name": "call_mcp_tool",
            "args": {"ServerName": "peekaboo", "ToolName": "browser", "Arguments": {"action": action}}
        }
        res = run_pre_hook(tool_call, env=env)
        assert res.get("decision") == "allow", f"Expected allow for browser action {action}, got {res}"
        print(f"  - Browser action '{action}' allowed in degraded mode: PASS")
    print("Test AB: PASS")

def test_ac_degraded_browser_navigation():
    print("\n--- Test AC: Degraded Browser Reversible Navigation Allowed ---")
    env = {"SIMULATE_FIREWALL_FAILURE": "1"}

    for action in ["navigate", "new_page", "hover"]:
        tool_call = {
            "name": "call_mcp_tool",
            "args": {"ServerName": "peekaboo", "ToolName": "browser", "Arguments": {"action": action, "url": "http://localhost:8000"}}
        }
        res = run_pre_hook(tool_call, env=env)
        assert res.get("decision") == "allow", f"Expected allow for browser action {action}, got {res}"
        print(f"  - Browser action '{action}' allowed in degraded mode: PASS")
    print("Test AC: PASS")

def test_ad_degraded_browser_send():
    print("\n--- Test AD: Degraded Browser Send Mutation Denied ---")
    env = {"SIMULATE_FIREWALL_FAILURE": "1"}

    tool_call = {
        "name": "call_mcp_tool",
        "args": {
            "ServerName": "peekaboo",
            "ToolName": "browser",
            "Arguments": {"action": "click", "query": "Send Message", "uid": "btn_send"}
        }
    }
    res = run_pre_hook(tool_call, env=env)
    assert res.get("decision") == "deny"
    assert "degraded" in res.get("reason", "").lower()
    print(f"  - Browser send denied in degraded mode: {res.get('reason')}")
    print("Test AD: PASS")

def test_ae_degraded_browser_purchase_delete():
    print("\n--- Test AE: Degraded Browser Purchase/Delete Denied ---")
    env = {"SIMULATE_FIREWALL_FAILURE": "1"}

    tool_buy = {
        "name": "call_mcp_tool",
        "args": {"ServerName": "peekaboo", "ToolName": "browser", "Arguments": {"action": "click", "query": "Purchase Now", "uid": "btn_purchase"}}
    }
    r_buy = run_pre_hook(tool_buy, env=env)
    assert r_buy.get("decision") == "deny"

    tool_del = {
        "name": "call_mcp_tool",
        "args": {"ServerName": "peekaboo", "ToolName": "browser", "Arguments": {"action": "click", "query": "Delete Permanently", "uid": "btn_del"}}
    }
    r_del = run_pre_hook(tool_del, env=env)
    assert r_del.get("decision") == "deny"
    print("  - Browser purchase and delete mutations denied in degraded mode: PASS")
    print("Test AE: PASS")

def test_af_degraded_browser_unknown_mutation():
    print("\n--- Test AF: Degraded Browser Unknown Mutation Denied (Fail-Closed) ---")
    env = {"SIMULATE_FIREWALL_FAILURE": "1"}

    tool_unk = {
        "name": "call_mcp_tool",
        "args": {"ServerName": "peekaboo", "ToolName": "browser", "Arguments": {"action": "custom_script_injection_or_unknown"}}
    }
    r_unk = run_pre_hook(tool_unk, env=env)
    assert r_unk.get("decision") == "deny"
    assert "degraded" in r_unk.get("reason", "").lower()
    print("  - Unknown browser mutation fail-closed: PASS")
    print("Test AF: PASS")

# ----------------- TRUE END-TO-END TESTS 1 - 3 -----------------

def test_true_e2e_1_monotonic_authorization():
    print("\n--- True E2E Test 1: Full Monotonic Authorization Pipeline ---")
    conv_id = "e2e_mono_pipe"
    task_id = "e2e_task_mono"
    try:
        # Step 1: User says "Send one text message in the mock chat"
        user_intent = "Send one text message in the mock chat"
        state = auto_create_contract_from_intent(user_intent, conv_id=conv_id, task_id=task_id)
        assert state["user_authority"]["authorized_effects"] == {"communication.send_text": 1}

        # Step 2: Agent attempts autonomous expansion to send_voice
        cmd_agent = [
            sys.executable, SAFE_INTERACT, "contract",
            "communication.send_voice", '{"communication.send_voice": 1}', "[]", "standard",
            conv_id, task_id, "agent"
        ]
        res_exp = json.loads(subprocess.run(cmd_agent, capture_output=True, text=True).stdout)
        assert res_exp.get("success") is False
        assert "Monotonicity Violation" in res_exp.get("error", "")

        # Step 3: Agent attempts proposed click on Voice button
        voice_call = {
            "name": "call_mcp_tool",
            "args": {"ServerName": "peekaboo", "ToolName": "click", "Arguments": {"on": "btn_send_voice", "query": "Record Voice", "app": "MockApp"}}
        }
        res_voice = run_pre_hook(voice_call, conv_id=conv_id, task_id=task_id)
        assert res_voice.get("decision") == "deny"
        print("  - Monotonicity protected pipeline: Voice call denied before any UI mutation: PASS")
        print("True E2E Test 1: PASS")
    finally:
        shutil.rmtree(f"/tmp/antigravity-effect-firewall/{conv_id}", ignore_errors=True)

def test_true_e2e_2_same_conversation_multitask():
    print("\n--- True E2E Test 2: Full Same-Conversation Multi-Task Execution ---")
    conv_id = "e2e_conv_multi"
    task_1 = "task_writer"
    task_2 = "task_cleaner"

    try:
        # Task 1: writer sending message
        init_task_contract("communication.send_text", {"communication.send_text": 2}, conv_id=conv_id, task_id=task_1)
        # Task 2: cleaner deleting temp mock file
        init_task_contract("destructive.delete", {"destructive.delete": 1}, risk_level="destructive", conv_id=conv_id, task_id=task_2)

        # 1. Task 1 issues receipt and consumes it
        rcpt_1 = issue_commit_receipt("communication.send_text", "btn_send_text", app="MockApp", conv_id=conv_id, task_id=task_1)
        ok1, _ = consume_commit_receipt("communication.send_text", "btn_send_text", app="MockApp", receipt_id=rcpt_1["receipt_id"], conv_id=conv_id, task_id=task_1)
        assert ok1 is True

        # 2. Task 1 dispatches mutation -> enters verification barrier
        send_tool = {"name": "call_mcp_tool", "args": {"ServerName": "peekaboo", "ToolName": "click", "Arguments": {"on": "btn_send_text", "query": "Send", "app": "MockApp"}}}
        run_pre_hook(send_tool, conv_id=conv_id, task_id=task_1)
        run_post_hook(send_tool, conv_id=conv_id, task_id=task_1)
        assert load_firewall_state(conv_id, task_1)["verification_required"] is True

        # 3. Task 2 operates in parallel: executes its own allowed mutation without being blocked by Task 1's barrier
        del_tool = {"name": "call_mcp_tool", "args": {"ServerName": "peekaboo", "ToolName": "click", "Arguments": {"on": "btn_delete_item", "query": "Delete", "app": "MockApp"}}}
        r_del = run_pre_hook(del_tool, conv_id=conv_id, task_id=task_2)
        assert r_del.get("decision") == "allow"
        run_post_hook(del_tool, conv_id=conv_id, task_id=task_2)

        # 4. Task 1 triggers recovery mode due to unexpected conflict
        trigger_recovery_mode("Task 1 recording conflict", conv_id=conv_id, task_id=task_1)
        assert load_firewall_state(conv_id, task_1)["state"] == "RECOVERY_MODE"
        assert load_firewall_state(conv_id, task_2)["state"] != "RECOVERY_MODE"

        # 5. Task 2 can still observe and complete cleanly
        obs_tool = {"name": "call_mcp_tool", "args": {"ServerName": "peekaboo", "ToolName": "see", "Arguments": {"app": "MockApp"}}}
        r_obs2 = run_pre_hook(obs_tool, conv_id=conv_id, task_id=task_2)
        assert r_obs2.get("decision") == "allow"

        print("  - Full task-level independence demonstrated: PASS")
        print("True E2E Test 2: PASS")
    finally:
        shutil.rmtree(f"/tmp/antigravity-effect-firewall/{conv_id}", ignore_errors=True)

def test_true_e2e_3_degraded_browser():
    print("\n--- True E2E Test 3: Full Degraded Browser Action-Level Classification ---")
    env = {"SIMULATE_FIREWALL_FAILURE": "1"}

    # 1. Inspect allowed
    r1 = run_pre_hook({"name": "call_mcp_tool", "args": {"ServerName": "peekaboo", "ToolName": "browser", "Arguments": {"action": "snapshot"}}}, env=env)
    assert r1.get("decision") == "allow"

    # 2. Navigate allowed
    r2 = run_pre_hook({"name": "call_mcp_tool", "args": {"ServerName": "peekaboo", "ToolName": "browser", "Arguments": {"action": "navigate", "url": "http://localhost:8000"}}}, env=env)
    assert r2.get("decision") == "allow"

    # 3. Send denied
    r3 = run_pre_hook({"name": "call_mcp_tool", "args": {"ServerName": "peekaboo", "ToolName": "browser", "Arguments": {"action": "click", "query": "Send"}}}, env=env)
    assert r3.get("decision") == "deny"

    # 4. Delete denied
    r4 = run_pre_hook({"name": "call_mcp_tool", "args": {"ServerName": "peekaboo", "ToolName": "browser", "Arguments": {"action": "click", "query": "Delete"}}}, env=env)
    assert r4.get("decision") == "deny"

    # 5. Purchase denied
    r5 = run_pre_hook({"name": "call_mcp_tool", "args": {"ServerName": "peekaboo", "ToolName": "browser", "Arguments": {"action": "click", "query": "Purchase"}}}, env=env)
    assert r5.get("decision") == "deny"

    print("  - Action-level browser classification confirmed under failure: PASS")
    print("True E2E Test 3: PASS")

def run_all():
    print("=====================================================================")
    print("STARTING FULL COMPUTER USE SAFETY v1 REGRESSION SUITE (35 TESTS)")
    print("=====================================================================")
    test_a_semantic_mismatch()
    test_b_unauthorized_adjacent_effect()
    test_c_effect_budget()
    test_d_verification_barrier()
    test_e_unexpected_state()
    test_f_recovery()
    test_g_unknown_high_impact()
    test_h_unknown_low_risk()
    test_i_shell_bypass()
    test_j_browser_external_effect()
    test_whatsapp_fixture()
    test_l_e2e_natural_language_contract()
    test_m_mock_ui_semantic_mismatch_e2e()
    test_n_mock_ui_mutation_barrier_and_unrelated_obs_e2e()
    test_o_mock_ui_unexpected_state_recovery_e2e()
    test_p_degraded_mode_e2e()
    test_q_multi_session_concurrency_isolation()
    test_r_daily_developer_autonomy_friction()
    test_s_unauthorized_contract_expansion()
    test_t_effect_budget_expansion()
    test_u_target_broadening()
    test_v_authorized_narrowing()
    test_w_new_user_authorization()
    test_x_same_conversation_task_isolation()
    test_y_cross_task_receipt_attack()
    test_z_cross_task_verification_leak()
    test_aa_cross_task_recovery_leak()
    test_ab_degraded_browser_read()
    test_ac_degraded_browser_navigation()
    test_ad_degraded_browser_send()
    test_ae_degraded_browser_purchase_delete()
    test_af_degraded_browser_unknown_mutation()
    test_true_e2e_1_monotonic_authorization()
    test_true_e2e_2_same_conversation_multitask()
    test_true_e2e_3_degraded_browser()
    print("\n=====================================================================")
    print("ALL 35 REGRESSION TESTS PASSED WITH 100% SUCCESS (TESTS A-AF + E2E 1-3)")
    print("=====================================================================")

if __name__ == "__main__":
    run_all()
