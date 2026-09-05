# Platform Scope & Limitations

## 1. Supported Platforms
- **macOS (Sonoma 14, Ventura 13, Sequoia 15):** Full desktop automation and Accessibility tree inspection via Peekaboo MCP.
- **Linux / CI:** Full support for syntax verification, policy parsing, CLI commands, mock DOM evaluation, and unit regression testing.

## 2. macOS Accessibility Tree Quirks
- Certain Electron or WebKit applications may defer populating accessibility elements until the window is focused. Use Tier 1 background observation first; if elements are missing, proceed to Tier 3 (focused semantic interaction).
- Ambiguous icon buttons without explicit `AXDescription` attributes trigger the Unknown High-Impact control guardrail and require human confirmation.

## 3. Sandboxing & Permissions
- Peekaboo requires macOS Accessibility permissions (`System Settings -> Privacy & Security -> Accessibility`) and Screen Recording permissions.
