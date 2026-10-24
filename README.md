# Antigravity Window Size Persistence for macOS

A zero-dependency Python utility to automatically persist and restore the window size, position, and maximized state of **Antigravity.app** on macOS.

---

## Features

- **Automatic App Detection**: Finds `Antigravity.app` in `/Applications`, `~/Applications`, or via Spotlight (`mdfind`).
- **Smart Window Persistence**:
  - Automatically restores previous window dimensions and screen coordinates from `~/Library/Application Support/Antigravity/app_storage.json`.
  - Preserves and restores maximized window state across launches.
  - Multi-monitor safety: repositions the window to an active display if a secondary monitor was disconnected.
  - Debounced listeners on `resize`, `move`, and `close` events for smooth performance.
- **Zero External Dependencies**: Built entirely with Python 3 standard library modules (`struct`, `json`, `hashlib`, `plistlib`). No `node`, `npm`, `npx`, or `pip` required.
- **Safe & Reversible**:
  - Automatically creates a permanent original backup (`app.asar.orig`) and timestamped backups before modifications.
  - One-command factory restoration.
- **macOS & Electron Integrity**:
  - Updates the SHA-256 hash in `Info.plist` (`ElectronAsarIntegrity`).
  - Automatically re-signs the bundle with `codesign` to comply with Gatekeeper and AMFI.

---

## Quick Start

Open Terminal and run:

```bash
# 1. Check current patch status
python3 patch_antigravity_window.py --status

# 2. Apply the patch (prompts to close Antigravity if running)
python3 patch_antigravity_window.py

# Or apply and close Antigravity automatically
python3 patch_antigravity_window.py --kill
```

> **Tip:** You can also use the included shell runner:
> ```bash
> chmod +x run.sh
> ./run.sh --kill
> ```

---

## CLI Options

| Option | Description |
|---|---|
| *(none)* | Applies the persistence patch to the detected Antigravity installation. |
| `--status` | Checks whether the patch is installed and active. |
| `--restore`, `--undo` | Restores the original factory `app.asar` from the backup. |
| `--kill` | Automatically terminates Antigravity if it is currently running. |
| `--app <path>` | Specifies a custom path to `Antigravity.app`. |

---

## Restoring Factory Defaults

To revert Antigravity back to its stock factory state at any time:

```bash
python3 patch_antigravity_window.py --restore
```

---

## Handling Official Updates

When Google updates Antigravity to a new version, the updater will replace `app.asar`. Simply re-run this script after updating to restore window persistence on the new version.
