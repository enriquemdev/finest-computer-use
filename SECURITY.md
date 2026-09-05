# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in **Finest Computer Use**, please do NOT open a public GitHub issue.

Please report vulnerabilities privately:
- Contact: Security Team / Repository Maintainer (`enriquemdev`) via GitHub Private Vulnerability Reporting or email.
- Include a detailed description of the vulnerability, steps to reproduce, and any proposed mitigation.

You should receive an acknowledgment within 24–48 hours.

---

## Security Model & Threat Guarantees

Finest Computer Use operates on defense-in-depth principles:

1. **PreToolUse Hard Enforcement:**  
   Safety checks are executed as an external process hook BEFORE any action reaches Peekaboo or the operating system. Even if an LLM hallucinates, ignores prompt guidelines, or receives adversarial instructions via prompt injection, the hook enforces policy deterministically.

2. **Monotonic Authorization:**  
   Only user instructions can grant permission for external effects (Level 4) or destructive actions (Level 5). Agents cannot autonomously escalate their privileges, broaden targets, or increase effect budgets.

3. **Anti-Brick / Anti-Fail-Open Invariant:**  
   If the safety hook encounters an unexpected runtime error:
   - Benign developer tools (`git`, `view_file`, shell commands) are allowed so the user/agent can repair the environment.
   - Mutating desktop and browser actions are DENIED (`fail-closed`).

4. **Rollback & Recovery:**  
   Every deployment creates a `.last_known_good` backup. In the event of healthcheck failure during an update or installation, the runtime reverts automatically.
