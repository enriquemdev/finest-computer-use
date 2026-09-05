# Unexpected State Recovery Protocol

## 1. State Desynchronization

When interacting with complex desktop applications, an action may trigger an unexpected modal, pop-up, or state transition (e.g. an unexpected permission prompt, an audio recording indicator, or an error banner).

The agent's policy requires immediate abort upon detecting unexpected UI states:
- **Rule:** If an action triggers an unexpected UI state, DO NOT proceed with planned mutations.
- **Firewall Action:** Transition task to `RECOVERY_MODE`.

---

## 2. Recovery Mode Invariants

When a task enters `RECOVERY_MODE`:
1. All standard mutating tool calls (`click`, `type`, `press`) are **DENIED**.
2. Only low-risk observational calls (`see`, `inspect_ui`) and explicit **Cancel / Stop** operations are permitted.
3. Once the baseline is restored (e.g. user closes the dialog or agent clicks Cancel), recovery mode is cleared:
   ```bash
   python3 safe_interact.py recovery_resolve <conv_id> <task_id>
   ```
