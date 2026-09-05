# Fail-Safe Degraded Mode (Anti-Brick + Anti-Fail-Open)

When external safety hooks intercept tool calls, failures in the hook process itself pose two symmetric threats:

1. **Bricking (Fail-Closed on Everything):**  
   If an import error or unhandled exception occurs in the hook, blocking all tools prevents the agent from reading files, executing terminal commands, or repairing the faulty script.
2. **Security Collapse (Fail-Open on Everything):**  
   If an exception handler simply returns `allow` for all calls to avoid bricking, any subsequent high-risk GUI action will execute without any safety guardrails.

Finest Computer Use solves this dilemma with **Degraded Mode Protection**.

---

## 1. The Dual Invariant

When `safe_interact.py` catches an unhandled exception or detects a missing dependency:
- **Benign Developer Tools Pass Through (Anti-Brick):**  
  Calls to `view_file`, `replace_file_content`, `write_to_file`, and standard developer commands (`git`, `ls`, `cargo`, `npm`) are allowed. The developer or agent can fix the broken file immediately.
- **Mutating Computer Use Fails Closed (Anti-Fail-Open):**  
  Any tool call intended to mutate the desktop GUI or web browser is denied.

---

## 2. Granular Browser Classification in Degraded Mode

In degraded mode, browser actions (`call_mcp_tool` with `ServerName == "peekaboo"` and `ToolName == "browser"`) are evaluated individually:

| Browser Action | Mode Classification | Decision | Rationale |
| :--- | :--- | :--- | :--- |
| `snapshot` | Level 0: Pure Observation | **ALLOW** | Read-only inspection of DOM state |
| `screenshot` | Level 0: Pure Observation | **ALLOW** | Read-only capture |
| `console` | Level 0: Pure Observation | **ALLOW** | Read-only logs |
| `network` | Level 0: Pure Observation | **ALLOW** | Read-only network events |
| `status` | Level 0: Pure Observation | **ALLOW** | Read-only browser health |
| `navigate` | Level 1: Reversible Navigation | **ALLOW** | URL navigation is inspectable and reversible |
| `new_page` | Level 1: Reversible Navigation | **ALLOW** | Tab creation is benign |
| `hover` | Level 1: Focus / Inspection | **ALLOW** | Non-mutating cursor placement |
| `click` | Level 4/5: Mutation | **DENY** | Cannot verify effect target without firewall |
| `upload_file`| Level 4: External Mutation | **DENY** | External data transmission |
| `purchase` | Level 5: High-Impact | **DENY** | Financial / destructive effect |
| `delete` | Level 5: High-Impact | **DENY** | Irreversible data loss |
| *(unknown)* | Unknown Action | **DENY** | Fails closed on any unrecognized action |
