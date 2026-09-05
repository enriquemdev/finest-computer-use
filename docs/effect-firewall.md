# Intent / Effect Firewall Specification

The Intent / Effect Firewall (`effect_firewall.py`) is the core stateful policy engine of Finest Computer Use.

---

## 1. Task Effect Contracts

Before an agent may execute Level 4 (External) or Level 5 (Destructive) actions, a **Task Effect Contract** must be established.

### Schema
```json
{
  "goal": "communication.send_text",
  "limits": {
    "communication.send_text": 1
  },
  "forbidden": [
    "communication.send_voice",
    "destructive.delete"
  ],
  "profile": "standard",
  "targets": {
    "communication.send_text": "Slack/#general"
  }
}
```

Contracts can be established explicitly via the CLI:
```bash
python3 safe_interact.py contract "communication.send_text" '{"communication.send_text": 1}' '["communication.send_voice"]' standard <conv_id> <task_id> user '{"communication.send_text": "Slack/#general"}'
```
or generated automatically from the natural language prompt via `auto_create_contract_from_intent()`.

---

## 2. Monotonic Authorization Rules

Contracts follow strict monotonic lattices:
1. **Provenance:** Each update specifies `source="user"` or `source="agent"`.
2. **Expansion Prohibition:** If `source == "agent"`:
   - No new Level 4 or Level 5 effect keys can be added to `limits`.
   - No numeric budget in `limits` can exceed the existing value.
   - Target specifications cannot be broadened (e.g. changing `Slack/#general` to `*` is denied).
3. **Narrowing Allowed:** If `source == "agent"`, the agent may restrict targets (e.g. from `Slack/*` to `Slack/#team-lead`).

---

## 3. Commit Receipts & Mutation Barriers

### The Execution Lifecycle:
1. **Proposal (PreToolUse):**
   - Agent proposes an action (e.g. `peekaboo click(send)`).
   - Firewall checks:
     - Is recovery mode active? (If yes, DENY).
     - Is mutation barrier active? (If yes, DENY).
     - Is there sufficient budget? (If no, DENY).
     - Does element match contract semantics? (If no, DENY).
   - If allowed, an in-memory or on-disk **Commit Receipt** is issued for that specific tool call and task.
2. **Dispatch:**
   - Tool executes via Peekaboo MCP.
3. **Completion (PostToolUse):**
   - PostToolUse consumes the commit receipt.
   - Decrements remaining budget by 1.
   - Raises the **Mutation Barrier**.
4. **Verification Requirement:**
   - The agent MUST call a target-bound observation (`peekaboo see` on target app) before any further mutation is allowed.
   - Unrelated observations do not lower the barrier.
