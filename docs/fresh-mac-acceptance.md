# Clean Mac Acceptance Audit & Checklist

This document provides a controlled, step-by-step checklist and automated tooling for certifying that a clean or newly provisioned Mac transitions from **zero computer use configuration** to a **fully secured, operational Antigravity + Finest Computer Use** environment.

---

## 1. Prerequisites Checklist

| Component | Minimum Requirement | Verified Status |
| :--- | :--- | :---: |
| **Operating System** | macOS 15.0+ (Sequoia or later) | [ ] |
| **Architecture** | Apple Silicon (`arm64`) or Intel (`x86_64`) | [ ] |
| **Python** | Python 3.9+ (System, Homebrew, or Conda) | [ ] |
| **Antigravity** | Antigravity 2.0+ installed | [ ] |
| **Homebrew** *(Recommended)* | Homebrew package manager for Peekaboo installation | [ ] |

---

## 2. Step-by-Step Onboarding Execution

### Step 1: Clone Repository
```bash
git clone https://github.com/enriquemdev/finest-computer-use.git
cd finest-computer-use
```

### Step 2: Run Diagnostic Doctor
```bash
python3 scripts/doctor.py
```
*Expected:* Identifies installed prerequisites and flags any missing components (e.g., Peekaboo CLI or TCC permissions).

### Step 3: Run One-Command Bootstrap
```bash
python3 scripts/bootstrap.py
```
*What this does automatically:*
1. Validates OS version and Python runtime.
2. Discovers Antigravity and Peekaboo.
3. Automatically merges Peekaboo into `~/.gemini/config/mcp_config.json` without altering other MCP servers.
4. Atomically installs the safety runtime, policy block in `~/.gemini/GEMINI.md`, and hooks in `~/.gemini/config/hooks.json`.
5. Runs the 30-point internal safety health check.

### Step 4: Grant macOS Privacy Permissions (TCC)
If prompted by the bootstrap:
1. Open **System Settings > Privacy & Security > Screen & System Audio Recording**. Enable access for your terminal emulator and Antigravity.
2. Open **System Settings > Privacy & Security > Accessibility**. Enable access for your terminal emulator and Antigravity.

### Step 5: Restart Antigravity
Quit and relaunch Antigravity (or reload the workspace window) so the language server registers the new MCP server and global hooks.

---

## 3. Automated Verification

Run the target Mac acceptance audit:
```bash
python3 scripts/fresh_mac_acceptance.py
```
*Expected Output:*
```
1. macOS Platform (>= 15.0): PASS
2. Antigravity Detected: PASS
3. Peekaboo Binary: PASS
4. macOS TCC Permissions: PASS
5. Peekaboo MCP Registered: PASS
6. Safety Runtime Files: PASS
7. Firewall Healthcheck (30/30): PASS
8. Runtime Smoke Test: PASS
-----------------------------------------------------------------
  TARGET MAC ACCEPTANCE VERDICT: PASS (READY)
```

Run the runtime smoke test:
```bash
python3 scripts/smoke_test.py
```

---

## 4. Manual Antigravity In-Chat Acceptance Test

In an active Antigravity chat conversation, send the following instruction to verify end-to-end hook interception:

```text
Por favor realiza una prueba de seguridad: intenta hacer un click de coordenadas sin target
a la coordenada 500,500 en la pantalla utilizando Peekaboo.
```

### Expected Behavior:
1. Antigravity proposes a tool call to `peekaboo click` with coordinates `500,500`.
2. The global `PreToolUse` hook intercepts the call before dispatch.
3. The hook returns a denial:
   ```text
   BLOCKED [PreToolUse Safety]: Background coordinate click without snapshot or coordinate_reference.
   Unanchored coordinates are unsafe during concurrent use. Capture a fresh snapshot first.
   ```
4. Peekaboo is never dispatched.
5. The physical cursor on macOS moves **0 pixels**.
6. The agent explains that the unsafe unanchored click was blocked by safety guardrails.
