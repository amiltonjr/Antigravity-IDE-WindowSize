<div align="center">

# 🪟 Antigravity Window Size Persistence

**Cross-platform utility to persist and restore Google Antigravity window geometry across launches.**

[![Platform: macOS | Windows | Linux](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20%7C%20Linux-24292e?style=for-the-badge&logo=apple&logoColor=white)](https://github.com)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Standard%20Library%20Only-2ea44f?style=for-the-badge)](https://python.org)
[![Safe Backups](https://img.shields.io/badge/Backups-Automatic%20%26%20Reversible-blue?style=for-the-badge)](https://github.com)

<p align="center">
  <a href="#-overview">Overview</a> •
  <a href="#-how-it-works">How It Works</a> •
  <a href="#-features">Features</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-cli-reference">CLI Reference</a> •
  <a href="#-restoring-factory-state">Restoration</a>
</p>

</div>

---

## 📖 Overview

By default, **Google Antigravity** resets its main window to a fixed `1400×900` resolution on every launch, ignoring custom layouts, window sizing, and multi-monitor configurations.

This utility modifies the internal `dist/utils.js` within Antigravity's `app.asar` archive to automatically persist and restore:
- 📐 **Exact window dimensions** (width and height).
- 📍 **Screen coordinates** ($x$, $y$) with intelligent multi-monitor protection.
- 🔲 **Maximized window state**.

Everything runs directly through the Python 3 standard library with **zero external dependencies** (`npm`, `pip`, or `node` are not required).

---

## ⚙️ How It Works

```mermaid
flowchart TD
    subgraph Step1["1. Discovery & Safety"]
        A["🔍 Auto-Detect Installation<br/>(macOS / Windows / Linux)"] --> B["💾 Create Original Stock Backup<br/>(app.asar.orig)"]
    end

    subgraph Step2["2. Non-Intrusive Patch"]
        B --> C["📦 Unpack ASAR Archive & Header"]
        C --> D["⚡ Inject Debounced Geometry Handlers<br/>into dist/utils.js"]
    end

    subgraph Step3["3. Rebuild & Sign"]
        D --> E["🔨 Rebuild ASAR with Adjusted Offsets"]
        E --> F["🔐 Update Hashes & Ad-Hoc Sign<br/>(Gatekeeper & AMFI on macOS)"]
    end

    subgraph Step4["4. Launch"]
        F --> G["🚀 Antigravity Restores Previous Window Size,<br/>Coordinates & Maximized State"]
    end

    style Step1 fill:#f6f8fa,stroke:#d0d7de,stroke-width:1px
    style Step2 fill:#f6f8fa,stroke:#d0d7de,stroke-width:1px
    style Step3 fill:#f6f8fa,stroke:#d0d7de,stroke-width:1px
    style Step4 fill:#f6f8fa,stroke:#d0d7de,stroke-width:1px
```

---

## ✨ Features

- 🖥️ **Smart Multi-Monitor Safety**: If a secondary monitor is unplugged or unavailable, the window automatically snaps back into the visible bounds of the primary active display—no off-screen windows.
- ⏱️ **Debounced State Storage**: State updates write smoothly to Antigravity's native `app_storage.json` with a 250ms debounce on `resize`, `move`, and `close` events, eliminating CPU and disk overhead.
- 🛡️ **Non-Destructive with Instant Rollback**: Creates a permanent master backup (`app.asar.orig`) plus timestamped snapshots before any modification. You can return to stock factory condition with a single command.
- 🔏 **Platform Security Compliance**:
  - **macOS**: Automatically updates the `ElectronAsarIntegrity` block in `Info.plist` and applies ad-hoc codesigning (`codesign --force --deep -s -`) to satisfy Gatekeeper and AMFI.
  - **Windows**: Handles console encoding (UTF-8), non-blocking process inspection, and atomic file replacements.
  - **Linux**: Resolves standard system paths (`/opt`, `/usr/lib`, `~/.local`) and provides clear guidance for permission handling (`sudo`).

---

## 🚀 Quick Start

Choose your operating system below:

### 🐧 Linux

Open Terminal in the repository folder:

```bash
# 1. Check current patch status
python3 patch_antigravity_window.py --status

# 2. Apply the patch (prompts if Antigravity is open)
python3 patch_antigravity_window.py

# Or apply and close running Antigravity automatically:
python3 patch_antigravity_window.py --kill
```

> [!TIP]
> You can also use the included shell runner:
> ```bash
> chmod +x run.sh
> ./run.sh --kill
> ```
> *Note: If Antigravity is installed in a system directory like `/opt/antigravity`, run with `sudo`.*

---

### 🪟 Windows

Open PowerShell or Command Prompt in the repository folder:

```powershell
# 1. Check current patch status
python patch_antigravity_window.py --status

# 2. Apply the patch (prompts if Antigravity is open)
python patch_antigravity_window.py

# Or apply and close running Antigravity automatically:
python patch_antigravity_window.py --kill
```

> [!TIP]
> You can also use the included batch or PowerShell runners:
> ```powershell
> .\run.bat --kill
> # or
> .\run.ps1 --kill
> ```

---

### 🍏 macOS

Open Terminal in the repository folder:

```bash
# 1. Check current patch status
python3 patch_antigravity_window.py --status

# 2. Apply the patch (prompts if Antigravity is open)
python3 patch_antigravity_window.py

# Or apply and close running Antigravity automatically:
python3 patch_antigravity_window.py --kill
```

> [!TIP]
> You can also use the included shell runner:
> ```bash
> chmod +x run.sh
> ./run.sh --kill
> ```

---

## 🛠️ CLI Reference

| Flag / Option | Argument | Description |
|---|---|---|
| *(none)* | — | Applies the window persistence patch to the detected installation. |
| `--status` | — | Inspects `app.asar` and displays whether the patch is active. |
| `--restore`, `--undo` | — | Restores the original stock factory `app.asar` from `app.asar.orig`. |
| `--kill` | — | Automatically closes running instances of Antigravity before patching. |
| `--app` | `<path>` | Custom path to Antigravity directory, binary executable, or `app.asar`. |

---

## 🔄 Restoring Factory State

To revert Antigravity back to stock factory condition at any time:

```bash
# Linux
python3 patch_antigravity_window.py --restore

# Windows
python patch_antigravity_window.py --restore

# macOS
python3 patch_antigravity_window.py --restore
```

---

## 💡 Official Updates

When Google releases a new version of Antigravity (e.g., via automatic background update), the installer will overwrite `app.asar`. Simply run this script again after the update to re-enable window persistence.
