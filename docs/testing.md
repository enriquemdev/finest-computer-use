# Testing & Verification Guide

The test harness provides comprehensive, standalone verification without needing real desktop clicks or side effects.

---

## 1. Running the Health Check (30 Checks)

```bash
python3 scripts/firewall_healthcheck.py
```
Validates:
- Syntax of all Python modules (`py_compile`).
- Subprocess imports in clean Python environments.
- Hooks JSON configuration validity.
- Fast-path execution speed (< 200ms).
- Physical guardrails (mouse drift, unanchored coordinates).
- True task-level state isolation.
- Monotonic authorization engine.
- Degraded mode behavior.

---

## 2. Running the Full Regression Suite (35 Tests)

```bash
python3 tests/run_firewall_regression.py
```
Covers:
- Tests A–K: Foundation guardrails, semantic mismatches, budgets, shell bypasses.
- Test L: Natural language contract generation.
- Tests M–O: True E2E mock UI scenarios using `tests/mock_ui/mock_ui.html`.
- Tests P–R: Degraded mode, session concurrency, developer autonomy.
- Tests S–W: Monotonic authorization lattice.
- Tests X–AA: True task-level isolation.
- Tests AB–AF: Granular degraded browser classification.
- True E2E Tests 1–3: Complete end-to-end integration flows.
