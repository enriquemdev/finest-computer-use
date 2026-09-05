# Installation & Lifecycle Management Guide

This document details how to install, verify, update, and remove **Finest Computer Use Safety**, whether on a brand-new Mac or an existing Antigravity installation.

---

## 1. Trust Boundaries & Architecture Responsibility

Finest Computer Use operates as an external, deterministic **safety and orchestration layer** between the agent reasoning engine and underlying desktop automation APIs.

```text
+-------------------------------------------------------------+
|                      Antigravity 2.0+                       |
|          (Agent Reasoning, Workspace, Tool Dispatch)        |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|               Finest Computer Use Safety Layer              |
|        (PreToolUse Hard Block, Taxonomy, Firewall,          |
|         Mutation Barrier, Task Isolation, Recovery)         |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                        Peekaboo MCP                         |
|        (Model Context Protocol Server for macOS UI)         |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                      macOS System APIs                      |
|         (Accessibility Tree, ScreenCaptureKit, TCC)         |
+-------------------------------------------------------------+
```

### Responsibility Breakdown:
- **macOS / Apple:** Manages system TCC privacy permissions (Accessibility, Screen Recording).
- **Peekaboo:** Manages direct low-level UI querying and OS event synthesis.
- **Finest Computer Use:** Enforces strict safety policies, blocks unanchored clicks, prevents adjacent side-effects, manages effect budgets, and isolates task states.
- **Antigravity:** Provides the developer agent interface and triggers configured hooks.

---

## 2. System Requirements

- **Operating System:** macOS 15.0+ (Sequoia or later) required by Peekaboo 4.3+ for modern ScreenCaptureKit automation.
- **Hardware Architecture:** Apple Silicon (`arm64`) or Intel (`x86_64`).
- **Python:** Python 3.9+ (System Apple Python, Homebrew Python, or Conda). No external package dependencies required (standard library only).
- **Antigravity:** Antigravity 2.0+ installed.
- **Peekaboo:** Peekaboo 4.0+ installed via Homebrew (`brew install steipete/tap/peekaboo`) or direct binary.

---

## 3. Recommended Onboarding: One-Command Bootstrap

For fresh setups, the automated bootstrap inspects prerequisites, registers MCP tools, and installs safety layers:

```bash
git clone https://github.com/enriquemdev/finest-computer-use.git
cd finest-computer-use
python3 scripts/bootstrap.py
```

### Bootstrap Options:
- `python3 scripts/bootstrap.py --dry-run`: Inspects all proposed changes without modifying the filesystem.
- `python3 scripts/bootstrap.py --check`: Runs diagnostic check only (exits 0=ready, 1=action required, 2=error).
- `python3 scripts/bootstrap.py --skip-mcp`: Skips automatic `mcp_config.json` modification.

---

## 4. Existing User Workflows

### Scenario A: Existing Antigravity User (Preserving Existing Configuration)
If you already use Antigravity with custom instructions in `~/.gemini/GEMINI.md`, other MCP servers in `mcp_config.json`, or custom hooks in `hooks.json`:
- `bootstrap.py` and `install.py` are strictly **non-destructive**.
- Your preexisting instructions, hooks, and MCP servers are preserved.
- Safety policies are cleanly merged between `<!-- finest-computer-use:start -->` and `<!-- finest-computer-use:end -->`.
- Automatic timestamped backups are stored in `~/.gemini/backup/`.

### Scenario B: Existing Peekaboo User
If Peekaboo is already installed and permissions are granted:
- `bootstrap.py` detects your existing binary and TCC status.
- Automatically links the existing Peekaboo executable into Antigravity MCP.

---

## 5. macOS Permissions (TCC) Guidance

Peekaboo requires two macOS permissions under **System Settings > Privacy & Security**:
1. **Screen & System Audio Recording:** Required to capture visual UI states and generate element maps.
2. **Accessibility:** Required to inspect the macOS Accessibility tree without focus shifting.

To verify permissions at any time:
```bash
python3 scripts/doctor.py
```

---

## 6. Verification & Healthcheck

After installation, verify full system health:
```bash
# Diagnostic inspection
python3 scripts/doctor.py

# Internal safety firewall test suite (30 checks)
python3 scripts/firewall_healthcheck.py

# Full regression harness (35 tests)
python3 tests/run_firewall_regression.py

# Non-invasive runtime smoke test
python3 scripts/smoke_test.py
```

---

## 7. Safe Updates & Staged Deployments

When updating Finest Computer Use:
```bash
git pull origin main
python3 scripts/bootstrap.py
```
Updates are validated using `py_compile` and tested before replacement. If a healthcheck failure occurs, the deployment automatically reverts to `.last_known_good`.

---

## 8. Uninstallation & Reversion

To completely remove the runtime and restore baseline settings:
```bash
python3 scripts/uninstall.py
```
This safely:
- Removes the managed block from `~/.gemini/GEMINI.md`.
- Unregisters the safety hook from `~/.gemini/config/hooks.json`.
- Removes runtime scripts from `~/.gemini/config/skills/computer-use/scripts/`.
- Preserves your preexisting configuration and historical backups in `~/.gemini/backup/`.
