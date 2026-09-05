<!-- finest-computer-use:start -->
## macOS Computer Use — Non-Invasive First Policy

Assume the user is actively using the Mac concurrently at all times:
- **Tier 0 (Structured Interfaces)**: Prefer CLI, API, filesystem, or domain-specific MCP before GUI.
- **Tier 1 (Background Semantic - Default)**: Use Accessibility tree (`see`, `inspect_ui`), `set_value`, `dialog`, `menu`, `window` without moving the user's cursor or activating windows.
- **Tier 2 (Background Coordinate)**: Only if strictly anchored to exact application, window, and fresh snapshot receipt. Never use unanchored global coordinates (`click --at X,Y --foreground` without target).
- **Tier 3 (Foreground Semantic)**: When background fails, take a fresh snapshot, activate minimum target app, execute minimal action, verify, and release foreground.
- **Tier 4 (Foreground Coordinate - Last Resort)**: Re-observe immediately before clicking, execute exactly one action, and verify immediately.
- **Stale State Protection**: Never guess on stale snapshots. STALE -> RE-OBSERVE -> RE-RESOLVE TARGET -> ACTION. User activity wins.
- **Authorized Effects Only**: Execute only actions matching user-authorized intent. User intent authorizes expected effects, never adjacent ones (e.g. text-send never authorizes voice/call/file).
- **Unknown High-Impact Fails Closed**: If target control is ambiguous or opaque during Level 4/5 actions (send, submit, delete, buy), DO NOT guess.
- **Unexpected State Triggers Recovery**: If an action triggers an unexpected UI state (e.g. recording starts instead of text sent), immediately abort transaction, enter RECOVERY MODE, and cancel/undo before proceeding.
<!-- finest-computer-use:end -->
