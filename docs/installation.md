# Installation & Lifecycle Management

## 1. Automated Installation

Run the idempotent installer from the repository root:
```bash
python3 scripts/install.py
```

### What the installer does:
1. **Creates a full backup** of your existing configuration in `~/.gemini/backup/computer-use-safety-<timestamp>/`.
2. **Pre-compiles all Python modules** using `py_compile` to guarantee zero syntax or indentation errors.
3. **Copies runtime modules** to `~/.gemini/config/skills/computer-use/scripts/`.
4. **Installs the skill definition** to `~/.gemini/config/skills/computer-use/SKILL.md`.
5. **Merges the managed policy block** into `~/.gemini/GEMINI.md` within `<!-- finest-computer-use:start -->` and `<!-- finest-computer-use:end -->` delimiters.
6. **Registers PreToolUse and PostToolUse hooks** in `~/.gemini/config/hooks.json`.
7. **Runs a 30-point health check** against the installed live system.
8. **Automatic Rollback:** If any step or health check fails, the installer immediately restores the previous backup.

---

## 2. Uninstallation & Reversion

To completely remove the runtime and restore baseline settings:
```bash
python3 scripts/uninstall.py
```
This removes the managed block from `GEMINI.md`, unregisters the hook from `hooks.json`, and deletes installed scripts while preserving your historical backups in `~/.gemini/backup/`.
