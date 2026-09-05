#!/usr/bin/env python3
"""
effect_taxonomy.py — Generalized Effect Classification and Semantic Alignment Engine.

Defines the 6-level taxonomy for Computer Use effects and verifies semantic alignment
between user intent and target UI controls across native applications, shell scripts,
and browser DOM automation.

Includes granular classification for browser DevTools actions in both Healthy and
Fail-Safe Degraded modes.
"""

from enum import IntEnum
import re
from typing import Dict, Any, Optional, Tuple, List

class EffectLevel(IntEnum):
    LEVEL_0_OBSERVATION = 0          # Read-only (see, inspect_ui, screenshot, cat, grep)
    LEVEL_1_NAVIGATION = 1           # Reversible navigation (scroll, window switch, focus)
    LEVEL_2_LOCAL_MUTATION = 2       # Reversible local mutation (draft typing, form edit)
    LEVEL_3_PERSISTENT_MUTATION = 3  # Local persistent change (save file, close window, edit config)
    LEVEL_4_EXTERNAL_SIDE_EFFECT = 4 # External side effect (send message, email, post, call, mic record)
    LEVEL_5_DESTRUCTIVE_SENSITIVE = 5# Destructive / financial (delete, purchase, permissions, wipe)

# Keywords indicating specific external/destructive effect categories
VOICE_OR_RECORDING_INDICATORS = [
    "voice", "audio", "mic", "microphone", "record", "recording",
    "voicenote", "ptt", "push_to_talk", "audiomessage", "voicemessage"
]

CALL_INDICATORS = [
    "call", "videocall", "audiocall", "phone", "dial", "ring"
]

FILE_ATTACHMENT_INDICATORS = [
    "attach", "attachment", "file", "upload", "document", "photo", "image", "gallery", "camera"
]

DELETE_OR_DISCARD_INDICATORS = [
    "delete", "trash", "remove", "destroy", "wipe", "erase", "discard", "purge", "clear_all"
]

FINANCIAL_INDICATORS = [
    "buy", "purchase", "pay", "payment", "checkout", "subscribe", "order", "transfer", "send_money"
]

TEXT_SEND_INDICATORS = [
    "send", "sendbutton", "submit", "btn_send", "composer_send", "sendmessage"
]

SAVE_INDICATORS = [
    "save", "apply", "commit", "confirm", "ok", "done"
]

# Browser DevTools Action Sets
BROWSER_READ_ONLY_ACTIONS = {
    "status", "connect", "disconnect", "list_pages", "select_page",
    "wait_for", "snapshot", "console", "network", "screenshot", "performance_trace"
}

BROWSER_NAVIGATION_ACTIONS = {
    "navigate", "new_page", "hover"
}

BROWSER_MUTATIVE_ACTIONS = {
    "click", "dom_click", "fill", "fill_form", "drag", "type",
    "press_key", "upload_file", "handle_dialog", "close_page", "call"
}

BROWSER_READ_ONLY_MCP_TOOLS = {
    "get_console_message", "get_heapsnapshot_class_nodes", "get_heapsnapshot_details",
    "get_heapsnapshot_dominators", "get_heapsnapshot_duplicate_strings", "get_heapsnapshot_edges",
    "get_heapsnapshot_retainers", "get_heapsnapshot_retaining_paths", "get_heapsnapshot_summary",
    "get_network_request", "get_tab_id", "lighthouse_audit", "list_3p_developer_tools",
    "list_console_messages", "list_extensions", "list_network_requests", "list_pages",
    "list_webmcp_tools", "performance_analyze_insight", "take_heapsnapshot", "take_screenshot",
    "take_snapshot", "wait_for"
}

BROWSER_NAVIGATION_MCP_TOOLS = {
    "navigate_page", "new_page", "hover", "resize_page"
}

def classify_browser_action_degraded(args: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    """
    Fail-Safe Degraded Mode Browser Action Classifier:
    - Read-only DOM/page inspection and traces -> ALLOW.
    - Reversible page navigation -> ALLOW.
    - Interactive/mutative actions (click, type, fill, upload, submit, delete, buy) -> DENY.
    - Unknown/opaque browser actions -> DENY (fail-closed).
    """
    action = args.get("action", "")
    mcp_tool = args.get("mcp_tool", "")

    # Safe read-only inspection
    if action in BROWSER_READ_ONLY_ACTIONS:
        return ("allow", None)
    if action == "call" and mcp_tool in BROWSER_READ_ONLY_MCP_TOOLS:
        return ("allow", None)

    # Safe reversible navigation
    if action in BROWSER_NAVIGATION_ACTIONS:
        return ("allow", None)
    if action == "call" and mcp_tool in BROWSER_NAVIGATION_MCP_TOOLS:
        return ("allow", None)

    # Any interactive, mutative, or unknown action must be denied in degraded mode
    return (
        "deny",
        "BLOCKED [Degraded Mode]: Effect Firewall unavailable; browser mutation cannot be safely effect-classified in degraded safety mode."
    )

def classify_action_risk(
    tool_name: str,
    args: Dict[str, Any]
) -> Tuple[EffectLevel, str]:
    """
    Classify the effect level and general category of a tool call.
    Returns (EffectLevel, effect_category_string).
    """
    # Level 0: Pure observation native tools
    if tool_name in ["see", "inspect_ui", "capture", "image", "verify_state", "permissions"]:
        return (EffectLevel.LEVEL_0_OBSERVATION, "observation.inspect")

    # Granular Browser Tool Classification
    if tool_name == "browser":
        action = args.get("action", "")
        mcp_tool = args.get("mcp_tool", "")

        # 1. Observation actions
        if action in BROWSER_READ_ONLY_ACTIONS or (action == "call" and mcp_tool in BROWSER_READ_ONLY_MCP_TOOLS):
            return (EffectLevel.LEVEL_0_OBSERVATION, "observation.browser")

        # 2. Navigation actions
        if action in BROWSER_NAVIGATION_ACTIONS or (action == "call" and mcp_tool in BROWSER_NAVIGATION_MCP_TOOLS):
            return (EffectLevel.LEVEL_1_NAVIGATION, "navigation.browser")

        # 3. Form input / drafting
        if action in ["fill", "fill_form", "type"]:
            if args.get("submit_key") in ["Enter", "Return"]:
                return (EffectLevel.LEVEL_4_EXTERNAL_SIDE_EFFECT, "external.key_commit")
            return (EffectLevel.LEVEL_2_LOCAL_MUTATION, "local_edit.browser")

        if action == "press_key":
            k = str(args.get("key", "")).lower()
            if k in ["return", "enter"]:
                return (EffectLevel.LEVEL_4_EXTERNAL_SIDE_EFFECT, "external.key_commit")
            return (EffectLevel.LEVEL_2_LOCAL_MUTATION, "local_edit.browser_press")

        # 4. Page close
        if action == "close_page" or (action == "call" and mcp_tool == "close_page"):
            return (EffectLevel.LEVEL_3_PERSISTENT_MUTATION, "persistent.browser_close_page")

        # 5. File upload
        if action == "upload_file" or (action == "call" and mcp_tool == "upload_file"):
            return (EffectLevel.LEVEL_4_EXTERNAL_SIDE_EFFECT, "communication.send_file")

        # 6. Dialog handler
        if action == "handle_dialog":
            if args.get("dialog_action") == "dismiss":
                return (EffectLevel.LEVEL_1_NAVIGATION, "recovery.cancel")
            return (EffectLevel.LEVEL_4_EXTERNAL_SIDE_EFFECT, "external.browser_dialog_accept")

        # 7. Browser click / DOM click
        if action in ["click", "dom_click"] or (action == "call" and mcp_tool in ["click", "click_at"]):
            target_text = (
                str(args.get("uid", "")) + " " +
                str(args.get("query", "")) + " " +
                str(args.get("text", "")) + " " +
                str(args.get("value", "")) + " " +
                str(args.get("on", ""))
            ).lower()

            # Recovery / Cancel
            if any(w in target_text for w in ["cancel", "undo", "stop", "abort", "dismiss", "back"]):
                return (EffectLevel.LEVEL_1_NAVIGATION, "recovery.cancel")

            # Destructive Delete
            if any(w in target_text for w in DELETE_OR_DISCARD_INDICATORS):
                return (EffectLevel.LEVEL_5_DESTRUCTIVE_SENSITIVE, "destructive.delete")

            # Financial Purchase
            if any(w in target_text for w in FINANCIAL_INDICATORS):
                return (EffectLevel.LEVEL_5_DESTRUCTIVE_SENSITIVE, "financial.purchase")

            # Voice / Audio
            if any(w in target_text for w in VOICE_OR_RECORDING_INDICATORS):
                return (EffectLevel.LEVEL_4_EXTERNAL_SIDE_EFFECT, "communication.send_voice")

            # File attachment
            if any(w in target_text for w in FILE_ATTACHMENT_INDICATORS):
                return (EffectLevel.LEVEL_4_EXTERNAL_SIDE_EFFECT, "communication.send_file")

            # Text Send / Submit
            if any(w in target_text for w in TEXT_SEND_INDICATORS) or "submit" in target_text:
                return (EffectLevel.LEVEL_4_EXTERNAL_SIDE_EFFECT, "communication.send_text")

            # Default browser click
            return (EffectLevel.LEVEL_1_NAVIGATION, "navigation.browser_click")

        # 8. Script execution / raw call
        if action == "call" and mcp_tool == "evaluate_script":
            script_body = str(args.get("mcp_args_json", "")).lower()
            if any(w in script_body for w in DELETE_OR_DISCARD_INDICATORS):
                return (EffectLevel.LEVEL_5_DESTRUCTIVE_SENSITIVE, "destructive.delete")
            if any(w in script_body for w in FINANCIAL_INDICATORS):
                return (EffectLevel.LEVEL_5_DESTRUCTIVE_SENSITIVE, "financial.purchase")
            if any(w in script_body for w in TEXT_SEND_INDICATORS):
                return (EffectLevel.LEVEL_4_EXTERNAL_SIDE_EFFECT, "communication.send_text")
            return (EffectLevel.LEVEL_4_EXTERNAL_SIDE_EFFECT, "external.evaluate_script")

        # Fallback for unknown browser action
        return (EffectLevel.LEVEL_4_EXTERNAL_SIDE_EFFECT, "unknown.browser_action")

    # Level 1: Navigation tools
    if tool_name in ["scroll", "space"]:
        return (EffectLevel.LEVEL_1_NAVIGATION, "navigation.scroll")
    if tool_name == "app":
        action = args.get("action", "")
        if action in ["focus", "switch", "list"]:
            return (EffectLevel.LEVEL_1_NAVIGATION, "navigation.app_focus")
        elif action in ["quit", "hide", "unhide"]:
            return (EffectLevel.LEVEL_1_NAVIGATION, "navigation.app_lifecycle")
    if tool_name == "window":
        action = args.get("action", "")
        if action in ["list", "minimize", "set-bounds", "raise"]:
            return (EffectLevel.LEVEL_1_NAVIGATION, "navigation.window")
        elif action == "close":
            return (EffectLevel.LEVEL_3_PERSISTENT_MUTATION, "persistent.window_close")

    # Level 2 vs Level 4: text input & pressing
    if tool_name == "set_value":
        return (EffectLevel.LEVEL_2_LOCAL_MUTATION, "local_edit.set_value")

    if tool_name == "type":
        return (EffectLevel.LEVEL_2_LOCAL_MUTATION, "local_edit.type")

    if tool_name == "press":
        keys = args.get("keys", []) or ([args.get("key")] if args.get("key") else [])
        keys_lower = [str(k).lower() for k in keys]
        if any(k in ["return", "enter"] for k in keys_lower):
            return (EffectLevel.LEVEL_4_EXTERNAL_SIDE_EFFECT, "external.key_commit")
        return (EffectLevel.LEVEL_2_LOCAL_MUTATION, "local_edit.press_key")

    # Level 1 to 5: Clicks depending on target semantics
    if tool_name in ["click", "dialog", "menu"]:
        target_text = ""
        if tool_name == "click":
            target_text = str(args.get("on", "")) + " " + str(args.get("query", ""))
        elif tool_name == "dialog":
            target_text = str(args.get("button", ""))
        elif tool_name == "menu":
            target_text = str(args.get("path", ""))

        target_lower = target_text.lower()

        # Check Recovery / Cancel / Undo first
        if any(w in target_lower for w in ["cancel", "undo", "stop", "abort", "dismiss", "back"]):
            return (EffectLevel.LEVEL_1_NAVIGATION, "recovery.cancel")

        # Check Level 5: Delete / destructive
        if any(w in target_lower for w in DELETE_OR_DISCARD_INDICATORS):
            return (EffectLevel.LEVEL_5_DESTRUCTIVE_SENSITIVE, "destructive.delete")

        # Check Level 5: Financial
        if any(w in target_lower for w in FINANCIAL_INDICATORS):
            return (EffectLevel.LEVEL_5_DESTRUCTIVE_SENSITIVE, "financial.purchase")

        # Check Level 4: Voice / recording
        if any(w in target_lower for w in VOICE_OR_RECORDING_INDICATORS):
            return (EffectLevel.LEVEL_4_EXTERNAL_SIDE_EFFECT, "communication.send_voice")

        # Check Level 4: Calls
        if any(w in target_lower for w in CALL_INDICATORS):
            return (EffectLevel.LEVEL_4_EXTERNAL_SIDE_EFFECT, "communication.call")

        # Check Level 4: Attachments
        if any(w in target_lower for w in FILE_ATTACHMENT_INDICATORS):
            return (EffectLevel.LEVEL_4_EXTERNAL_SIDE_EFFECT, "communication.send_file")

        # Check Level 4: Send text / submit
        if any(w in target_lower for w in TEXT_SEND_INDICATORS):
            return (EffectLevel.LEVEL_4_EXTERNAL_SIDE_EFFECT, "communication.send_text")

        # Check Level 3: Save / persistent change
        if any(w in target_lower for w in SAVE_INDICATORS):
            return (EffectLevel.LEVEL_3_PERSISTENT_MUTATION, "persistent.save")

        # If coords are provided without semantic hints
        if "coords" in args and not args.get("on") and not args.get("query"):
            return (EffectLevel.LEVEL_4_EXTERNAL_SIDE_EFFECT, "unknown.coordinate_click")

        # Default click on normal UI button / item
        return (EffectLevel.LEVEL_1_NAVIGATION, "navigation.click")

    return (EffectLevel.LEVEL_1_NAVIGATION, "general.unclassified")

def evaluate_semantic_alignment(
    intended_effect: str,
    target_identifier: str,
    target_label: str = "",
    target_help: str = ""
) -> Tuple[bool, Optional[str]]:
    """
    Validate that the target element semantics match the intended effect.
    Returns (is_aligned, mismatch_reason).
    """
    combined = f"{target_identifier} {target_label} {target_help}".lower()

    # Cancel / undo / stop / back actions are universally permissible recovery / navigation controls
    if any(w in combined for w in ["cancel", "undo", "stop", "abort", "dismiss", "back", "close"]):
        return (True, None)

    # Case 1: Intended effect is sending text
    if intended_effect == "communication.send_text":
        for indicator in VOICE_OR_RECORDING_INDICATORS:
            if indicator in combined:
                return (
                    False,
                    f"Semantic Mismatch: Intended 'send_text' but target contains voice/recording indicator '{indicator}' ({target_identifier})."
                )
        for indicator in CALL_INDICATORS:
            if indicator in combined:
                return (
                    False,
                    f"Semantic Mismatch: Intended 'send_text' but target contains call indicator '{indicator}' ({target_identifier})."
                )
        for indicator in FILE_ATTACHMENT_INDICATORS:
            if indicator in combined and "send" not in combined:
                return (
                    False,
                    f"Semantic Mismatch: Intended 'send_text' but target contains attachment indicator '{indicator}' ({target_identifier})."
                )

    # Case 2: Intended effect is save
    if intended_effect == "persistent.save":
        for indicator in ["discard", "don't save", "dont save", "cancel", "delete", "trash"]:
            if indicator in combined:
                return (
                    False,
                    f"Semantic Mismatch: Intended 'save' but target indicates discard/cancel '{indicator}'."
                )

    # Case 3: Intended effect is submit form/text
    if intended_effect in ["external.submit", "external.submit_text"]:
        for indicator in FINANCIAL_INDICATORS:
            if indicator in combined and "purchase" not in intended_effect:
                return (
                    False,
                    f"Semantic Mismatch: Intended non-financial submission but target indicates financial purchase '{indicator}'."
                )

    # Case 4: Intended effect is close / cancel
    if intended_effect in ["navigation.close", "navigation.cancel"]:
        for indicator in ["delete", "trash", "erase", "wipe", "destroy"]:
            if indicator in combined:
                return (
                    False,
                    f"Semantic Mismatch: Intended benign close/cancel but target indicates destructive action '{indicator}'."
                )

    return (True, None)

def is_unknown_high_impact_control(
    level: EffectLevel,
    target_identifier: str,
    target_label: str,
    target_role: str = ""
) -> bool:
    """
    Check if a control is ambiguous / opaque during a Level 4 or Level 5 action.
    Fails closed if high impact + no semantic label.
    """
    if level < EffectLevel.LEVEL_4_EXTERNAL_SIDE_EFFECT:
        return False

    cleaned_id = target_identifier.strip()
    cleaned_label = target_label.strip()

    is_generic_id = bool(re.match(r"^elem_\d+$", cleaned_id)) or cleaned_id == ""
    if is_generic_id and (cleaned_label == "" or cleaned_label == '""'):
        return True

    return False

def inspect_shell_bypass(cmd: str) -> Tuple[bool, EffectLevel, str, Optional[str]]:
    """
    Inspect shell commands (like osascript) that attempt UI mutations.
    Returns (is_ui_bypass, level, effect_category, details).
    """
    cmd_lower = cmd.lower()
    
    if "osascript" in cmd_lower or "system events" in cmd_lower:
        if "keystroke" in cmd_lower or "key code" in cmd_lower:
            if "return" in cmd_lower or "enter" in cmd_lower:
                return (True, EffectLevel.LEVEL_4_EXTERNAL_SIDE_EFFECT, "external.key_commit", "osascript keystroke Return")
            return (True, EffectLevel.LEVEL_2_LOCAL_MUTATION, "local_edit.keystroke", "osascript keystroke")
            
        if "click" in cmd_lower:
            for ind in VOICE_OR_RECORDING_INDICATORS:
                if ind in cmd_lower:
                    return (True, EffectLevel.LEVEL_4_EXTERNAL_SIDE_EFFECT, "communication.send_voice", f"osascript click on {ind}")
            for ind in DELETE_OR_DISCARD_INDICATORS:
                if ind in cmd_lower:
                    return (True, EffectLevel.LEVEL_5_DESTRUCTIVE_SENSITIVE, "destructive.delete", f"osascript click on {ind}")
            for ind in TEXT_SEND_INDICATORS:
                if ind in cmd_lower:
                    return (True, EffectLevel.LEVEL_4_EXTERNAL_SIDE_EFFECT, "communication.send_text", f"osascript click on {ind}")
            return (True, EffectLevel.LEVEL_1_NAVIGATION, "navigation.click", "osascript click")

    return (False, EffectLevel.LEVEL_0_OBSERVATION, "shell.standard", None)
