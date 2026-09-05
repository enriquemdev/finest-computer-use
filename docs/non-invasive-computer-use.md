# Non-Invasive Computer Use Policy

Finest Computer Use operates under the premise that the human user is actively working on their Mac simultaneously with the agent. An agent must never hijack user focus, steal the cursor, or disrupt user typing.

---

## The Non-Invasive Hierarchy

### Tier 0: Structured Interfaces (Highest Priority)
- Always prefer CLI tools, APIs, filesystems, or domain-specific MCP servers over GUI automation.
- Never use GUI clicks to inspect files or run terminal commands.

### Tier 1: Background Semantic Actions (Default GUI Mode)
- Query macOS Accessibility Tree without moving the cursor or bringing apps to the foreground.
- Use `peekaboo see` and `peekaboo inspect_ui` in the background.
- Use `peekaboo set_value` to modify input fields without keystroke injection into foreground windows.
- Use `peekaboo menu` and `peekaboo window` APIs.

### Tier 2: Background Coordinate Actions (Anchored Only)
- Coordinate actions (`click --at X,Y`) are ONLY permitted if strictly anchored to a fresh snapshot receipt and a specific target window/app.
- Unanchored global clicks (`click` with coordinates but no window or element anchor) are blocked by the firewall.

### Tier 3: Foreground Semantic Actions
- Used only when background accessibility APIs cannot access the control.
- Procedure:
  1. Capture fresh snapshot.
  2. Activate target window.
  3. Execute single semantic action (`click` by element UID/label).
  4. Immediately verify outcome.
  5. Release foreground focus.

### Tier 4: Foreground Coordinate Actions (Last Resort)
- Strictly guarded.
- Requires immediate re-observation right before clicking to ensure cursor coordinates haven't drifted.
- Exactly one action permitted, followed immediately by verification.
