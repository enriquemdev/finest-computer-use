# Architecture Overview

Finest Computer Use is an external, deterministic safety supervisor designed for agentic desktop automation on macOS. It operates between the agent planner (e.g. Antigravity) and the underlying operating system automation interfaces (e.g. Peekaboo MCP).

---

## 1. System Layers

```
+-------------------------------------------------------------------+
|                        Agent Planner (LLM)                        |
|   (Antigravity Core / Subagent / Task Engine)                     |
+-------------------------------------------------------------------+
                                  |
                                  | Proposes ToolCall
                                  v
+-------------------------------------------------------------------+
|                      PreToolUse Hook Router                       |
|               (finest_computer_use/safe_interact.py)              |
|                                                                   |
|   [Fast-Path Evaluator]  < 20ms                                   |
|   - view_file, edit, developer shell (git, npm)  --> ALLOW        |
|                                                                   |
|   [Physical Invasiveness Validator]                               |
|   - Block mouse move, unanchored coords, targetless keys          |
+-------------------------------------------------------------------+
                                  |
                                  | (Non-fastpath actions)
                                  v
+-------------------------------------------------------------------+
|                     Intent / Effect Firewall                      |
|              (finest_computer_use/effect_firewall.py)             |
|                                                                   |
|   1. Monotonic Authorization Engine (User vs Agent provenance)   |
|   2. 6-Level Effect Taxonomy Classification (effect_taxonomy.py)  |
|   3. Task Effect Contract & Budget Enforcement                    |
|   4. Mutation Barrier (Observe -> Mutate -> Verify)               |
|   5. Recovery Mode State Machine                                  |
|   6. POSIX File Locking (Atomic state per conv_id + task_id)      |
+-------------------------------------------------------------------+
                                  |
                   +--------------+--------------+
                   |                             |
             Decision: DENY                Decision: ALLOW
                   |                             |
                   v                             v
+------------------------------------+  +----------------------------+
| Returns structured error response  |  | Dispatches to Peekaboo MCP |
| with explicit policy violation info|  | (macOS Accessibility API)  |
+------------------------------------+  +----------------------------+
                                                 |
                                                 v
                                        +----------------------------+
                                        |   PostToolUse Hook Router  |
                                        | - Consumes commit receipt  |
                                        | - Raises mutation barrier  |
                                        | - Decrements budget count  |
                                        +----------------------------+
```

---

## 2. Component Directory

- **`safe_interact.py`**:
  The primary entry point executed by the Antigravity hook runner on `PreToolUse` and `PostToolUse`. Contains the fast-path bypass for non-desktop commands, CLI subcommands for contract inspection/manipulation, and error interception.
- **`effect_firewall.py`**:
  Manages session states, JSON contracts, side-effect budgets, commit receipts, atomic file locking, and monotonic authorization rules.
- **`effect_taxonomy.py`**:
  Defines the 6 risk levels, semantic matching rules, forbidden keyword pairs, and fallback classifications for degraded modes.
- **`deploy_firewall.py`**:
  Ensures safe, atomic updates of firewall scripts using staging directories, `py_compile` checks, isolated import tests, and `.last_known_good` rollbacks.
- **`bootstrap.py`**:
  Orchestrates onboarding on fresh machines: preflight checks, Antigravity discovery, Peekaboo configuration, MCP merger, safety installation, and post-install doctor validation.
- **`doctor.py`**:
  Standalone diagnostic inspector reporting full system readiness and actionable guidance with standard exit codes.

---

## 3. Trust Boundary

Finest Computer Use is an independent safety layer with clearly separated operational boundaries:

```text
Antigravity (Agent Engine)
    ↓  PreToolUse Hook (<20ms)
Finest Computer Use (Deterministic Policy & Invasiveness Firewall)
    ↓  Allowed tool calls
Peekaboo (macOS Model Context Protocol Server)
    ↓  System Calls
macOS 15+ (Sequoia TCC & Accessibility Subsystem)
```

- **Antigravity** owns user session management, agent prompt evaluation, and hook triggering.
- **Finest Computer Use** owns deterministic invariant enforcement, side-effect budgets, and mutation barrier state.
- **Peekaboo** owns accessibility automation, screenshot capture, and event synthesis.
- **macOS** owns operating-system security, SIP, and user privacy consent (TCC).

---

## 4. Testing & Verification Levels

The architecture is verified across three distinct confidence tiers:
- **Level 1 — Portable (CI-safe):** AST compilation, isolated imports, contract lattices, recovery state transitions, and mock UI pipelines executed in headless environments (Linux / macOS).
- **Level 2 — Clean Environment Simulation:** Isolated temporary `$HOME` fixtures testing fresh bootstrap, idempotence, MCP merging, config preservation, failure injection, and uninstall.
- **Level 3 — Real Host Mac Integration:** Actual Antigravity runtime, live Peekaboo MCP, macOS Accessibility & Screen Recording TCC permissions, and non-invasive smoke tests.
