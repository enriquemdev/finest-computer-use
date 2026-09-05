# Contributing Guidelines

Thank you for contributing to **Finest Computer Use**.

## Development Workflow

1. Fork the repository and create a branch for your feature or fix.
2. Ensure Python 3.9+ is installed.
3. Make changes in `src/finest_computer_use/` or related documentation.
4. Run syntax verification:
   ```bash
   python3 -m py_compile src/finest_computer_use/*.py scripts/*.py tests/*.py
   ```
5. Run the healthcheck and regression suites:
   ```bash
   python3 scripts/firewall_healthcheck.py
   python3 tests/run_firewall_regression.py
   ```
   All 30 health checks and 35 regression tests MUST pass.

## Commit Conventions

- Use [Conventional Commits](https://www.conventionalcommits.org/) (e.g. `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`).
- Do NOT include `Co-Authored-By` or AI attribution trailers in commit messages.

## Staged Deployments

When modifying live firewall components, use `scripts/deploy_firewall.py` which enforces the staging pipeline:
`WRITE STAGING -> PY_COMPILE -> ISOLATED IMPORT TEST -> BACKUP LKG -> ATOMIC REPLACE -> HEALTH CHECK -> CONFIRM`.
