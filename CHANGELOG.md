# Changelog

All notable changes to the **Finest Computer Use Safety** architecture are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.2] - 2026-09-05

### MCP Conflict Protection, Unified Discovery & Truthful Evidence Semantics

This patch release closes four concrete onboarding and evidence gaps identified in v1.1.1 without altering the frozen Computer Use Safety core.

#### Fixed & Endured
- **Existing Custom Peekaboo MCP Conflict Protection (`scripts/bootstrap.py`)**:
  - Distinguishes unmanaged or custom Peekaboo configurations (differing binary paths, customized arguments, environment variables, or other properties) from default Finest installations.
  - Never mutates or overwrites user-customized configurations; emits `ACTION REQUIRED` and leaves the existing file completely untouched (Cases A–F validated).
  - Explicitly marks managed entries with `_finest_managed: True` while migrating legacy Finest configurations safely.
- **Canonical-vs-Legacy MCP Doctor Semantics (`scripts/doctor.py`)**:
  - Recognizes `~/.gemini/config/mcp_config.json` as the sole authoritative canonical configuration.
  - Correctly reports `ACTION REQUIRED` when Peekaboo is registered only in legacy `~/.gemini/antigravity/mcp_config.json`.
  - Transparently identifies symlink equivalence via inode verification (`os.path.samefile`).
  - Reports `ERROR` / `ACTION REQUIRED` when the canonical file is malformed, even if the legacy file is valid.
- **Unified Antigravity Discovery Logic (`src/finest_computer_use/discovery.py`)**:
  - Implemented single-source reusable discovery module (`AntigravityDiscovery`, `is_valid_app_bundle`, `discover_antigravity`).
  - Unified detection across `scripts/bootstrap.py`, `scripts/doctor.py`, and `scripts/fresh_mac_acceptance.py`.
  - Rejects empty app directories and ensures valid macOS executable bundles (`Contents/MacOS/<binary>`).
- **Truthful Smoke & Acceptance Status Reporting (`scripts/smoke_test.py`, `scripts/fresh_mac_acceptance.py`)**:
  - Eliminated misleading "4/4 PASS" and "ALL RUNTIME GUARDS FUNCTIONING" claims from standalone executions.
  - Accurately reports `AUTOMATED SMOKE CHECKS: 3/3 PASS`, `REAL ANTIGRAVITY HOOK E2E: NOT EXECUTED`, and `OVERALL STATUS: PASS WITH MANUAL E2E PENDING`.
  - Acceptance report explicitly logs `TARGET MAC ACCEPTANCE VERDICT: READY WITH DOCUMENTED MANUAL EVIDENCE PENDING`.

---

## [1.1.1] - 2026-09-05

### Onboarding Correctness, Evidence Quality & Release Consistency

This patch release hardens the clean-machine onboarding pipeline, refines discovery semantics, eliminates configuration risk, introduces capability probing, and enforces rigorous evidence classification.

#### Fixed & Endured
- **Canonical MCP Configuration Isolation (`scripts/bootstrap.py`)**:
  - Targets only the canonical global MCP path (`~/.gemini/config/mcp_config.json`).
  - Completely preserves any secondary or legacy configuration files (`~/.gemini/antigravity/mcp_config.json`) without destructive overwrite.
  - Adds atomic writes via sibling `.tmp.<pid>` files, `fsync`, post-write validation, and automatic rollback on malformed input or write error.
- **Antigravity Discovery Verification (`scripts/bootstrap.py`, `scripts/doctor.py`)**:
  - Enforces macOS app bundle structural integrity (verifies executable binary inside `Contents/MacOS/`).
  - Reclassifies config-only state (`~/.gemini` present without confirmed app bundle or CLI) as `ACTION REQUIRED` rather than false positive `PASS`.
- **Peekaboo Capability Readiness Probes (`scripts/doctor.py`)**:
  - Added granular capability probes (`probe_peekaboo_mcp`, `probe_peekaboo_permissions`, `probe_peekaboo_observation`, `probe_peekaboo_capabilities`).
  - Validates that the installed Peekaboo binary supports the required `mcp` subcommand and non-invasive read-only observation.
- **Evidence Categorization & Honest Semantics (`scripts/smoke_test.py`, `scripts/fresh_mac_acceptance.py`)**:
  - Clear 4-section smoke test explicitly distinguishing standalone handler smoke from host Antigravity PreToolUse hook dispatch (`REAL ANTIGRAVITY HOOK E2E: NOT EXECUTED`).
  - Structured acceptance report annotating each check with confidence tiers (`PORTABLE`, `HOST_INTEGRATION`, `FIXTURE`, `ANTIGRAVITY_E2E`, `TRUE_CLEAN_MAC_E2E`).
  - Retains honest declaration that physical virgin-machine validation is unexecuted (`TRUE CLEAN MAC E2E: NOT EXECUTED`).
- **Deterministic Release Manifest (`scripts/generate_manifest.py`)**:
  - Introduced automated manifest generator supporting deterministic SHA-256 generation, cryptographic verification (`--verify`), and cross-surface version reconciliation (`--check-version`).

---

## [1.1.0] - 2026-09-05

### Clean-Machine Onboarding & Diagnostic Tooling

This release introduces comprehensive, production-grade clean-machine onboarding, multi-tier system diagnostics, and automated lifecycle testing for transitioning fresh macOS environments into verified, secure Computer Use workstations.

#### Added
- **One-Command Onboarding Orchestrator (`scripts/bootstrap.py`)**:
  - Automated detection of Antigravity installation and discovery paths.
  - Idempotent registration of Peekaboo MCP in `~/.gemini/config/mcp_config.json` while preserving preexisting servers.
  - Support for `--dry-run` (zero filesystem mutations), `--check`, `--json`, `--skip-mcp`, and `--home=<dir>`.
- **Multi-Tier Diagnostics Inspector (`scripts/doctor.py`)**:
  - Standardized preflight checks across OS (macOS 15+ Sequoia), Python (>= 3.9), Antigravity discovery, Peekaboo CLI, macOS TCC permissions, MCP config, and runtime integrity.
  - Standardized exit codes: `0 = Ready`, `1 = Action Required`, `2 = Critical Error`.
  - Non-invasive TCC verification using `peekaboo permissions --json`.
- **Safe Runtime Smoke Test (`scripts/smoke_test.py`)**:
  - Verifies live background semantic inspection without mouse movement.
  - Validates active firewall rejection of unanchored coordinate clicks.
- **Clean-Machine Acceptance Test Harness (`scripts/fresh_mac_acceptance.py`)**:
  - 8-stage audit certifying clean start, preflight, bootstrap, doctor, regression, and smoke test.
- **Clean-Machine Lifecycle Test Suite (`tests/test_fresh_install.py`)**:
  - 31 automated tests verifying virgin installation, dry-run zero-mutation, idempotence, user config preservation, safe uninstallation, and staged syntax error rollback.
- **Hardened Documentation**:
  - `docs/troubleshooting.md`: Concrete diagnostic workflows for 7 common failure classes.
  - `docs/fresh-mac-acceptance.md`: Acceptance test procedure and certification matrix.
  - Updated `docs/installation.md` and `docs/architecture.md` with explicit macOS 15+ requirements and testing tier definitions.

---

## [1.0.0] - 2026-09-05

### Initial Release — Computer Use Safety Architecture Freeze

This release establishes the baseline production safety architecture for macOS desktop computer use by agentic AI systems.

#### Added
- **Non-Invasive Computer Use Policy (Tiers 0–4)**:
  - Strict hierarchical preference: Structured Interfaces (Tier 0) -> Background Semantic (Tier 1) -> Background Coordinate (Tier 2) -> Foreground Semantic (Tier 3) -> Foreground Coordinate (Tier 4).
  - Enforced zero unanchored coordinate clicks and absolute prohibition of targetless mouse drifts.
- **6-Level Effect Taxonomy**:
  - Formal classification across Level 0 (Pure Observation) to Level 5 (High-Impact / Destructive).
  - Semantic alignment evaluator comparing target accessibility labels with task intent keywords.
  - Automatic detection of adjacent high-impact controls (e.g. voice record adjacent to text send).
- **PreToolUse Hard Interception**:
  - Global `PreToolUse` hook running before tool execution.
  - Ultra-fast native tool bypass router (< 20ms) ensuring zero developer friction for native commands (`view_file`, `run_command(git)`, `replace_file_content`).
- **Monotonic Authorization Engine**:
  - Provenance-aware authorization distinguishing `user` vs `agent` origins.
  - Formal restriction: Agents may only narrow scopes (e.g. specific thread IDs or files) and can never autonomously expand effect budgets or authorize new Level 4/5 actions.
- **True Task-Level State Isolation**:
  - Multi-task execution state keyed by composite `(conversation_id, task_id)`.
  - Atomic POSIX filesystem locking (`fcntl.flock`) preventing race conditions during concurrent subagent execution.
  - Cross-task barrier and receipt isolation preventing stolen commit tokens or shared recovery states.
- **Mutation Barriers & Target-Bound Verification**:
  - Mandatory `OBSERVE -> MUTATE -> VERIFY` cycle for external actions.
  - Unrelated observations (e.g. checking system settings) cannot clear mutation barriers for target applications.
- **Recovery Mode & Safe Baseline**:
  - Automatic transition to `RECOVERY_MODE` when unexpected UI state is encountered (e.g., active audio recording or modal dialog).
  - Gating: all mutations blocked until safe baseline is restored.
- **Fail-Safe Degraded Mode (Anti-Brick + Anti-Fail-Open)**:
  - In the event of an internal firewall exception or syntax corruption, benign developer tools remain operational while all desktop/browser mutations fail closed.
  - Granular browser action classification allowing read-only inspection (`snapshot`, `console`, `network`) and reversible navigation (`navigate`), while blocking mutation actions (`click`, `upload_file`, `purchase`).
- **Staged Safe Deployment & Rollback**:
  - Staged compilation (`py_compile`) and isolated subprocess imports before updating active modules.
  - Immediate atomic rollback to `.last_known_good` upon syntax error or test failure.
- **Verification Suites**:
  - 35-test comprehensive regression test suite (`tests/run_firewall_regression.py`).
  - 30-point standalone healthcheck verification runner (`scripts/firewall_healthcheck.py`).
