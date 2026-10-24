# Antigravity Window Size Persistence (macOS, Windows & Linux)

A zero-dependency Python utility to automatically persist and restore the window size, position, and maximized state of Google **Antigravity** across **macOS**, **Windows**, and **Linux**.

---

## Features

- **Cross-Platform Auto-Detection**:
  - **Linux**: Automatically locates system and user installs (`/opt/antigravity`, `/usr/lib/antigravity`, `~/.local/share/antigravity`, `PATH`, extracted folders in `~/Downloads`).
  - **Windows**: Automatically locates `%LOCALAPPDATA%\Programs\antigravity` and standard Program Files paths.
  - **macOS**: Automatically locates `/Applications/Antigravity.app`, `~/Applications`, and Spotlight (`mdfind`).
  - Supports custom installation directories via `--app <path>`.
- **Smart Window Geometry Persistence**:
  - Restores previous window dimensions and screen coordinates from `app_storage.json`.
  - Preserves and restores maximized window state across launches.
  - Multi-monitor safety: repositions the window safely into view if a secondary monitor was disconnected.
  - Debounced listeners on `resize`, `move`, and `close` events for smooth performance.
- **Zero External Dependencies**: Built entirely with Python 3 standard library modules (`struct`, `json`, `hashlib`, etc.). No `node`, `npm`, `npx`, or `pip` required.
- **Safe & Fully Reversible**:
  - Automatically creates a permanent original backup (`app.asar.orig`) and timestamped rollback backups.
  - Instant one-command factory restore.
- **Platform Integrity & Permissions**:
  - Updates Electron ASAR integrity hashes (`ElectronAsarIntegrity` in `Info.plist` on macOS).
  - Automatically re-signs the bundle with `codesign` on macOS for Gatekeeper/AMFI compliance.
  - Handles permission checks gracefully on Linux systems.

---

## Quick Start

### Linux

Open Terminal in the repository folder:

```bash
# 1. Check current patch status
python3 patch_antigravity_window.py --status

# 2. Apply the patch (prompts if Antigravity is open)
python3 patch_antigravity_window.py

# Or apply and close running Antigravity automatically:
python3 patch_antigravity_window.py --kill
```

> **Tip:** You can also use the included shell runner:
> ```bash
> chmod +x run.sh
> ./run.sh --kill
> ```
> *Note: If installed in a system directory like `/opt/antigravity`, run with `sudo`.*

### Windows

Open PowerShell or Command Prompt in the repository folder:

```powershell
# 1. Check current patch status
python patch_antigravity_window.py --status

# 2. Apply the patch (prompts if Antigravity is open)
python patch_antigravity_window.py

# Or apply and close running Antigravity automatically:
python patch_antigravity_window.py --kill
```

> **Tip:** You can also run `.\run.bat` or `.\run.ps1`:
> ```powershell
> .\run.ps1 --status
> ```

### macOS

Open Terminal in the repository folder:

```bash
# 1. Check current patch status
python3 patch_antigravity_window.py --status

# 2. Apply the patch (prompts if Antigravity is open)
python3 patch_antigravity_window.py

# Or apply and close running Antigravity automatically:
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
| `--restore`, `--undo` | Restores the original stock factory `app.asar` from the backup. |
| `--kill` | Automatically terminates Antigravity if it is currently running. |
| `--app <path>` | Specifies a custom path to Antigravity directory, binary, or `app.asar`. |

---

## Restoring Factory Defaults

To revert Antigravity back to its stock factory state at any time:

```bash
# Linux
python3 patch_antigravity_window.py --restore

# Windows
python patch_antigravity_window.py --restore

# macOS
python3 patch_antigravity_window.py --restore
```

---

## Handling Official Updates

When Google updates Antigravity to a new version, the updater will replace `app.asar`. Simply re-run this script after updating to restore window persistence on the new version.
