---
name: computer-use
description: Comprehensive, hardened guide for macOS desktop automation using Peekaboo MCP tools. Enforces the Non-Invasive First hierarchy (Tiers 0-4), strict snapshot receipt validation, zero unanchored coordinate clicks, and user concurrency protection.
---

# macOS Computer Use with Peekaboo — Hardened Operational Guide

## Core Architectural Policy: Non-Invasive First, Foreground When Necessary

You operate concurrently on macOS while the user actively works. The user's physical mouse cursor, screen focus, and active window belong to the user.
- **Default mode**: Work silently in the background using Accessibility and structured APIs.
- **Escalation policy**: Foreground is permitted when technically necessary for task correctness. Do not sacrifice task execution for background dogmatism.
- **Rule of Thumb**: `BACKGROUND METHOD AVAILABLE? YES -> Use it. NO -> Foreground justified (minimal window, revalidate, verify, restore).`

---

## The 5-Tier Interaction Hierarchy

### Tier 0 — Structured Interfaces (Always Check First)
Before invoking graphical Computer Use, check if the task can be achieved faster, more reliably, and invisibly via:
1. Shell commands / Terminal scripts (`run_command`).
2. Domain-specific APIs or MCP servers (e.g. database, filesystem, engram).
3. Filesystem operations directly.
4. Application AppleScript / `osascript` or CLI utilities.
*Never use visual GUI automation when a clean structured interface is available.*

### Tier 1 — Background Semantic Interaction (Default for GUI)
For macOS applications with Accessibility support:
- **Observation**: `see(app_target: "AppName")` or `window_id` to inspect without activating or raising windows.
- **Text Entry**: `set_value(on: "elem_id", value: "text")` directly into `AXTextArea` or `AXTextField`. Zero keystroke synthesis, zero cursor movement.
- **Dialogs & Sheets**: `dialog(action: "click", button: "...", app: "AppName")`. Never calculate manual coordinates for standard buttons (Save, Cancel, Delete, Don't Save).
- **Menus**: `menu(action: "list", app: "AppName")` and `menu(action: "click", app: "AppName", path: "...")` via background AX.
- **Scrolling**: `set_value(on: "scroll_bar_id", value: target_float)` or element-targeted scroll.
- **Windows**: `window(action: "close|minimize|set-bounds", app: "...", window_id: ...)` in background.

### Tier 2 — Background Coordinate Interaction (Strictly Anchored)
If an element lacks an actionable AX role but Peekaboo allows background coordinate delivery:
- **MANDATORY**: Must be anchored to an exact application, exact `window_id`, and a fresh `snapshot` receipt (`ps1_...`).
- **PROHIBITED**: Unanchored global display coordinates without target receipts.

### Tier 3 — Foreground Semantic Interaction (Justified Escalation)
When background execution fails or is rejected by security policies:
1. Capture fresh state: `see(app_target: "AppName")`.
2. Activate ONLY the minimal necessary app: `app(action: "focus", name: "AppName")`.
3. Target the specific element semantically (`action: "AXPress"` or semantic click).
4. Verify immediately with a fresh capture.
5. Release foreground / return to background immediately.

### Tier 4 — Foreground Coordinate Interaction (Last Resort)
When an element cannot be addressed semantically (e.g., non-accessible Canvas, custom graphics):
1. **Re-observe immediately before clicking**: Do not reuse observations made seconds ago.
2. Confirm target presence, window bounds, and application identity.
3. Perform **exactly one** action: `click(coords: "x,y", foreground: true)`.
4. Re-observe immediately to verify the outcome.
5. **NEVER** chain multiple unverified global clicks based on an old observation.

---

## Absolute Prohibitions & Guardrails

1. **Banned Pattern: Unanchored Global Coordinate Clicks**
   - Commands like `peekaboo click --at X,Y --foreground` without explicit window/app/snapshot context are strictly forbidden. If the user moves a window or switches apps, an unanchored click causes dangerous misclicks.
2. **User Concurrency Assumption**
   - Between `observation` and `action`, the user may have switched apps, moved a window, scrolled, or typed.
   - Always validate that the target window and element are unchanged.
3. **Snapshot Lifecycle Protection (`ps1_...`)**
   - Every `see` returns a receipt `ps1_<32-hex>`.
   - If a mutation fails with a stale receipt error: **STALE -> RE-OBSERVE -> RE-RESOLVE TARGET -> ACTION**. Never guess coordinates after a stale error.
4. **Dangerous Actions Safeguard**
   - Actions involving deletion, closing unsaved work, system settings, or irreversible states require double observation and explicit semantic target resolution. Never use coordinate clicking for destructive choices.
5. **Restoring User Context (Conservative — USER ACTIVITY WINS)**
   - Before foreground escalation: `previous_app = get_current_frontmost_app()`.
   - Execute minimal atomic foreground operation.
   - Before restoring: `current_frontmost = get_current_frontmost_app()`.
   - **Algorithm**:
     ```text
     IF current_frontmost == agent_target_app:
         restore(previous_app)
     ELSE:
         skip_restoration()  # User switched apps; user activity wins.
     ```
6. **Hard PreToolUse Enforcement Hook**
   - A global `PreToolUse` hook (`~/.gemini/config/hooks.json` -> `scripts/safe_interact.py`) actively intercepts all Peekaboo calls.
   - Automatically denies unanchored coordinate clicks, targetless global keystrokes, and physical `move` commands before dispatch.
7. **Background Cold Launch (Tier 0)**
   - To open an application silently in the background without stealing focus or raising windows, use macOS Tier 0 LaunchServices:
     `open -g -a <AppName>` (e.g. `open -g -a Calculator`).

---

## Computer Use Intent / Effect Firewall

### 1. Philosophy: Authorized Effects Only
The agent may execute actions necessary to fulfill the user's request, but MUST NOT produce unintended persistent, external, or destructive side-effects. Explicit user intent authorizes only requested effects—never adjacent effects (e.g. text-send never authorizes voice recording, phone calls, reactions, or file uploads).

### 2. Effect Taxonomy (Levels 0–5)
- **Level 0 (Observation)**: `see`, `inspect_ui`, `capture`, `image`, `browser`, `verify_state`, read-only shell (`ls`, `grep`). Default: **ALLOW**.
- **Level 1 (Reversible Navigation)**: `scroll`, `window(focus/switch/list)`, `menu(list)`. Default: **ALLOW** with non-invasive checks.
- **Level 2 (Reversible Local Mutation)**: `set_value` into draft text fields, local form editing. Default: **ALLOW**.
- **Level 3 (Persistent Mutation)**: `window(close)`, `menu(Save)`, configuration changes. Requires **Effect Alignment + Post-Verification**.
- **Level 4 (External Side Effect)**: `communication.send_text`, `communication.send_voice`, `communication.call`, `external.submit`, mic/camera activation. Requires **Preflight + Budget + Two-Phase Commit + Immediate Verification**.
- **Level 5 (Destructive / Sensitive)**: File deletion (`rm`, delete button), financial purchase/transfer, permissions grants. **Fails closed on ambiguity; requires strict alignment**.

### 3. Semantic Effect Alignment & Fail-Closed Rule
- Before any mutation, compare **Intended Effect** against **Target Semantics**:
  - `send_text` vs target containing `voice|audio|mic|record|call` -> **MISMATCH -> HARD DENY**.
  - `save` vs target containing `discard|cancel|delete` -> **MISMATCH -> HARD DENY**.
  - `close` vs target containing `delete|trash|wipe` -> **MISMATCH -> HARD DENY**.
- **Unknown High-Impact Controls**: If a control is ambiguous/unlabeled during Level 4/5 actions -> **FAIL CLOSED (DO NOT GUESS)**.

### 4. Side-Effect Budgets & Mutation Barrier
- **Budget Enforcement**: Each authorized external effect has a strict count limit (e.g. `send_text: 1`). Second commits are blocked to prevent duplicate transmissions.
- **Mutation Barrier**: Enforces `OBSERVE -> ONE IMPORTANT MUTATION -> VERIFY -> CONTINUE`. After a Level 3+ mutation, further high-impact mutations are blocked until an observation confirms state transition.

### 5. Expected State Transitions & Recovery Mode
- **Expected != Actual**: If an action does not produce the expected state (e.g. voice recording starts instead of text sent), the transaction immediately aborts and enters **RECOVERY MODE**.
- **Recovery Gating**: While in recovery mode, ONLY observation and safe recovery operations (`cancel`, `undo`, `stop recording`, `back`) are permitted. All new external commits (`send`, `submit`, `Return`) are blocked until safe state is verified and resolved.

---

## Metric Tracking Contract
For every Computer Use operation, maintain an accurate internal tally:
- AX/semantic background operations
- Background clicks / set_value / dialog calls
- Foreground activations
- Physical cursor movements (Target: 0)
- Global unanchored coordinate clicks (Target: 0)
- Stale snapshot rejections & forced re-observations
- Unauthorized high-impact effects blocked
- Recovery mode transitions & resolutions
