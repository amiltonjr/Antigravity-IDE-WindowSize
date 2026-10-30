#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Antigravity Window Size Persistence Patch
==========================================
Cross-platform utility (macOS, Windows & Linux) to automatically persist and restore
the window size, position, and maximized state of Google Antigravity.

Author: Amilton Camargo Junior (Comandante)
Website: https://comandanteamilton.com.br/

Features:
- Automatically detects Antigravity installation on macOS, Windows, and Linux.
- Injects non-intrusive window persistence into dist/utils.js in app.asar.
- Automatically handles multi-monitor screen repositioning safety.
- Manages Electron ASAR integrity and macOS codesigning where applicable.
- Intelligent backup and restore: prevents accidental downgrade when app updates.
- Automatically manages Linux desktop shortcuts (.desktop) and application menu integration.
- 100% standalone using Python standard library (no npm, pip, or node needed).
"""

__author__ = "Amilton Camargo Junior (Comandante)"
__url__ = "https://comandanteamilton.com.br/"
__version__ = "1.2.1"

import argparse
import ast
import hashlib
import json
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

GITHUB_REPO_URL = "https://github.com/amiltonjr/Antigravity-IDE-WindowSize"
GITHUB_RAW_SCRIPT_URL = "https://raw.githubusercontent.com/amiltonjr/Antigravity-IDE-WindowSize/master/patch_antigravity_window.py"

# Enable UTF-8 encoding and ANSI color sequences on Windows console
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    try:
        os.system("")
    except Exception:
        pass

PATCH_MARKER = "/* __ANTIGRAVITY_WINDOW_PERSISTENCE_PATCH_V1__ */"


def log(msg: str):
    print(f"\033[1;34m[*]\033[0m {msg}")


def log_success(msg: str):
    print(f"\033[1;32m[✓]\033[0m {msg}")


def log_warn(msg: str):
    print(f"\033[1;33m[!]\033[0m {msg}")


def log_error(msg: str):
    print(f"\033[1;31m[✗]\033[0m {msg}", file=sys.stderr)


class AppPaths:
    """Holds resolved paths for an Antigravity installation."""

    def __init__(
        self,
        app_root: str,
        asar_path: str,
        resources_dir: str,
        info_plist_path: str = None,
        is_unpacked: bool = False,
        app_dir: str = None,
    ):
        self.app_root = app_root
        self.asar_path = asar_path
        self.resources_dir = resources_dir
        self.info_plist_path = info_plist_path
        self.is_unpacked = is_unpacked
        self.app_dir = app_dir or os.path.join(resources_dir, "app")
        self.backup_orig = (
            os.path.join(resources_dir, "app.asar.orig")
            if asar_path
            else os.path.join(resources_dir, "app.orig")
        )
        self.patch_info_path = (
            os.path.join(resources_dir, "app.asar.patch_info.json")
            if asar_path
            else os.path.join(resources_dir, "app.patch_info.json")
        )


def resolve_app_structure(base_path: str) -> AppPaths:
    """Resolves whether a given directory or file is a valid Antigravity install."""
    if not base_path:
        return None

    p = os.path.abspath(os.path.expanduser(base_path))

    # Case 1: Directly points to app.asar
    if os.path.isfile(p) and os.path.basename(p) == "app.asar":
        resources_dir = os.path.dirname(p)
        parent = os.path.dirname(resources_dir)
        plist = os.path.join(parent, "Info.plist")
        return AppPaths(
            app_root=parent,
            asar_path=p,
            resources_dir=resources_dir,
            info_plist_path=plist if os.path.exists(plist) else None,
        )

    # Case 2: Points to an executable binary (e.g. Antigravity.exe, antigravity, antigravity-ide)
    if os.path.isfile(p):
        parent = os.path.dirname(p)
        if os.path.basename(parent) == "bin" and not os.path.exists(os.path.join(parent, "resources")):
            p = os.path.dirname(parent)
        else:
            p = parent

    # Case 3: macOS bundle layout (<app>/Contents/Resources/app.asar)
    macos_asar = os.path.join(p, "Contents", "Resources", "app.asar")
    if os.path.exists(macos_asar):
        plist = os.path.join(p, "Contents", "Info.plist")
        return AppPaths(
            app_root=p,
            asar_path=macos_asar,
            resources_dir=os.path.join(p, "Contents", "Resources"),
            info_plist_path=plist if os.path.exists(plist) else None,
        )

    # Case 4: Windows / Linux standard layout (<app>/resources/app.asar)
    std_asar = os.path.join(p, "resources", "app.asar")
    if os.path.exists(std_asar):
        return AppPaths(
            app_root=p,
            asar_path=std_asar,
            resources_dir=os.path.join(p, "resources"),
            info_plist_path=None,
        )

    # Case 5: Path is directly the resources folder containing app.asar
    direct_asar = os.path.join(p, "app.asar")
    if os.path.exists(direct_asar):
        parent = os.path.dirname(p)
        return AppPaths(
            app_root=parent,
            asar_path=direct_asar,
            resources_dir=p,
            info_plist_path=None,
        )

    # Case 6: Unpacked directory layout (<app>/resources/app)
    unpacked_app = os.path.join(p, "resources", "app")
    if os.path.isdir(unpacked_app) and (
        os.path.exists(os.path.join(unpacked_app, "package.json"))
        or os.path.exists(os.path.join(unpacked_app, "product.json"))
        or os.path.exists(os.path.join(unpacked_app, "out"))
    ):
        return AppPaths(
            app_root=p,
            asar_path=None,
            resources_dir=os.path.join(p, "resources"),
            info_plist_path=None,
            is_unpacked=True,
            app_dir=unpacked_app,
        )

    # Case 7: Path is directly the resources directory containing 'app' folder
    if os.path.basename(p) == "resources" and os.path.isdir(os.path.join(p, "app")):
        parent = os.path.dirname(p)
        return AppPaths(
            app_root=parent,
            asar_path=None,
            resources_dir=p,
            info_plist_path=None,
            is_unpacked=True,
            app_dir=os.path.join(p, "app"),
        )

    # Case 8: Path is directly the 'app' directory inside resources
    if os.path.basename(p) == "app" and os.path.basename(os.path.dirname(p)) == "resources":
        resources_dir = os.path.dirname(p)
        parent = os.path.dirname(resources_dir)
        return AppPaths(
            app_root=parent,
            asar_path=None,
            resources_dir=resources_dir,
            info_plist_path=None,
            is_unpacked=True,
            app_dir=p,
        )

    return None


def get_default_candidate_paths() -> list:
    """Returns candidate paths for Antigravity based on the host OS."""
    candidates = []

    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidates.append(os.path.join(local_app_data, "Programs", "antigravity"))
            candidates.append(os.path.join(local_app_data, "Programs", "Antigravity"))
        candidates.append(os.path.expanduser("~/AppData/Local/Programs/antigravity"))

        prog_files = os.environ.get("ProgramFiles")
        if prog_files:
            candidates.append(os.path.join(prog_files, "Antigravity"))
            candidates.append(os.path.join(prog_files, "antigravity"))

        prog_files_x86 = os.environ.get("ProgramFiles(x86)")
        if prog_files_x86:
            candidates.append(os.path.join(prog_files_x86, "Antigravity"))
            candidates.append(os.path.join(prog_files_x86, "antigravity"))

        # Also check common extracted folders in Downloads
        downloads_dir = os.path.expanduser("~/Downloads")
        candidates.extend([
            os.path.join(downloads_dir, "Antigravity-Linux-x64"),
            os.path.join(downloads_dir, "antigravity-linux-x64"),
            os.path.join(downloads_dir, "Antigravity"),
        ])

    elif sys.platform == "darwin":
        candidates.extend([
            "/Applications/Antigravity.app",
            os.path.expanduser("~/Applications/Antigravity.app"),
        ])
    else:
        # Linux / Unix
        candidates.extend([
            "/opt/Antigravity",
            "/opt/antigravity",
            "/opt/Antigravity IDE",
            "/opt/antigravity-ide",
            "/usr/lib/antigravity",
            "/usr/lib/Antigravity",
            "/usr/lib/antigravity-ide",
            "/usr/share/antigravity",
            "/usr/share/Antigravity",
            "/usr/share/antigravity-ide",
            os.path.expanduser("~/.local/share/antigravity"),
            os.path.expanduser("~/.local/share/Antigravity"),
            os.path.expanduser("~/.local/share/antigravity-ide"),
            os.path.expanduser("~/Applications/Antigravity"),
            os.path.expanduser("~/Applications/antigravity"),
            os.path.expanduser("~/Applications/Antigravity IDE"),
            os.path.expanduser("~/Applications/antigravity-ide"),
            os.path.expanduser("~/Downloads/Antigravity-Linux-x64"),
            os.path.expanduser("~/Downloads/antigravity-linux-x64"),
            os.path.expanduser("~/Downloads/Antigravity"),
            os.path.expanduser("~/Downloads/Antigravity IDE"),
            os.path.expanduser("~/Downloads/antigravity-ide"),
        ])

        # Resolve from PATH if available
        for bin_name in ["antigravity", "Antigravity", "antigravity-ide", "Antigravity IDE"]:
            which_path = shutil.which(bin_name)
            if which_path:
                real_bin = os.path.realpath(which_path)
                candidates.append(os.path.dirname(real_bin))
                candidates.append(os.path.dirname(os.path.dirname(real_bin)))

    return candidates


def find_antigravity_app(custom_path: str = None) -> AppPaths:
    """Finds and resolves the Antigravity installation on the system."""
    if custom_path:
        resolved = resolve_app_structure(custom_path)
        if resolved:
            return resolved
        log_error(f"Specified path does not contain a valid Antigravity installation: {custom_path}")
        sys.exit(1)

    # Search standard candidate paths
    for candidate in get_default_candidate_paths():
        resolved = resolve_app_structure(candidate)
        if resolved:
            return resolved

    # On macOS, attempt Spotlight lookup
    if sys.platform == "darwin":
        try:
            res = subprocess.run(
                ["mdfind", 'kMDItemCFBundleIdentifier == "com.google.antigravity"'],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in res.stdout.strip().splitlines():
                line = line.strip()
                if line.endswith(".app"):
                    resolved = resolve_app_structure(line)
                    if resolved:
                        return resolved
        except Exception:
            pass

    log_error("Could not automatically locate the Antigravity installation.")
    log_error("Please specify its location manually using: --app <path>")
    sys.exit(1)


def is_app_running(app_paths: AppPaths) -> bool:
    """Checks whether the targeted Antigravity installation is currently running."""
    if sys.platform == "win32":
        exe_path = os.path.join(app_paths.app_root, "Antigravity.exe")
        if not os.path.exists(exe_path):
            return False

        try:
            cmd = 'Get-Process Antigravity -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Path'
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=5,
            )
            running_paths = [line.strip().lower() for line in res.stdout.strip().splitlines() if line.strip()]
            target_norm = os.path.normpath(exe_path).lower()
            return any(os.path.normpath(p) == target_norm for p in running_paths)
        except Exception:
            try:
                res = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq Antigravity.exe", "/NH"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return "antigravity.exe" in res.stdout.lower()
            except Exception:
                return False

    elif sys.platform == "darwin":
        try:
            res = subprocess.run(
                ["pgrep", "-f", f"{app_paths.app_root}/Contents/MacOS/Antigravity"],
                capture_output=True,
                timeout=5,
            )
            return res.returncode == 0
        except Exception:
            return False
    else:
        # Linux
        try:
            for bin_name in ["antigravity-ide", "antigravity", "Antigravity"]:
                res = subprocess.run(["pgrep", "-f", f"{app_paths.app_root}/{bin_name}"], capture_output=True, timeout=5)
                if res.returncode == 0:
                    return True
                res_bin = subprocess.run(["pgrep", "-f", f"{app_paths.app_root}/bin/{bin_name}"], capture_output=True, timeout=5)
                if res_bin.returncode == 0:
                    return True
            for bin_name in ["antigravity-ide", "antigravity", "Antigravity"]:
                res_gen = subprocess.run(["pgrep", "-x", bin_name], capture_output=True, timeout=5)
                if res_gen.returncode == 0:
                    return True
            return False
        except Exception:
            return False


def kill_running_app(app_paths: AppPaths):
    """Terminates running instances of Antigravity."""
    log_warn("Closing running Antigravity processes...")
    if sys.platform == "win32":
        try:
            subprocess.run(["taskkill", "/F", "/IM", "Antigravity.exe", "/T"], check=False, capture_output=True)
        except Exception as e:
            log_error(f"Error terminating process: {e}")
    elif sys.platform == "darwin":
        try:
            subprocess.run(["pkill", "-f", f"{app_paths.app_root}/Contents/MacOS/Antigravity"], check=False)
        except Exception as e:
            log_error(f"Error terminating process: {e}")
    else:
        # Linux
        try:
            subprocess.run(["pkill", "-f", "antigravity-ide"], check=False)
            subprocess.run(["pkill", "-f", "antigravity"], check=False)
            subprocess.run(["pkill", "-f", "Antigravity"], check=False)
        except Exception as e:
            log_error(f"Error terminating process: {e}")

    # Ensure processes have completely exited and released file locks across all platforms
    for _ in range(10):
        if not is_app_running(app_paths):
            break
        time.sleep(0.5)
    time.sleep(1.0 if sys.platform == "win32" else 0.5)


def compute_electron_integrity(data: bytes) -> dict:
    """Calculates SHA-256 block-level integrity hash in Electron ASAR format."""
    block_size = 4 * 1024 * 1024  # 4 MB
    blocks = []
    for i in range(0, len(data), block_size):
        chunk = data[i : i + block_size]
        blocks.append(hashlib.sha256(chunk).hexdigest())
    return {
        "algorithm": "SHA256",
        "hash": hashlib.sha256(data).hexdigest(),
        "blockSize": block_size,
        "blocks": blocks,
    }


def parse_asar(asar_path: str):
    """Reads and parses the header and payload of an ASAR archive."""
    with open(asar_path, "rb") as f:
        hdr = f.read(16)
        if len(hdr) < 16:
            raise ValueError("ASAR file is truncated or invalid.")
        magic, size1, size2, json_size = struct.unpack("<4I", hdr)
        if magic != 4:
            raise ValueError(f"Unexpected ASAR magic header: {magic}")
        json_data = f.read(json_size).decode("utf-8")
        header = json.loads(json_data)
        pad_len = (4 - (json_size % 4)) % 4
        f.read(pad_len)
        payload = f.read()
    return header, payload


def extract_app_version_from_asar(header: dict, payload: bytes) -> str:
    """Extracts application version from package.json within ASAR payload."""
    try:
        pkg_entry = header["files"]["package.json"]
        offset = int(pkg_entry["offset"])
        size = pkg_entry["size"]
        pkg = json.loads(payload[offset : offset + size].decode("utf-8"))
        return pkg.get("version", "unknown")
    except Exception:
        return "unknown"


def extract_app_version_from_dir(app_dir: str) -> str:
    """Extracts application version from package.json or product.json in an unpacked app directory."""
    if not app_dir or not os.path.isdir(app_dir):
        return "unknown"
    for fname in ["product.json", "package.json"]:
        fpath = os.path.join(app_dir, fname)
        if os.path.isfile(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("ideVersion") and data["ideVersion"] != "Antigravity IDE":
                        return str(data["ideVersion"])
                    if "version" in data:
                        return str(data["version"])
            except Exception:
                pass
    return "unknown"


def get_app_product_info(app_paths: AppPaths) -> dict:
    """Retrieves metadata from product.json if present in app_dir or ASAR."""
    if not app_paths:
        return {}
    if app_paths.app_dir:
        prod_path = os.path.join(app_paths.app_dir, "product.json")
        if os.path.isfile(prod_path):
            try:
                with open(prod_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    if app_paths.asar_path and os.path.isfile(app_paths.asar_path):
        try:
            h, payload = parse_asar(app_paths.asar_path)
            if "product.json" in h.get("files", {}):
                entry = h["files"]["product.json"]
                offset = int(entry["offset"])
                size = int(entry["size"])
                return json.loads(payload[offset : offset + size].decode("utf-8"))
        except Exception:
            pass
    return {}


def build_asar(header: dict, payload: bytes) -> bytes:
    """Builds a complete ASAR binary from JSON header dict and raw payload."""
    json_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
    json_len = len(json_bytes)
    pad_len = (4 - (json_len % 4)) % 4
    pickle_len = 4 + json_len + pad_len
    payload_size = pickle_len + 4

    header_bytes = (
        struct.pack("<4I", 4, payload_size, pickle_len, json_len)
        + json_bytes
        + (b"\x00" * pad_len)
    )
    return header_bytes + payload


def load_patch_info(app_paths: AppPaths) -> dict:
    """Loads recorded patch metadata if present."""
    if os.path.exists(app_paths.patch_info_path):
        try:
            with open(app_paths.patch_info_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def save_patch_info(app_paths: AppPaths, info: dict):
    """Saves patch metadata to record hashes and version info."""
    try:
        with open(app_paths.patch_info_path, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2)
    except Exception as e:
        log_warn(f"Notice: Could not save patch metadata: {e}")


def remove_patch_info(app_paths: AppPaths):
    """Removes recorded patch metadata upon restoration."""
    if os.path.exists(app_paths.patch_info_path):
        try:
            os.remove(app_paths.patch_info_path)
        except Exception:
            pass


def generate_patched_utils_js(original_code: str) -> str:
    """Injects window persistence logic into dist/utils.js."""
    if PATCH_MARKER in original_code:
        return original_code

    patch_prelude = f"\n{PATCH_MARKER}\nlet _antigravityStorageManager = null;\n"

    target_create_window = "function createWindow(url, storageManager) {"
    replacement_create_window = f"""function createWindow(url, storageManager) {{
    {PATCH_MARKER}
    if (storageManager) {{
        _antigravityStorageManager = storageManager;
    }} else if (_antigravityStorageManager) {{
        storageManager = _antigravityStorageManager;
    }}

    let initialBounds = {{ width: 1400, height: 900 }};
    let startMaximized = false;
    try {{
        const storagePath = (0, paths_1.getAppStoragePath)();
        if (fs.existsSync(storagePath)) {{
            const stored = JSON.parse(fs.readFileSync(storagePath, "utf-8"));
            if (stored.windowBounds) {{
                const b = typeof stored.windowBounds === "string" ? JSON.parse(stored.windowBounds) : stored.windowBounds;
                if (b && typeof b.width === "number" && typeof b.height === "number") {{
                    const w = Math.max(500, Math.round(b.width));
                    const h = Math.max(400, Math.round(b.height));
                    const displays = electron_1.screen ? electron_1.screen.getAllDisplays() : [];
                    let visible = false;
                    if (typeof b.x === "number" && typeof b.y === "number" && displays.length > 0) {{
                        visible = displays.some(d => {{
                            const db = d.bounds;
                            return b.x >= db.x - 100 && b.x < db.x + db.width &&
                                   b.y >= db.y - 100 && b.y < db.y + db.height;
                        }});
                    }}
                    if (visible) {{
                        initialBounds = {{ x: Math.round(b.x), y: Math.round(b.y), width: w, height: h }};
                    }} else {{
                        initialBounds = {{ width: w, height: h }};
                    }}
                }}
            }}
            if (stored.windowMaximized === "true" || stored.windowMaximized === true) {{
                startMaximized = true;
            }}
        }}
    }} catch (e) {{
        console.error("[WindowPersistence] Error loading saved window bounds:", e);
    }}
"""

    target_browser_window = """    const win = new electron_1.BrowserWindow({
        width: 1400,
        height: 900,"""

    replacement_browser_window = """    const win = new electron_1.BrowserWindow({
        width: initialBounds.width,
        height: initialBounds.height,
        ...(initialBounds.x !== undefined ? { x: initialBounds.x, y: initialBounds.y } : {}),"""

    persistence_listeners = """    if (startMaximized) {
        win.maximize();
    }

    let saveBoundsTimer = null;
    const persistWindowBounds = () => {
        if (saveBoundsTimer) clearTimeout(saveBoundsTimer);
        saveBoundsTimer = setTimeout(async () => {
            if (win.isDestroyed()) return;
            try {
                const isMax = win.isMaximized();
                const isFull = win.isFullScreen();
                const isMin = win.isMinimized();
                const updates = { windowMaximized: String(isMax) };
                if (!isMax && !isFull && !isMin) {
                    updates.windowBounds = JSON.stringify(win.getBounds());
                }
                const mgr = storageManager || _antigravityStorageManager;
                if (mgr && typeof mgr.updateItems === "function") {
                    await mgr.updateItems(updates);
                } else {
                    const sPath = (0, paths_1.getAppStoragePath)();
                    let cur = {};
                    if (fs.existsSync(sPath)) {
                        try { cur = JSON.parse(fs.readFileSync(sPath, "utf-8")); } catch {}
                    }
                    Object.assign(cur, updates);
                    fs.writeFileSync(sPath, JSON.stringify(cur, null, 2), "utf-8");
                }
            } catch (err) {
                console.error("[WindowPersistence] Error persisting window bounds:", err);
            }
        }, 250);
    };

    win.on("resize", persistWindowBounds);
    win.on("move", persistWindowBounds);
    win.on("close", persistWindowBounds);"""

    # Target 1: createWindow signature
    if target_create_window not in original_code:
        match_cw = re.search(r"function\s+createWindow\s*\(\s*url\s*,\s*storageManager\s*\)\s*\{", original_code)
        if match_cw:
            target_create_window = match_cw.group(0)
        else:
            raise RuntimeError("Signature 'function createWindow(url, storageManager)' not found in dist/utils.js")

    # Target 2: BrowserWindow initialization (width: 1400, height: 900)
    if target_browser_window not in original_code:
        match_bw = re.search(
            r"const\s+win\s*=\s*new\s+electron_1\.BrowserWindow\s*\(\s*\{\s*width:\s*1400\s*,\s*height:\s*900\s*,",
            original_code,
        )
        if match_bw:
            target_browser_window = match_bw.group(0)
            replacement_browser_window = """const win = new electron_1.BrowserWindow({
        width: initialBounds.width,
        height: initialBounds.height,
        ...(initialBounds.x !== undefined ? { x: initialBounds.x, y: initialBounds.y } : {}),"""
        else:
            raise RuntimeError("Default initialization 'width: 1400, height: 900' not found in dist/utils.js")

    # Target 3: loadURL call (compatible with v2.26, v2.28+, and future versions)
    target_load_url = "void win.loadURL(url);"
    replacement_load_url = f"{persistence_listeners}\n\n    void win.loadURL(url);"

    if target_load_url in original_code:
        target_to_replace = target_load_url
        replacement_to_use = replacement_load_url
    else:
        match_lu = re.search(r"void\s+win\.loadURL\s*\(\s*url\s*\)\s*;", original_code)
        if match_lu:
            target_to_replace = match_lu.group(0)
            replacement_to_use = f"{persistence_listeners}\n\n    {target_to_replace}"
        else:
            raise RuntimeError("Snippet 'void win.loadURL(url);' not found in dist/utils.js")

    patched = patch_prelude + original_code.replace(
        target_create_window, replacement_create_window, 1
    ).replace(
        target_browser_window, replacement_browser_window, 1
    ).replace(
        target_to_replace, replacement_to_use, 1
    )

    return patched


def apply_patch(app_paths: AppPaths, force_kill: bool = False):
    """Applies the window size persistence patch to the targeted installation."""
    if app_paths.is_unpacked:
        utils_path = os.path.join(app_paths.app_dir, "dist", "utils.js")
        if not os.path.exists(utils_path):
            app_ver = extract_app_version_from_dir(app_paths.app_dir)
            log_success(f"Detected Antigravity IDE v{app_ver} ({app_paths.app_root}).")
            log_success(
                "Antigravity IDE natively persists window geometry (width, height, coordinates, and maximized state)."
            )
            log("No ASAR patch required for Antigravity IDE.")
            return

        if is_app_running(app_paths):
            if force_kill:
                kill_running_app(app_paths)
            else:
                log_warn("Antigravity is currently running.")
                if sys.stdin.isatty():
                    resp = input("Do you want to close Antigravity to apply the patch now? [y/N]: ").strip().lower()
                    if resp in ("y", "yes", "s", "sim"):
                        kill_running_app(app_paths)
                    else:
                        log_error("Operation aborted. Please close Antigravity before applying the patch.")
                        sys.exit(1)
                else:
                    log_error("Antigravity is running. Close it or use --kill to automatically terminate it.")
                    sys.exit(1)

        with open(utils_path, "r", encoding="utf-8") as f:
            code = f.read()

        if PATCH_MARKER in code:
            log_warn("Window persistence patch is already applied to this installation!")
            return

        log("Injecting geometry persistence logic into dist/utils.js...")
        patched_code = generate_patched_utils_js(code)
        backup_file = os.path.join(app_paths.app_dir, "dist", "utils.js.orig")
        if not os.path.exists(backup_file):
            shutil.copy2(utils_path, backup_file)
        with open(utils_path, "w", encoding="utf-8") as f:
            f.write(patched_code)
        log_success("PATCH APPLIED SUCCESSFULLY to unpacked installation!")
        return

    asar_path = app_paths.asar_path

    if not asar_path or not os.path.exists(asar_path):
        log_error(f"app.asar not found at: {asar_path}")
        sys.exit(1)

    if is_app_running(app_paths):
        if force_kill:
            kill_running_app(app_paths)
        else:
            log_warn("Antigravity is currently running.")
            if sys.stdin.isatty():
                resp = input("Do you want to close Antigravity to apply the patch now? [y/N]: ").strip().lower()
                if resp in ("y", "yes", "s", "sim"):
                    kill_running_app(app_paths)
                else:
                    log_error("Operation aborted. Please close Antigravity before applying the patch.")
                    sys.exit(1)
            else:
                log_error("Antigravity is running. Close it or use --kill to automatically terminate it.")
                sys.exit(1)

    log(f"Unpacking and reading ASAR: {asar_path}")
    header, payload = parse_asar(asar_path)
    app_version = extract_app_version_from_asar(header, payload)
    log(f"Detected Antigravity version: {app_version}")

    try:
        utils_entry = header["files"]["dist"]["files"]["utils.js"]
    except KeyError:
        log_error("dist/utils.js not found inside app.asar")
        sys.exit(1)

    old_offset = int(utils_entry["offset"])
    old_size = utils_entry["size"]
    original_utils_bytes = payload[old_offset : old_offset + old_size]
    original_utils_code = original_utils_bytes.decode("utf-8")

    if PATCH_MARKER in original_utils_code:
        log_warn("Window persistence patch is already applied to this installation!")
        return

    log("Injecting geometry persistence logic (size, position, maximized state)...")
    patched_utils_code = generate_patched_utils_js(original_utils_code)
    patched_utils_bytes = patched_utils_code.encode("utf-8")

    delta = len(patched_utils_bytes) - old_size
    utils_entry["size"] = len(patched_utils_bytes)
    utils_entry["integrity"] = compute_electron_integrity(patched_utils_bytes)

    def adjust_offsets(node):
        if isinstance(node, dict):
            if "files" in node:
                for child in node["files"].values():
                    adjust_offsets(child)
            elif "offset" in node:
                off = int(node["offset"])
                if off > old_offset:
                    node["offset"] = str(off + delta)

    adjust_offsets(header)

    new_payload = (
        payload[:old_offset]
        + patched_utils_bytes
        + payload[old_offset + old_size :]
    )

    log("Rebuilding new app.asar archive...")
    new_asar_bytes = build_asar(header, new_payload)
    new_asar_sha256 = hashlib.sha256(new_asar_bytes).hexdigest()

    # Safety backups and version tracking
    backup_orig = app_paths.backup_orig
    backup_timestamp = os.path.join(
        app_paths.resources_dir,
        f"app.asar.backup-{time.strftime('%Y%m%d-%H%M%S')}",
    )

    try:
        with open(asar_path, "rb") as f:
            current_clean_hash = hashlib.sha256(f.read()).hexdigest()

        # Check if backup_orig already exists from an older version
        if os.path.exists(backup_orig):
            with open(backup_orig, "rb") as f:
                old_backup_hash = hashlib.sha256(f.read()).hexdigest()
            if old_backup_hash != current_clean_hash:
                log_warn("Detected a newly updated stock Antigravity installation!")
                prev_backup = f"{backup_orig}.prev-{time.strftime('%Y%m%d-%H%M%S')}"
                log(f"Archiving previous backup to: {prev_backup}")
                shutil.copy2(backup_orig, prev_backup)
                log(f"Updating master factory backup to current stock version: {backup_orig}")
                shutil.copy2(asar_path, backup_orig)
        else:
            log(f"Creating permanent original backup at: {backup_orig}")
            shutil.copy2(asar_path, backup_orig)

        log(f"Creating timestamped backup at: {backup_timestamp}")
        shutil.copy2(asar_path, backup_timestamp)

        # Atomic file write (with retries for Windows file handle release)
        temp_asar = asar_path + ".tmp"
        with open(temp_asar, "wb") as f:
            f.write(new_asar_bytes)

        for attempt in range(5):
            try:
                os.replace(temp_asar, asar_path)
                break
            except PermissionError:
                if attempt < 4 and sys.platform == "win32":
                    time.sleep(0.5)
                else:
                    raise
        log_success("New app.asar successfully written.")

        # Save patch metadata to protect against accidental downgrade on restore
        save_patch_info(
            app_paths,
            {
                "patcher_version": __version__,
                "patch_marker": PATCH_MARKER,
                "app_version": app_version,
                "original_asar_sha256": current_clean_hash,
                "patched_asar_sha256": new_asar_sha256,
                "patched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        )
    except PermissionError as pe:
        log_error(f"Permission denied while modifying {asar_path}: {pe}")
        if sys.platform != "win32":
            log_error("Please try running the script with elevated permissions (e.g. sudo).")
        sys.exit(1)

    # macOS Info.plist ElectronAsarIntegrity update
    if app_paths.info_plist_path and os.path.exists(app_paths.info_plist_path):
        log("Updating ElectronAsarIntegrity hash in Info.plist...")
        try:
            import plistlib

            with open(app_paths.info_plist_path, "rb") as f:
                plist = plistlib.load(f)

            if "ElectronAsarIntegrity" in plist and "Resources/app.asar" in plist["ElectronAsarIntegrity"]:
                plist["ElectronAsarIntegrity"]["Resources/app.asar"]["hash"] = new_asar_sha256
                with open(app_paths.info_plist_path, "wb") as f:
                    plistlib.dump(plist, f)
                log_success("Info.plist successfully updated with new SHA-256 integrity hash.")
            else:
                log_warn("ElectronAsarIntegrity key not present or format mismatch.")
        except Exception as e:
            log_warn(f"Notice while updating Info.plist: {e}")

    # macOS Gatekeeper / AMFI codesigning
    if sys.platform == "darwin":
        log("Re-signing application bundle with ad-hoc codesign...")
        try:
            res = subprocess.run(
                ["codesign", "--force", "--deep", "-s", "-", app_paths.app_root],
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                log_success("Ad-hoc codesign completed successfully.")
            else:
                log_warn(f"Codesign notice: {res.stderr.strip()}")
        except Exception as e:
            log_warn(f"Codesign error: {e}")

        print("\n\033[1;33m[i] macOS Ad-Hoc Signing Notice:\033[0m")
        print("  • The app was re-signed ad-hoc so macOS Gatekeeper allows running modified ASAR.")
        print("  • If macOS Keychain prompts for password access on first launch, click 'Always Allow'.")
        print("  • Background auto-updater may be overwritten or require manual update on new releases.")

    print("\n" + "=" * 62)
    log_success("PATCH APPLIED SUCCESSFULLY!")
    print("  • Antigravity will now persist window size, position, and maximized state.")
    print("  • When reopened, the window will restore exact previous dimensions.")
    print(f"  • Original backup preserved at: {backup_orig}")
    print("=" * 62 + "\n")


def find_pending_update() -> tuple:
    """Finds any pending official update package downloaded by Antigravity in local cache.

    Returns (path_to_update, version_string) or (None, None).
    """
    candidates = []
    if sys.platform == "darwin":
        candidates.append(os.path.expanduser("~/Library/Caches/com.google.antigravity/pending/Antigravity.zip"))
    elif sys.platform == "win32":
        search_dirs = [
            os.path.expandvars(r"%LOCALAPPDATA%\com.google.antigravity\pending"),
            os.path.expandvars(r"%LOCALAPPDATA%\antigravity-updater\pending"),
        ]
        for sdir in search_dirs:
            if os.path.isdir(sdir):
                for f in os.listdir(sdir):
                    if f.lower().endswith((".zip", ".exe")):
                        candidates.append(os.path.join(sdir, f))
    else:
        search_dirs = [
            os.path.expanduser("~/.cache/com.google.antigravity/pending"),
            os.path.expanduser("~/.cache/antigravity-updater/pending"),
            os.path.expanduser("~/.cache/antigravity-ide-updater/pending"),
            os.path.expanduser("~/.cache/Antigravity IDE/pending"),
            os.path.expanduser("~/.config/Antigravity IDE/pending"),
            os.path.expanduser("~/.config/antigravity-ide/pending"),
        ]
        for sdir in search_dirs:
            if os.path.isdir(sdir):
                for f in os.listdir(sdir):
                    if f.lower().endswith((".zip", ".tar.gz", ".tgz", ".appimage")):
                        candidates.append(os.path.join(sdir, f))

    for c in candidates:
        if os.path.isfile(c) and os.path.getsize(c) > 5 * 1024 * 1024:
            version = "latest"
            if sys.platform == "darwin":
                try:
                    import plistlib
                    with zipfile.ZipFile(c, "r") as zf:
                        plist_data = zf.read("Antigravity.app/Contents/Info.plist")
                        plist = plistlib.loads(plist_data)
                        version = plist.get("CFBundleShortVersionString", "latest")
                except Exception:
                    pass
            elif sys.platform == "win32":
                if c.lower().endswith(".exe"):
                    try:
                        with open(c, "rb") as ef:
                            data = ef.read()
                        m = re.search(
                            b'(?:P\x00r\x00o\x00d\x00u\x00c\x00t\x00|F\x00i\x00l\x00e\x00)V\x00e\x00r\x00s\x00i\x00o\x00n\x00\x00\x00((?:[0-9\.]\x00)+)',
                            data,
                        )
                        if m:
                            raw_ver = m.group(1).decode("utf-16le").rstrip("\x00")
                            if raw_ver and re.match(r"^\d+(\.\d+)+", raw_ver):
                                version = raw_ver
                    except Exception:
                        pass
            info_json = os.path.join(os.path.dirname(c), "update-info.json")
            if version == "latest" and os.path.isfile(info_json):
                try:
                    with open(info_json, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if "version" in data:
                            version = data["version"]
                except Exception:
                    pass
            if version == "latest":
                fn_match = re.search(r"(\d+\.\d+\.\d+)", os.path.basename(c))
                if fn_match:
                    version = fn_match.group(1)
            return c, version
    return None, None


def check_online_update(app_paths: AppPaths) -> dict:
    """Checks official Google Antigravity auto-updater server for new versions.

    Returns a dict with update info if an update is available, or None.
    """
    if not app_paths:
        return None
    try:
        machine = platform.machine().lower()
        arch = "arm64" if machine in ("arm64", "aarch64") else "x64"

        if sys.platform == "darwin":
            platform_arch = f"darwin-{arch}"
        elif sys.platform == "win32":
            platform_arch = f"win32-{arch}-user"
        else:
            platform_arch = f"linux-{arch}"

        product = get_app_product_info(app_paths)
        commit = product.get("commit", "unknown")
        quality = product.get("quality", "stable")

        feed_url = f"https://antigravity-ide-auto-updater-974169037036.us-central1.run.app/api/update/{platform_arch}/{quality}/{commit}/no_hostname"

        req = urllib.request.Request(feed_url, headers={"User-Agent": "Antigravity-IDE-WindowSize"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 204:
                return None
            data = json.loads(resp.read().decode("utf-8"))
            if not data or not data.get("url"):
                return None

            download_url = data["url"]
            ver_match = re.search(r"/(\d+\.\d+\.\d+(?:-[^/]+)?)/", download_url)
            if ver_match:
                version = ver_match.group(1)
            else:
                version = data.get("name") or data.get("productVersion") or "latest"

            return {
                "version": version,
                "commit": data.get("version"),
                "url": download_url,
                "sha256": data.get("sha256hash"),
                "displayName": data.get("displayName", os.path.basename(download_url)),
                "raw": data,
            }
    except Exception:
        return None


def download_file_with_progress(url: str, dest_path: str, expected_sha256: str = None) -> bool:
    """Downloads a file from url to dest_path with download progress and SHA-256 verification."""
    log(f"Downloading official update from:\n    {url}")
    temp_dest = dest_path + ".downloading"
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    if os.path.exists(temp_dest):
        try:
            os.remove(temp_dest)
        except Exception:
            pass

    try:
        encoded_url = urllib.parse.quote(url, safe=":/%?&=+@#~")
        req = urllib.request.Request(encoded_url, headers={"User-Agent": "Antigravity-Updater"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            total_size = resp.headers.get("Content-Length")
            total_bytes = int(total_size) if total_size and total_size.isdigit() else 0
            downloaded = 0
            hasher = hashlib.sha256()

            chunk_size = 1024 * 1024  # 1 MB
            start_time = time.time()
            last_log_time = start_time

            with open(temp_dest, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    hasher.update(chunk)
                    downloaded += len(chunk)
                    now = time.time()
                    if now - last_log_time >= 1.5 or (total_bytes and downloaded == total_bytes):
                        last_log_time = now
                        pct = f"({(downloaded / total_bytes) * 100:.1f}%)" if total_bytes else ""
                        mb_dl = downloaded / (1024 * 1024)
                        mb_tot = f" / {total_bytes / (1024 * 1024):.1f} MB" if total_bytes else " MB"
                        speed = mb_dl / max(now - start_time, 0.001)
                        print(f"[*] Downloading: {mb_dl:.1f}{mb_tot} {pct} [{speed:.1f} MB/s]...", end="\r", flush=True)

            print()

        actual_sha256 = hasher.hexdigest()
        if expected_sha256 and actual_sha256.lower() != expected_sha256.lower():
            log_error("SHA-256 verification failed!")
            log_error(f"  Expected: {expected_sha256}")
            log_error(f"  Received: {actual_sha256}")
            if os.path.exists(temp_dest):
                try:
                    os.remove(temp_dest)
                except Exception:
                    pass
            return False

        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except Exception:
                pass
        os.replace(temp_dest, dest_path)
        log_success(f"Download complete & verified ({downloaded / (1024 * 1024):.1f} MB).")
        return True
    except Exception as e:
        log_error(f"Download failed: {e}")
        if os.path.exists(temp_dest):
            try:
                os.remove(temp_dest)
            except Exception:
                pass
        return False


def apply_pending_update(app_paths: AppPaths, force_kill: bool = False):
    """Applies a pending official update and automatically reapplies the window persistence patch."""
    update_file, update_version = find_pending_update()

    if not update_file:
        log("Checking official update server for available updates...")
        online_update = check_online_update(app_paths)
        if not online_update:
            log_success("Antigravity is already up to date! No updates available.")
            return

        update_version = online_update["version"]
        cache_dir = os.path.expanduser("~/.cache/antigravity-updater/pending")
        if sys.platform == "win32":
            local_app_data = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/AppData/Local")
            cache_dir = os.path.join(local_app_data, "antigravity-updater", "pending")
        elif sys.platform == "darwin":
            cache_dir = os.path.expanduser("~/Library/Caches/com.google.antigravity/pending")

        os.makedirs(cache_dir, exist_ok=True)
        raw_filename = os.path.basename(urllib.parse.urlparse(online_update["url"]).path)
        filename = urllib.parse.unquote(raw_filename) or "update.tar.gz"
        dest_file = os.path.join(cache_dir, filename)

        if not download_file_with_progress(online_update["url"], dest_file, online_update.get("sha256")):
            log_error("Could not complete downloading the official update.")
            return

        update_file = dest_file

    # Check if this pending version is ALREADY installed
    current_installed_ver = None
    if app_paths.asar_path and os.path.exists(app_paths.asar_path):
        try:
            h, p = parse_asar(app_paths.asar_path)
            current_installed_ver = extract_app_version_from_asar(h, p)
        except Exception:
            pass
    elif app_paths.is_unpacked:
        current_installed_ver = extract_app_version_from_dir(app_paths.app_dir)

    if current_installed_ver and update_version != "latest":
        if parse_version_tuple(current_installed_ver) >= parse_version_tuple(update_version):
            log_success(
                f"Antigravity is already updated to version v{current_installed_ver} "
                f"(cached update file was v{update_version})."
            )
            log("Applying window persistence patch to current installation...")
            new_app_paths = find_antigravity_app(app_paths.app_root)
            apply_patch(new_app_paths, force_kill=force_kill)
            log("Cleaning up stale updater cache...")
            try:
                if os.path.isfile(update_file):
                    os.remove(update_file)
                shutil.rmtree(os.path.dirname(update_file), ignore_errors=True)
            except Exception:
                pass
            log_success(f"All set! Antigravity v{current_installed_ver} is patched with window persistence active.")
            return

    log(f"Found update package: v{update_version} ({update_file})")

    if is_app_running(app_paths):
        if not force_kill:
            log_warn("Antigravity is currently running. It must be closed to apply the update.")
            if sys.stdin.isatty():
                try:
                    ans = input("Close Antigravity automatically and continue with update? [Y/n]: ").strip().lower()
                    if ans and ans not in ("y", "yes", "s", "sim"):
                        log_error("Update cancelled by user.")
                        return
                except (EOFError, KeyboardInterrupt):
                    log_error("\nUpdate cancelled.")
                    return
            else:
                log_error("Antigravity is running. Close it or use --kill to automatically terminate it before updating.")
                sys.exit(1)
        kill_running_app(app_paths)

    temp_dir = tempfile.mkdtemp(prefix="antigravity_update_")
    try:
        log(f"Extracting official update package v{update_version}...")
        if sys.platform == "darwin":
            # ditto preserves Mach-O execution permissions, symlinks, and Apple code signature
            res = subprocess.run(["ditto", "-xk", update_file, temp_dir], capture_output=True, text=True)
            if res.returncode != 0:
                log_error(f"Failed to extract update package: {res.stderr}")
                return
            new_app = os.path.join(temp_dir, "Antigravity.app")
            if not os.path.exists(new_app):
                candidates = [c for c in os.listdir(temp_dir) if c.endswith(".app")]
                if candidates:
                    new_app = os.path.join(temp_dir, candidates[0])
                else:
                    log_error(f"Extracted bundle not found in {temp_dir}")
                    return

            log(f"Installing new version to {app_paths.app_root}...")
            target_app = app_paths.app_root
            backup_temp = target_app + ".old"
            if os.path.exists(backup_temp):
                shutil.rmtree(backup_temp, ignore_errors=True)

            os.rename(target_app, backup_temp)
            try:
                shutil.move(new_app, target_app)
                shutil.rmtree(backup_temp, ignore_errors=True)
            except Exception as e:
                log_error(f"Failed to install new bundle: {e}")
                if os.path.exists(backup_temp):
                    os.rename(backup_temp, target_app)
                return

            # Clean up pending updater caches
            try:
                if os.path.isfile(update_file):
                    os.remove(update_file)
                shutil.rmtree(os.path.dirname(update_file), ignore_errors=True)
                shipit_cache = os.path.expanduser("~/Library/Caches/com.google.antigravity.ShipIt")
                if os.path.exists(shipit_cache):
                    shutil.rmtree(shipit_cache, ignore_errors=True)
            except Exception:
                pass

        elif sys.platform == "win32":
            if update_file.lower().endswith(".exe"):
                log("Running official Windows installer in update mode...")
                install_dir = os.path.normpath(app_paths.app_root)
                cmd = [update_file, "--updated", "/S", f"/D={install_dir}"]
                elevate_exe = os.path.join(app_paths.resources_dir, "elevate.exe")

                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode != 0:
                    log_warn(f"Silent update with /D returned code {res.returncode}. Retrying with [--updated, /S]...")
                    res = subprocess.run([update_file, "--updated", "/S"], capture_output=True, text=True)

                if res.returncode != 0 and os.path.exists(elevate_exe):
                    log_warn("Retrying with elevation helper (elevate.exe)...")
                    res = subprocess.run([elevate_exe, update_file, "--updated", "/S"], capture_output=True, text=True)

                if res.returncode != 0:
                    log_warn(f"Silent install returned code {res.returncode} (NSIS aborted).")
                    log("Launching installer in standard mode to complete update...")
                    subprocess.run([update_file, "--updated"])

                log("Waiting for installer to finish updating files...")
                time.sleep(3)
                exe_name = os.path.basename(update_file)
                for _ in range(30):
                    try:
                        chk = subprocess.run(
                            ["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/NH"],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        if exe_name.lower() not in chk.stdout.lower():
                            break
                    except Exception:
                        break
                    time.sleep(1)
                time.sleep(2)
            else:
                with zipfile.ZipFile(update_file, "r") as zf:
                    zf.extractall(temp_dir)
                extracted_items = [i for i in os.listdir(temp_dir) if not i.startswith(".")]
                if len(extracted_items) == 1 and os.path.isdir(os.path.join(temp_dir, extracted_items[0])):
                    source_dir = os.path.join(temp_dir, extracted_items[0])
                else:
                    source_dir = temp_dir
                for item in os.listdir(source_dir):
                    s = os.path.join(source_dir, item)
                    d = os.path.join(app_paths.app_root, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        if os.path.exists(d):
                            try:
                                os.remove(d)
                            except Exception:
                                pass
                        shutil.copy2(s, d)
            try:
                if os.path.isfile(update_file):
                    os.remove(update_file)
                shutil.rmtree(os.path.dirname(update_file), ignore_errors=True)
            except Exception:
                pass

        else:
            # Linux
            if update_file.lower().endswith(".appimage"):
                log(f"Replacing AppImage at {app_paths.app_root}...")
                shutil.copy2(update_file, app_paths.app_root)
                os.chmod(app_paths.app_root, 0o755)
            elif update_file.lower().endswith((".tar.gz", ".tgz", ".tar")):
                import tarfile
                with tarfile.open(update_file, "r:*") as tf:
                    tf.extractall(temp_dir)
                extracted_items = [i for i in os.listdir(temp_dir) if not i.startswith(".")]
                if len(extracted_items) == 1 and os.path.isdir(os.path.join(temp_dir, extracted_items[0])):
                    source_dir = os.path.join(temp_dir, extracted_items[0])
                else:
                    source_dir = temp_dir
                for item in os.listdir(source_dir):
                    s = os.path.join(source_dir, item)
                    d = os.path.join(app_paths.app_root, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        if os.path.exists(d):
                            try:
                                os.remove(d)
                            except Exception:
                                pass
                        shutil.copy2(s, d)
            else:
                with zipfile.ZipFile(update_file, "r") as zf:
                    zf.extractall(temp_dir)
                extracted_items = [i for i in os.listdir(temp_dir) if not i.startswith(".")]
                if len(extracted_items) == 1 and os.path.isdir(os.path.join(temp_dir, extracted_items[0])):
                    source_dir = os.path.join(temp_dir, extracted_items[0])
                else:
                    source_dir = temp_dir
                for item in os.listdir(source_dir):
                    s = os.path.join(source_dir, item)
                    d = os.path.join(app_paths.app_root, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        if os.path.exists(d):
                            try:
                                os.remove(d)
                            except Exception:
                                pass
                        shutil.copy2(s, d)

            # Ensure executable permissions for Linux binaries
            for bin_name in ("antigravity-ide", "antigravity", "Antigravity", "chrome_crashpad_handler", "chrome-sandbox"):
                bp = os.path.join(app_paths.app_root, bin_name)
                if os.path.isfile(bp):
                    try:
                        os.chmod(bp, 0o755)
                    except Exception:
                        pass
            bin_dir = os.path.join(app_paths.app_root, "bin")
            if os.path.isdir(bin_dir):
                for b in os.listdir(bin_dir):
                    bp = os.path.join(bin_dir, b)
                    if os.path.isfile(bp):
                        try:
                            os.chmod(bp, 0o755)
                        except Exception:
                            pass

            try:
                if os.path.isfile(update_file):
                    os.remove(update_file)
                shutil.rmtree(os.path.dirname(update_file), ignore_errors=True)
            except Exception:
                pass

        log_success(f"Official update v{update_version} installed successfully!")

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    # Re-apply persistence patch to the fresh install
    log("Applying window persistence patch to new installation...")
    new_app_paths = find_antigravity_app(app_paths.app_root)
    apply_patch(new_app_paths, force_kill=True)
    if sys.platform.startswith("linux"):
        ensure_linux_desktop_entry(new_app_paths)
    log_success(f"All set! Antigravity is now updated to v{update_version} with window persistence active.")


def ensure_linux_desktop_entry(app_paths: AppPaths, force: bool = False) -> bool:
    """Ensures a Linux desktop shortcut (.desktop) and application menu entry exist.

    If not already present or if force is True, creates ~/.local/share/applications/antigravity-ide.desktop
    with the official icon installed to the user's icon directory.
    """
    if not sys.platform.startswith("linux") or not app_paths:
        return False

    desktop_dir = os.path.expanduser("~/.local/share/applications")
    desktop_file = os.path.join(desktop_dir, "antigravity-ide.desktop")

    # Locate executable binary
    binary_path = None
    for cand in (
        os.path.join(app_paths.app_root, "antigravity-ide"),
        os.path.join(app_paths.app_root, "antigravity"),
        os.path.join(app_paths.app_root, "Antigravity"),
        os.path.join(app_paths.app_root, "bin", "antigravity-ide"),
        os.path.join(app_paths.app_root, "bin", "antigravity"),
    ):
        if os.path.isfile(cand):
            binary_path = cand
            break

    if not binary_path:
        if os.path.isfile(app_paths.app_root):
            binary_path = app_paths.app_root
        else:
            which_bin = shutil.which("antigravity-ide") or shutil.which("antigravity")
            if which_bin:
                binary_path = which_bin

    if not binary_path:
        return False

    # Check if a desktop entry already exists pointing to this installation
    if not force:
        candidates = [
            desktop_file,
            os.path.join(desktop_dir, "antigravity.desktop"),
            "/usr/share/applications/antigravity-ide.desktop",
            "/usr/share/applications/antigravity.desktop",
        ]
        for c in candidates:
            if os.path.isfile(c) and os.path.getsize(c) > 0:
                try:
                    with open(c, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        if app_paths.app_root in content or binary_path in content or "Antigravity" in content:
                            return True
                except Exception:
                    pass

    # Setup Icon: check repository for icon.png or antigravity.png
    script_dir = os.path.dirname(os.path.abspath(__file__))
    source_icon = None
    for icon_name in ("icon.png", "antigravity.png"):
        candidate_icon = os.path.join(script_dir, icon_name)
        if os.path.isfile(candidate_icon) and os.path.getsize(candidate_icon) > 100:
            source_icon = candidate_icon
            break

    if not source_icon:
        for cached in (
            os.path.expanduser("~/.local/share/icons/antigravity.png"),
            os.path.expanduser("~/.local/share/pixmaps/antigravity.png"),
        ):
            if os.path.isfile(cached):
                source_icon = cached
                break

    user_icons_dir = os.path.expanduser("~/.local/share/icons")
    hicolor_apps_dir = os.path.join(user_icons_dir, "hicolor", "512x512", "apps")
    pixmaps_dir = os.path.expanduser("~/.local/share/pixmaps")

    os.makedirs(user_icons_dir, exist_ok=True)
    os.makedirs(hicolor_apps_dir, exist_ok=True)
    os.makedirs(pixmaps_dir, exist_ok=True)

    dest_icon_path = os.path.join(user_icons_dir, "antigravity.png")

    if source_icon and os.path.isfile(source_icon):
        try:
            shutil.copy2(source_icon, dest_icon_path)
            shutil.copy2(source_icon, os.path.join(hicolor_apps_dir, "antigravity-ide.png"))
            shutil.copy2(source_icon, os.path.join(pixmaps_dir, "antigravity-ide.png"))
            shutil.copy2(source_icon, os.path.join(pixmaps_dir, "antigravity.png"))
        except Exception:
            pass
    elif not os.path.isfile(dest_icon_path):
        try:
            icon_url = "https://antigravity.google/assets/image/brand/antigravity-icon__full-color.png"
            req = urllib.request.Request(icon_url, headers={"User-Agent": "Antigravity-IDE-WindowSize"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = resp.read()
                if data:
                    with open(dest_icon_path, "wb") as f:
                        f.write(data)
                    with open(os.path.join(hicolor_apps_dir, "antigravity-ide.png"), "wb") as f:
                        f.write(data)
        except Exception:
            pass

    try:
        os.chmod(binary_path, 0o755)
    except Exception:
        pass

    desktop_content = f"""[Desktop Entry]
Name=Antigravity IDE
Comment=Google Antigravity IDE
GenericName=Integrated Development Environment
Exec="{binary_path}" %F
Icon={dest_icon_path}
Type=Application
StartupNotify=true
StartupWMClass=antigravity-ide
Categories=Development;IDE;TextEditor;
MimeType=text/plain;inode/directory;x-scheme-handler/antigravity-ide;
Keywords=antigravity;code;editor;ide;ai;
Path={app_paths.app_root}
Actions=new-empty-window;

[Desktop Action new-empty-window]
Name=New Empty Window
Name[pt_BR]=Nova Janela Vazia
Exec="{binary_path}" --new-window %F
Icon={dest_icon_path}
"""
    try:
        os.makedirs(desktop_dir, exist_ok=True)
        with open(desktop_file, "w", encoding="utf-8") as f:
            f.write(desktop_content)
        os.chmod(desktop_file, 0o755)

        if shutil.which("update-desktop-database"):
            try:
                subprocess.run(
                    ["update-desktop-database", desktop_dir],
                    capture_output=True,
                    check=False,
                    timeout=5,
                )
            except Exception:
                pass

        if shutil.which("gtk-update-icon-cache"):
            try:
                subprocess.run(
                    ["gtk-update-icon-cache", "-q", "-t", "-f", os.path.join(user_icons_dir, "hicolor")],
                    capture_output=True,
                    check=False,
                    timeout=5,
                )
            except Exception:
                pass

        log_success(f"Created Linux desktop shortcut: {desktop_file}")
        return True
    except Exception as e:
        log_warn(f"Could not create Linux desktop shortcut: {e}")
        return False


def parse_version_tuple(v: str) -> tuple:
    """Parses a version string into an integer tuple for comparison."""
    try:
        nums = [int(x) for x in re.findall(r"\d+", v)]
        return tuple(nums) if nums else (0,)
    except Exception:
        return (0,)


def check_for_self_update(silent: bool = True) -> tuple:
    """Checks GitHub repository for a newer version of patch_antigravity_window.py.

    Returns (remote_version, remote_code) if an update is available, or (None, None).
    """
    try:
        with urllib.request.urlopen(GITHUB_RAW_SCRIPT_URL, timeout=2.5) as resp:
            content = resp.read().decode("utf-8")
            match = re.search(r'__version__\s*=\s*[\'"]([^\'"]+)[\'"]', content)
            if not match:
                if not silent:
                    log_warn("Could not determine remote version from GitHub.")
                return None, None

            remote_ver = match.group(1)
            if parse_version_tuple(remote_ver) > parse_version_tuple(__version__):
                border = "=" * 62
                print(f"\n\033[1;36m{border}\033[0m")
                print(f"\033[1;36m[🚀] Update Available for Antigravity-IDE-WindowSize!\033[0m")
                print(f"  • Installed version: \033[1;33mv{__version__}\033[0m")
                print(f"  • Latest version:    \033[1;32mv{remote_ver}\033[0m")
                print(f"  • Run with \033[1;37m--selfupdate\033[0m (or \033[1;37m./run.sh --selfupdate\033[0m) to update in-place.")
                print(f"\033[1;36m{border}\033[0m\n")
                return remote_ver, content
            else:
                if not silent:
                    log_success(f"Antigravity-IDE-WindowSize is up to date (v{__version__}).")
                return None, None
    except Exception as e:
        if not silent:
            log_warn(f"Notice: Failed to check for script updates online: {e}")
        return None, None


def perform_self_update():
    """Updates the tool to the latest version available on GitHub."""
    log("Checking for updates to Antigravity-IDE-WindowSize...")
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    git_dir = os.path.join(script_dir, ".git")

    # Method 1: Git repository pull if cloned via git
    if os.path.isdir(git_dir):
        log("Detected Git clone. Updating via 'git pull'...")
        try:
            res = subprocess.run(
                ["git", "-C", script_dir, "pull", "--ff-only"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if res.returncode == 0:
                out = res.stdout.strip()
                if "Already up to date" in out:
                    log_success(f"Repository is already up to date (v{__version__}).")
                else:
                    log_success(f"Git pull succeeded:\n{out}")
                return
            else:
                log_warn(f"git pull returned notice: {res.stderr.strip()}. Falling back to direct script update...")
        except Exception as e:
            log_warn(f"Git pull error: {e}. Falling back to direct script update...")

    # Method 2: Direct download & syntax validation fallback
    remote_ver, remote_code = check_for_self_update(silent=False)
    if not remote_code:
        return

    try:
        # Validate syntax of downloaded code
        ast.parse(remote_code)
    except SyntaxError as e:
        log_error(f"Downloaded update failed syntax check: {e}. Aborting self-update.")
        return

    # Write atomically
    new_script = script_path + ".new"
    try:
        with open(new_script, "w", encoding="utf-8") as f:
            f.write(remote_code)
        shutil.copymode(script_path, new_script)
        os.replace(new_script, script_path)
        log_success(f"Antigravity-IDE-WindowSize successfully updated to v{remote_ver}!")
    except Exception as e:
        log_error(f"Failed to save updated script: {e}")
        if os.path.exists(new_script):
            os.remove(new_script)


def check_status(app_paths: AppPaths):
    """Displays current status of the patch on the detected installation."""
    log(f"Detected application: {app_paths.app_root}")

    if app_paths.is_unpacked:
        log(f"Target Directory: {app_paths.app_dir}")
        app_version = extract_app_version_from_dir(app_paths.app_dir)
        log(f"Antigravity Version: {app_version}")

        utils_path = os.path.join(app_paths.app_dir, "dist", "utils.js")
        if os.path.exists(utils_path):
            with open(utils_path, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()
            if PATCH_MARKER in code:
                log_success("Status: PATCH IS ACTIVE and functioning (unpacked).")
            else:
                log_warn("Status: PATCH NOT APPLIED (window uses default 1400x900 size).")
        else:
            log_success("Status: Antigravity IDE natively persists window geometry via its built-in state manager.")
            cfg_dir = os.path.expanduser("~/.config/Antigravity IDE")
            if os.path.exists(cfg_dir):
                log(f"Storage path: {cfg_dir}")

        if sys.platform.startswith("linux"):
            df = os.path.expanduser("~/.local/share/applications/antigravity-ide.desktop")
            if os.path.isfile(df):
                log_success(f"Desktop shortcut: Active ({df})")
            else:
                log_warn("Desktop shortcut: Not found (will be created automatically on next run).")

        update_file, update_ver = find_pending_update()
        if update_file:
            is_already_installed = False
            if update_ver != "latest" and app_version != "unknown":
                if parse_version_tuple(app_version) >= parse_version_tuple(update_ver):
                    is_already_installed = True
            if not is_already_installed:
                log_warn(f"Pending official update detected in cache: v{update_ver} ({os.path.basename(update_file)})")
                log("Run with --update (or ./run.sh --update) to install the update and automatically re-patch.")
        else:
            try:
                online = check_online_update(app_paths)
                if online:
                    log_warn(f"Official update available online: v{online['version']} ({online['displayName']})")
                    log("Run with --update (or ./run.sh --update) to download, install, and automatically re-patch.")
            except Exception:
                pass
        return

    asar_path = app_paths.asar_path
    log(f"Target ASAR: {asar_path}")

    if not asar_path or not os.path.exists(asar_path):
        log_error("app.asar not found.")
        return

    header, payload = parse_asar(asar_path)
    app_version = extract_app_version_from_asar(header, payload)
    log(f"Antigravity Version: {app_version}")

    patch_info = load_patch_info(app_paths)
    is_patched = False
    try:
        utils_entry = header["files"]["dist"]["files"]["utils.js"]
        old_offset = int(utils_entry["offset"])
        old_size = utils_entry["size"]
        code = payload[old_offset : old_offset + old_size].decode("utf-8", "ignore")
        if PATCH_MARKER in code:
            is_patched = True
    except Exception as e:
        log_error(f"Error inspecting ASAR: {e}")

    if is_patched:
        log_success("Status: PATCH IS ACTIVE and functioning.")
        if patch_info and patch_info.get("patched_at"):
            log(f"Patched at: {patch_info['patched_at']}")
    else:
        log_warn("Status: PATCH NOT APPLIED (window uses default 1400x900 size).")
        if patch_info and patch_info.get("app_version") and patch_info["app_version"] != app_version:
            log_warn(
                f"Notice: App was previously patched on version {patch_info['app_version']}, "
                f"but has since been officially updated to {app_version}."
            )
            log("Run without arguments to apply persistence to this new version.")

    backup_orig = app_paths.backup_orig
    if os.path.exists(backup_orig):
        log(f"Original factory backup present: {backup_orig}")

    if sys.platform.startswith("linux"):
        df = os.path.expanduser("~/.local/share/applications/antigravity-ide.desktop")
        if os.path.isfile(df):
            log_success(f"Desktop shortcut: Active ({df})")
        else:
            log_warn("Desktop shortcut: Not found (will be created automatically on next run).")

    update_file, update_ver = find_pending_update()
    if update_file:
        is_already_installed = False
        if update_ver != "latest" and app_version != "unknown":
            if parse_version_tuple(app_version) >= parse_version_tuple(update_ver):
                is_already_installed = True
        if not is_already_installed:
            log_warn(f"Pending official update detected in cache: v{update_ver} ({os.path.basename(update_file)})")
            log("Run with --update (or ./run.sh --update) to install the update and automatically re-patch.")
    else:
        try:
            online = check_online_update(app_paths)
            if online:
                log_warn(f"Official update available online: v{online['version']} ({online['displayName']})")
                log("Run with --update (or ./run.sh --update) to download, install, and automatically re-patch.")
        except Exception:
            pass


def restore_backup(app_paths: AppPaths, force_kill: bool = False, force: bool = False):
    """Restores the original stock factory backup of app.asar safely."""
    if app_paths.is_unpacked:
        utils_path = os.path.join(app_paths.app_dir, "dist", "utils.js")
        backup_utils = os.path.join(app_paths.app_dir, "dist", "utils.js.orig")
        if os.path.exists(backup_utils):
            log(f"Restoring {backup_utils} -> {utils_path}...")
            shutil.copy2(backup_utils, utils_path)
            log_success("Restored stock utils.js from backup.")
            return
        elif os.path.exists(utils_path):
            log_warn("No backup utils.js.orig found for unpacked installation.")
            return
        else:
            log_success("Antigravity IDE operates with stock configurations natively. No ASAR restoration required.")
            return

    asar_path = app_paths.asar_path
    backup_orig = app_paths.backup_orig

    if not os.path.exists(backup_orig):
        log_error(f"No original backup found at: {backup_orig}")
        sys.exit(1)

    if not os.path.exists(asar_path):
        log_error(f"app.asar not found at: {asar_path}")
        sys.exit(1)

    # Read current ASAR and backup hashes
    with open(asar_path, "rb") as f:
        current_bytes = f.read()
    current_sha256 = hashlib.sha256(current_bytes).hexdigest()

    with open(backup_orig, "rb") as f:
        orig_bytes = f.read()
    orig_sha256 = hashlib.sha256(orig_bytes).hexdigest()

    # Check 1: Already original stock?
    if current_sha256 == orig_sha256:
        log_warn("The application is already running the stock original ASAR. No restoration needed.")
        remove_patch_info(app_paths)
        return

    # Check 2: Check if current ASAR has patch marker
    current_is_patched = False
    try:
        curr_header, curr_payload = parse_asar(asar_path)
        utils_entry = curr_header["files"]["dist"]["files"]["utils.js"]
        curr_utils_code = curr_payload[
            int(utils_entry["offset"]) : int(utils_entry["offset"]) + utils_entry["size"]
        ].decode("utf-8", "ignore")
        if PATCH_MARKER in curr_utils_code:
            current_is_patched = True
    except Exception:
        pass

    # Check 3: Has Antigravity updated since the patch was applied?
    patch_info = load_patch_info(app_paths)
    if patch_info:
        expected_patched_hash = patch_info.get("patched_asar_sha256")
        if expected_patched_hash and current_sha256 != expected_patched_hash and not current_is_patched:
            log_warn("=" * 64)
            log_warn("DETECTED OFFICIAL UPDATE: app.asar has been replaced by an Antigravity update!")
            log_warn(
                f"Patch was recorded for version {patch_info.get('app_version', 'unknown')}, "
                "but current app.asar is a new unpatched version."
            )
            log_error(
                "Restoring app.asar.orig would DOWNGRADE your installation and overwrite the new update!"
            )
            log_warn("=" * 64)
            if not force:
                log_error("Aborting restore for safety. Use --force to override if you genuinely wish to downgrade.")
                sys.exit(1)
            else:
                log_warn("Proceeding with restore due to --force flag.")
    elif not current_is_patched:
        log_warn("=" * 64)
        log_warn("Current app.asar is not patched. It may have been installed by a new official update.")
        log_error("Restoring app.asar.orig could downgrade your app from a newer version!")
        log_warn("=" * 64)
        if not force:
            log_error("Aborting restore for safety. Use --force to override if you genuinely wish to downgrade.")
            sys.exit(1)
        else:
            log_warn("Proceeding with restore due to --force flag.")

    if is_app_running(app_paths):
        if force_kill:
            kill_running_app(app_paths)
        else:
            log_warn("Antigravity is currently running.")
            if sys.stdin.isatty():
                resp = input("Do you want to close Antigravity to restore the backup? [y/N]: ").strip().lower()
                if resp in ("y", "yes", "s", "sim"):
                    kill_running_app(app_paths)
                else:
                    log_error("Operation aborted.")
                    sys.exit(1)
            else:
                log_error("Antigravity is running. Close it or use --kill to restore.")
                sys.exit(1)

    log(f"Restoring {backup_orig} -> {asar_path}...")
    try:
        for attempt in range(5):
            try:
                shutil.copy2(backup_orig, asar_path)
                break
            except PermissionError:
                if attempt < 4 and sys.platform == "win32":
                    time.sleep(0.5)
                else:
                    raise
        remove_patch_info(app_paths)
    except PermissionError as pe:
        log_error(f"Permission denied while restoring {asar_path}: {pe}")
        if sys.platform != "win32":
            log_error("Please try running the script with elevated permissions (e.g. sudo).")
        sys.exit(1)

    # Restore Info.plist on macOS
    if app_paths.info_plist_path and os.path.exists(app_paths.info_plist_path):
        try:
            import plistlib

            with open(backup_orig, "rb") as f:
                orig_sha256 = hashlib.sha256(f.read()).hexdigest()
            with open(app_paths.info_plist_path, "rb") as f:
                plist = plistlib.load(f)
            if "ElectronAsarIntegrity" in plist and "Resources/app.asar" in plist["ElectronAsarIntegrity"]:
                plist["ElectronAsarIntegrity"]["Resources/app.asar"]["hash"] = orig_sha256
                with open(app_paths.info_plist_path, "wb") as f:
                    plistlib.dump(plist, f)
                log_success("Info.plist restored.")
        except Exception as e:
            log_warn(f"Notice while restoring Info.plist: {e}")

    # Re-sign on macOS
    if sys.platform == "darwin":
        log("Re-signing with codesign...")
        subprocess.run(["codesign", "--force", "--deep", "-s", "-", app_paths.app_root], check=False)

    log_success("Restore complete! Application reverted to factory state.")


def main():
    parser = argparse.ArgumentParser(
        description="Patch to persist window size and position in Antigravity (macOS, Windows & Linux).",
        epilog="Author: Amilton Camargo Junior (Comandante) • https://comandanteamilton.com.br/",
    )
    parser.add_argument(
        "--app",
        type=str,
        default=None,
        help="Custom path to Antigravity directory, binary, or app.asar (optional).",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Check whether the persistence patch is currently active.",
    )
    parser.add_argument(
        "--restore",
        "--undo",
        action="store_true",
        help="Restore the original factory app.asar from backup.",
    )
    parser.add_argument(
        "--force",
        "--force-restore",
        action="store_true",
        help="Force restore even if an official application update was detected.",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Apply a pending official update downloaded by Antigravity and automatically re-patch.",
    )
    parser.add_argument(
        "--selfupdate",
        "--self-update",
        action="store_true",
        help="Update Antigravity-IDE-WindowSize itself to the latest version from GitHub.",
    )
    parser.add_argument(
        "--kill",
        action="store_true",
        help="Automatically terminate Antigravity if it is currently running.",
    )
    parser.add_argument(
        "--shortcut",
        "--create-shortcut",
        action="store_true",
        help="Create or refresh Linux desktop shortcut (.desktop) and application menu entry.",
    )

    args = parser.parse_args()

    if args.selfupdate:
        perform_self_update()
        return

    # Check for script updates online (silent notification if newer version found)
    try:
        check_for_self_update(silent=True)
    except Exception:
        pass

    app_paths = find_antigravity_app(args.app)

    # On Linux, ensure the desktop shortcut and application menu entry exist
    if sys.platform.startswith("linux"):
        ensure_linux_desktop_entry(app_paths, force=args.shortcut)

    if args.shortcut:
        return

    if args.status:
        check_status(app_paths)
    elif args.restore:
        restore_backup(app_paths, force_kill=args.kill, force=args.force)
    elif args.update:
        apply_pending_update(app_paths, force_kill=args.kill)
    else:
        apply_patch(app_paths, force_kill=args.kill)


if __name__ == "__main__":
    main()
