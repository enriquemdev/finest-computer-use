# Changelog

All notable changes to the **Finest Computer Use Safety** architecture are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
