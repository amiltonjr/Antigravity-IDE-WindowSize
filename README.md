<div align="center">

# 🪟 Antigravity Window Size Persistence

**Cross-platform utility to persist and restore Google Antigravity window geometry across launches.**

<a href="https://github.com" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20%7C%20Linux-24292e?style=for-the-badge&logo=apple&logoColor=white" alt="Platform: macOS | Windows | Linux" /></a>
<a href="https://python.org" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.8+" /></a>
<a href="https://python.org" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/badge/Dependencies-Standard%20Library%20Only-2ea44f?style=for-the-badge" alt="Zero Dependencies" /></a>
<a href="https://comandanteamilton.com.br/" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/badge/Author-Amilton%20Camargo%20Junior-blueviolet?style=for-the-badge" alt="Author" /></a>

<p align="center">
  <a href="#-overview">Overview</a> •
  <a href="#-how-it-works">How It Works</a> •
  <a href="#-features">Features</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-cli-reference">CLI Reference</a> •
  <a href="#-restoring-factory-state">Restoration</a> •
  <a href="#-macos-security--keychain-notice">macOS Notice</a> •
  <a href="#-author">Author</a>
</p>

</div>

---

## 📖 Overview

By default, **Google Antigravity** resets its window to `1400×900` on launch. This utility modifies `dist/utils.js` inside `app.asar` to automatically persist:
- 📐 **Dimensions** (width and height).
- 📍 **Position** ($x$, $y$) with off-screen multi-monitor safety.
- 🔲 **Maximized state**.

Runs standalone via Python 3 with **zero external dependencies**.

---

## ⚙️ How It Works

```mermaid
flowchart LR
    A["🔍 Detect App"] --> B["💾 Backup app.asar"] --> C["⚡ Inject Persistence"] --> D["🔨 Rebuild & Sign"] --> E["🚀 Auto-Restore"]
```

1. **Auto-detects** Antigravity on macOS, Windows, or Linux.
2. **Backs up** original `app.asar` (`app.asar.orig`) and saves version metadata.
3. **Injects** debounced window geometry handlers into `dist/utils.js`.
4. **Restores** your exact window layout on every launch.

---

## ✨ Features

- 🖥️ **Multi-Monitor Safe**: If a display is disconnected, the window shifts safely to an active screen.
- ⏱️ **Debounced Saving**: Geometry writes to native `app_storage.json` without lag (250ms debounce).
- 🛡️ **Intelligent Downgrade Guard**: Tracks version and ASAR hashes. If Google updates Antigravity, `--restore` will safely abort to prevent downgrading your app with an obsolete backup.
- 🔄 **Safe Backup Rotation**: When reapplying the patch to a newly updated version, the master backup is automatically updated to match the new stock release.
- 🔏 **Platform Compliant**: Handles macOS `codesign`/`ElectronAsarIntegrity`, Windows paths, and Linux permissions.

---

## 🚀 Quick Start

Run from your terminal (use `python` on Windows, `python3` on macOS/Linux):

```bash
# Check current status
python3 patch_antigravity_window.py --status

# Apply the patch (prompts if Antigravity is running)
python3 patch_antigravity_window.py

# Or apply and close Antigravity automatically:
python3 patch_antigravity_window.py --kill
```

> [!TIP]
> **Convenience runners:**
> - **Windows**: `.\run.bat --kill` *(or `.\run.ps1 --kill` in PowerShell)*
> - **Linux / macOS**: `./run.sh --kill` *(use `sudo ./run.sh` only if installed in a system directory like `/opt`)*

---

## 🛠️ CLI Reference

| Option | Argument | Description |
|---|---|---|
| *(none)* | — | Applies the persistence patch to the detected installation. |
| `--status` | — | Checks if the patch is active on `app.asar`. |
| `--restore`, `--undo` | — | Restores the stock factory `app.asar` from backup. |
| `--force`, `--force-restore` | — | Overrides the downgrade protection and forces restoration even if an update was detected. |
| `--kill` | — | Terminates Antigravity if currently running before patching. |
| `--app` | `<path>` | Custom path to Antigravity folder, executable, or `app.asar`. |

---

## 🔄 Restoring Factory State

To revert Antigravity back to stock factory condition at any time:

```bash
python3 patch_antigravity_window.py --restore
```
*(On Windows, run `python patch_antigravity_window.py --restore` or `.\run.bat --restore`)*

> [!NOTE]
> **Intelligent Downgrade Guard:**
> If Antigravity was updated by Google after the patch was applied, the script detects the change and prevents `--restore` from overwriting your new version with an obsolete backup. If you genuinely want to force a restore, pass `--force`.

---

## 🍎 macOS Security & Keychain Notice

When modifying `app.asar` on macOS, the original Google Developer ID signature is replaced with an ad-hoc signature (`codesign -s -`) so macOS Gatekeeper and AMFI allow the modified application to execute.

Please be aware of the following macOS behaviors:
1. **Keychain Access Prompts:** macOS binds Keychain credentials (stored tokens, passwords) to the binary's code signing identity. On the first launch after patching, macOS may prompt you once:
   > *"Antigravity wants to access key '...' in your keychain. Enter your login password to allow."*
   Select **"Always Allow"** to proceed normally.
2. **In-App Auto-Updates:** Electron's background updater (`Squirrel.Mac` / `ShipIt`) validates that downloaded updates match the running binary's signing certificate. If an automatic background update fails signature verification, simply download the new release or update manually when prompted.
3. **Official Updates:** When Antigravity updates to a new version, Google replaces `app.asar` with the new stock version (and restores the official Google signature). Simply run this script again to re-enable window persistence.

<p align="left">
  <a href="https://antigravity.google/download" target="_blank" rel="noopener noreferrer">
    <img src="https://img.shields.io/badge/Download-Official%20Google%20Antigravity%20IDE-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="Download Official Google Antigravity IDE" />
  </a>
</p>

---

## 👤 Author

**Amilton Camargo Junior (Comandante)**
- 🌐 Website: <a href="https://comandanteamilton.com.br/" target="_blank" rel="noopener noreferrer">comandanteamilton.com.br</a>
