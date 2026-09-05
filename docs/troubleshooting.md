# Troubleshooting & Operational Diagnostics Guide

This guide covers resolution strategies for common onboarding, permission, runtime, and configuration issues.

---

## 1. Quick Diagnostic: Run the System Doctor

Whenever you encounter an unexpected state or error, run:
```bash
python3 scripts/doctor.py
```
`doctor.py` inspects every layer of the stack (OS version, Antigravity, Peekaboo, TCC permissions, MCP config, hooks, and firewall state) and emits actionable next steps.

---

## 2. Common Issues & Solutions

### Issue A: `peekaboo: command not found`
- **Cause:** Peekaboo is not installed or its binary directory is not in your shell's `$PATH`.
- **Diagnosis:** Run `which peekaboo`.
- **Solution:**
  - If using Homebrew:
    ```bash
    brew install steipete/tap/peekaboo
    ```
  - If installed manually in a custom path, ensure `/opt/homebrew/bin` (Apple Silicon) or `/usr/local/bin` (Intel) is included in your shell profile (`~/.zshrc` or `~/.bashrc`).

### Issue B: Accessibility or Screen Recording Permission Denied
- **Cause:** macOS Transparency, Consent, and Control (TCC) has not granted required capabilities to Terminal, iTerm2, or Antigravity.
- **Diagnosis:** Run `peekaboo permissions` or `python3 scripts/doctor.py`.
- **Solution:**
  1. Open **System Settings > Privacy & Security > Screen & System Audio Recording**. Enable access for your terminal emulator and Antigravity.
  2. Open **System Settings > Privacy & Security > Accessibility**. Enable access for your terminal emulator and Antigravity.
  3. Quit and reopen the application if prompted by macOS.

### Issue C: Peekaboo MCP Disconnected or Tools Not Visible in Antigravity
- **Cause:** `mcp_config.json` is missing the `peekaboo` entry, or Antigravity was running when the file was edited.
- **Diagnosis:** Inspect `~/.gemini/config/mcp_config.json`.
- **Solution:**
  1. Run the automatic merger:
     ```bash
     python3 scripts/bootstrap.py
     ```
  2. Restart the Antigravity application or reload the workspace window to trigger MCP server discovery.

### Issue D: Safety Hooks Not Intercepting (`safe_interact.py`)
- **Cause:** `~/.gemini/config/hooks.json` does not contain the `computer-use-safety` section, or points to an invalid script path.
- **Diagnosis:** Run `python3 scripts/doctor.py`.
- **Solution:**
  1. Re-register hooks idempotently:
     ```bash
     python3 scripts/install.py
     ```
  2. Confirm `~/.gemini/config/hooks.json` contains:
     ```json
     "computer-use-safety": {
       "enabled": true,
       "PreToolUse": [{ "matcher": "*", "hooks": [{ "command": "python3 /path/to/safe_interact.py" }] }],
       "PostToolUse": [{ "matcher": "*", "hooks": [{ "command": "python3 /path/to/safe_interact.py post" }] }]
     }
     ```

### Issue E: Fail-Safe Degraded Mode Active
- **Cause:** An unhandled exception or missing dependency occurred in the advanced firewall module.
- **Symptom:** Terminal commands (`git`, `ls`, file edits) still work normally (anti-brick), but desktop clicks or browser mutations return `BLOCKED [Degraded Mode]`.
- **Solution:**
  1. Run `python3 scripts/firewall_healthcheck.py` to identify the syntax error or missing module.
  2. Use the safe staged deployer to reinstall the good module:
     ```bash
     python3 scripts/install.py
     ```

### Issue F: Duplicate Configuration Blocks After Manual Edits
- **Cause:** Multiple manual pastes of `GEMINI.md` policy blocks or `hooks.json` entries.
- **Solution:**
  - `scripts/install.py` and `scripts/bootstrap.py` are strictly idempotent. Running `python3 scripts/install.py` automatically searches for existing `<!-- finest-computer-use:start -->` and `<!-- finest-computer-use:end -->` delimiters, replacing redundant blocks with a single clean managed block.

### Issue G: Corrupted Staged Updates
- **Cause:** Modifying live runtime scripts directly with syntax errors.
- **Solution:**
  - Always use `scripts/deploy_firewall.py` for staging. If an update fails, restore from the last known good backup:
    ```bash
    python3 scripts/deploy_firewall.py --rollback safe_interact.py
    ```
