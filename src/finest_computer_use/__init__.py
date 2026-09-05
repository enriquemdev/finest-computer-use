"""
finest_computer_use — Hardened macOS Computer Use Safety Architecture.

Core modules:
- effect_taxonomy: 6-level effect taxonomy and semantic alignment engine.
- effect_firewall: Task-scoped Intent/Effect Firewall, monotonic authorization, and state machine.
- safe_interact: Minimal resilient bootstrap router and physical guardrail enforcement.
"""

from .effect_taxonomy import (
    EffectLevel,
    classify_action_risk,
    evaluate_semantic_alignment,
    is_unknown_high_impact_control,
    inspect_shell_bypass,
    classify_browser_action_degraded
)

from .effect_firewall import (
    init_task_contract,
    auto_create_contract_from_intent,
    trigger_recovery_mode,
    resolve_recovery_mode,
    issue_commit_receipt,
    consume_commit_receipt,
    pre_tool_firewall_check,
    post_tool_firewall_update,
    load_firewall_state,
    save_firewall_state
)

from .safe_interact import (
    process_hook_payload,
    process_post_tool_payload
)

__version__ = "1.0.0"

__all__ = [
    "EffectLevel",
    "classify_action_risk",
    "evaluate_semantic_alignment",
    "is_unknown_high_impact_control",
    "inspect_shell_bypass",
    "classify_browser_action_degraded",
    "init_task_contract",
    "auto_create_contract_from_intent",
    "trigger_recovery_mode",
    "resolve_recovery_mode",
    "issue_commit_receipt",
    "consume_commit_receipt",
    "pre_tool_firewall_check",
    "post_tool_firewall_update",
    "load_firewall_state",
    "save_firewall_state",
    "process_hook_payload",
    "process_post_tool_payload",
    "__version__"
]
