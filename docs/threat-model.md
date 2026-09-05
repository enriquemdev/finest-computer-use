# Threat Model & Attack Vectors

The Finest Computer Use Safety Architecture explicitly addresses several high-consequence failure modes in autonomous computer use:

---

## 1. Threat Vectors Addressed

### TV-1: Semantic Mismatch on Ambiguous UI Elements
- **Vector:** Agent is authorized to perform action A (e.g. `send_text`), but clicks an adjacent control B (e.g. `voice_record`) because their icons or accessibility trees look similar.
- **Mitigation:** Strict semantic keyword analysis matching target button attributes against authorized task goals. Any adjacent or conflicting action is rejected at PreToolUse.

### TV-2: Autonomous Scope Escalation & Privilege Creep
- **Vector:** Agent decides on its own to expand an authorized contract (e.g., adding delete privileges or increasing send budget) during execution without user knowledge.
- **Mitigation:** Monotonic Authorization Engine. Agent provenance can only narrow target scope (subsets); any expansion requires verified `user` provenance.

### TV-3: Uncontrolled Mutation Loops (Blind Clicks)
- **Vector:** Agent executes rapid consecutive clicks without observing the outcome, potentially clicking confirmations or dangerous buttons repeatedly.
- **Mitigation:** Mutation Barrier. Every mutation raises a barrier requiring an immediate target-bound observation (`see` on the target application) before another mutation is permitted.

### TV-4: Cross-Task State Leaks in Concurrent Sessions
- **Vector:** In multi-agent or subagent environments, one subagent inherits an authorized commit receipt or recovery state from another subagent running under the same parent conversation.
- **Mitigation:** Full task-level state isolation keyed by `(conversation_id, task_id)` with POSIX file locks (`fcntl.flock`).

### TV-5: Global Hook Brick (Fail-Open / Fail-Closed Catastrophe)
- **Vector:** A syntax error or dependency failure in a global PreToolUse hook blocks all agent tools (including terminal and file editor), bricking the system.
- **Mitigation:** Fail-Safe Degraded Mode and fast-path bypass. Fast-path tools are exempt from complex dependencies. If modules fail to load, developer tools pass through, but desktop mutations fail closed.

### TV-6: External Effect Bypasses via Shell
- **Vector:** Agent attempts to circumvent desktop GUI restrictions by using shell tools (`osascript`, `curl`, `mail`).
- **Mitigation:** Inspection of terminal commands for AppleScript GUI interaction (`tell application "System Events"`), external webhook dispatches, and irreversible mutations.
