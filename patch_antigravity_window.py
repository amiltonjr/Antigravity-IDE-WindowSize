#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Antigravity Window Size Persistence Patch
==========================================
Este script localiza o Antigravity.app no macOS, aplica persistência de tamanho
e posição da janela (lembrando as últimas dimensões deixadas pelo usuário),
atualiza a integridade do ASAR no Info.plist e refaz a assinatura com codesign.

Funciona de forma 100% autônoma no macOS utilizando apenas a biblioteca padrão do Python 3.
Zero dependências externas (sem necessidade de npm, pip ou npx).
"""

import argparse
import hashlib
import json
import os
import plistlib
import shutil
import struct
import subprocess
import sys
import time
from pathlib import Path

PATCH_MARKER = "/* __ANTIGRAVITY_WINDOW_PERSISTENCE_PATCH_V1__ */"

CANDIDATE_PATHS = [
    "/Applications/Antigravity.app",
    os.path.expanduser("~/Applications/Antigravity.app"),
]


def log(msg: str):
    print(f"\033[1;34m[*]\033[0m {msg}")


def log_success(msg: str):
    print(f"\033[1;32m[✓]\033[0m {msg}")


def log_warn(msg: str):
    print(f"\033[1;33m[!]\033[0m {msg}")


def log_error(msg: str):
    print(f"\033[1;31m[✗]\033[0m {msg}", file=sys.stderr)


def find_antigravity_app(custom_path: str = None) -> str:
    """Localiza o diretório do Antigravity.app no sistema."""
    if custom_path:
        p = os.path.abspath(os.path.expanduser(custom_path))
        if os.path.isdir(p) and os.path.exists(os.path.join(p, "Contents", "Resources", "app.asar")):
            return p
        log_error(f"Caminho especificado não contém um Antigravity.app válido: {custom_path}")
        sys.exit(1)

    for p in CANDIDATE_PATHS:
        if os.path.isdir(p) and os.path.exists(os.path.join(p, "Contents", "Resources", "app.asar")):
            return p

    # Tenta localizar via Spotlight/mdfind
    try:
        res = subprocess.run(
            ["mdfind", 'kMDItemCFBundleIdentifier == "com.google.antigravity"'],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in res.stdout.strip().splitlines():
            line = line.strip()
            if line.endswith(".app") and os.path.exists(os.path.join(line, "Contents", "Resources", "app.asar")):
                return line
    except Exception:
        pass

    log_error("Não foi possível localizar o Antigravity.app no sistema.")
    sys.exit(1)


def is_app_running(app_path: str) -> bool:
    """Verifica se o Antigravity está em execução."""
    try:
        res = subprocess.run(["pgrep", "-f", f"{app_path}/Contents/MacOS/Antigravity"], capture_output=True)
        return res.returncode == 0
    except Exception:
        return False


def kill_running_app(app_path: str):
    """Fecha o aplicativo caso esteja aberto."""
    log_warn("Encerrando instâncias em execução do Antigravity...")
    try:
        subprocess.run(["pkill", "-f", f"{app_path}/Contents/MacOS/Antigravity"], check=False)
        time.sleep(1.5)
    except Exception as e:
        log_error(f"Erro ao encerrar processo: {e}")


def compute_electron_integrity(data: bytes) -> dict:
    """Calcula a integridade de bloco SHA-256 no formato esperado pelo Electron ASAR."""
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
    """Lê o header e o payload de um arquivo ASAR."""
    with open(asar_path, "rb") as f:
        hdr = f.read(16)
        if len(hdr) < 16:
            raise ValueError("Arquivo ASAR inválido ou truncado.")
        magic, size1, size2, json_size = struct.unpack("<4I", hdr)
        if magic != 4:
            raise ValueError(f"Magic header ASAR inesperado: {magic}")
        json_data = f.read(json_size).decode("utf-8")
        header = json.loads(json_data)
        pad_len = (4 - (json_size % 4)) % 4
        f.read(pad_len)
        payload = f.read()
    return header, payload


def build_asar(header: dict, payload: bytes) -> bytes:
    """Constrói o binário ASAR completo a partir do header JSON e do payload."""
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


def generate_patched_utils_js(original_code: str) -> str:
    """Gera o código modificado de dist/utils.js com a persistência de janela."""
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
        console.error("[WindowPersistence] Erro ao carregar dimensões salvas:", e);
    }}
"""

    target_browser_window = """    const win = new electron_1.BrowserWindow({
        width: 1400,
        height: 900,"""

    replacement_browser_window = """    const win = new electron_1.BrowserWindow({
        width: initialBounds.width,
        height: initialBounds.height,
        ...(initialBounds.x !== undefined ? { x: initialBounds.x, y: initialBounds.y } : {}),"""

    target_return_win = """    void win.loadURL(url);
    return win;"""

    replacement_return_win = """    if (startMaximized) {
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
                console.error("[WindowPersistence] Erro ao persistir dimensões:", err);
            }
        }, 250);
    };

    win.on("resize", persistWindowBounds);
    win.on("move", persistWindowBounds);
    win.on("close", persistWindowBounds);

    void win.loadURL(url);
    return win;"""

    if target_create_window not in original_code:
        raise RuntimeError("Assinatura 'function createWindow(url, storageManager)' não encontrada em dist/utils.js")
    if target_browser_window not in original_code:
        raise RuntimeError("Inicialização padrão 'width: 1400, height: 900' não encontrada em dist/utils.js")
    if target_return_win not in original_code:
        raise RuntimeError("Trecho final 'void win.loadURL(url); return win;' não encontrado em dist/utils.js")

    patched = patch_prelude + original_code.replace(
        target_create_window, replacement_create_window, 1
    ).replace(
        target_browser_window, replacement_browser_window, 1
    ).replace(
        target_return_win, replacement_return_win, 1
    )

    return patched


def apply_patch(app_path: str, force_kill: bool = False):
    """Aplica o patch de persistência de tamanho de janela no app especificado."""
    asar_path = os.path.join(app_path, "Contents", "Resources", "app.asar")
    info_plist_path = os.path.join(app_path, "Contents", "Info.plist")

    if not os.path.exists(asar_path):
        log_error(f"app.asar não encontrado em: {asar_path}")
        sys.exit(1)

    if is_app_running(app_path):
        if force_kill:
            kill_running_app(app_path)
        else:
            log_warn("O Antigravity está em execução no momento.")
            resp = input("Deseja fechar o aplicativo para aplicar o patch agora? [S/n]: ").strip().lower()
            if resp in ("", "s", "sim", "y", "yes"):
                kill_running_app(app_path)
            else:
                log_error("Operação cancelada. Feche o Antigravity antes de aplicar o patch.")
                sys.exit(1)

    log(f"Lendo e desempacotando ASAR: {asar_path}")
    header, payload = parse_asar(asar_path)

    try:
        utils_entry = header["files"]["dist"]["files"]["utils.js"]
    except KeyError:
        log_error("dist/utils.js não encontrado dentro do app.asar")
        sys.exit(1)

    old_offset = int(utils_entry["offset"])
    old_size = utils_entry["size"]
    original_utils_bytes = payload[old_offset : old_offset + old_size]
    original_utils_code = original_utils_bytes.decode("utf-8")

    if PATCH_MARKER in original_utils_code:
        log_warn("O patch de persistência já está aplicado neste aplicativo!")
        return

    log("Injetando código de persistência de geometria (tamanho/posição/maximizado)...")
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

    log("Reempacotando novo app.asar...")
    new_asar_bytes = build_asar(header, new_payload)
    new_asar_sha256 = hashlib.sha256(new_asar_bytes).hexdigest()

    # Criação do backup de segurança
    backup_orig = os.path.join(app_path, "Contents", "Resources", "app.asar.orig")
    backup_timestamp = os.path.join(
        app_path,
        "Contents",
        "Resources",
        f"app.asar.backup-{time.strftime('%Y%m%d-%H%M%S')}",
    )

    if not os.path.exists(backup_orig):
        log(f"Criando backup mestre original em: {backup_orig}")
        shutil.copy2(asar_path, backup_orig)

    log(f"Criando backup pontual em: {backup_timestamp}")
    shutil.copy2(asar_path, backup_timestamp)

    # Gravação do novo ASAR
    temp_asar = asar_path + ".tmp"
    with open(temp_asar, "wb") as f:
        f.write(new_asar_bytes)
    os.replace(temp_asar, asar_path)
    log_success("Novo app.asar gravado com sucesso.")

    # Atualização da integridade no Info.plist
    if os.path.exists(info_plist_path):
        log("Atualizando assinatura de integridade ElectronAsarIntegrity no Info.plist...")
        try:
            with open(info_plist_path, "rb") as f:
                plist = plistlib.load(f)

            if "ElectronAsarIntegrity" in plist and "Resources/app.asar" in plist["ElectronAsarIntegrity"]:
                plist["ElectronAsarIntegrity"]["Resources/app.asar"]["hash"] = new_asar_sha256
                with open(info_plist_path, "wb") as f:
                    plistlib.dump(plist, f)
                log_success("Info.plist atualizado com o novo hash SHA-256.")
            else:
                log_warn("Chave ElectronAsarIntegrity não presente ou com formato diferente.")
        except Exception as e:
            log_warn(f"Não foi possível atualizar Info.plist: {e}")

    # Re-assinatura de código para conformidade com o macOS Gatekeeper / AMFI
    log("Re-assinando o bundle com codesign ad-hoc...")
    try:
        res = subprocess.run(
            ["codesign", "--force", "--deep", "-s", "-", app_path],
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            log_success("Assinatura de código ad-hoc aplicada com sucesso.")
        else:
            log_warn(f"Aviso ao assinar com codesign: {res.stderr.strip()}")
    except Exception as e:
        log_warn(f"Erro ao executar codesign: {e}")

    print("\n" + "=" * 60)
    log_success("PATCH APLICADO COM SUCESSO!")
    print("  • O Antigravity agora salvará automaticamente o tamanho e posição da janela.")
    print("  • Ao reabrir, a janela retornará exatamente às últimas dimensões utilizadas.")
    print("  • Backup original preservado em: Contents/Resources/app.asar.orig")
    print("=" * 60 + "\n")


def check_status(app_path: str):
    """Exibe o status atual do app e do patch."""
    asar_path = os.path.join(app_path, "Contents", "Resources", "app.asar")
    log(f"Aplicativo detectado: {app_path}")
    if not os.path.exists(asar_path):
        log_error("app.asar não encontrado.")
        return

    header, payload = parse_asar(asar_path)
    try:
        utils_entry = header["files"]["dist"]["files"]["utils.js"]
        old_offset = int(utils_entry["offset"])
        old_size = utils_entry["size"]
        code = payload[old_offset : old_offset + old_size].decode("utf-8", "ignore")
        if PATCH_MARKER in code:
            log_success("Status: PATCH ATIVO e funcionando.")
        else:
            log_warn("Status: PATCH NÃO APLICADO (janela mantém tamanho padrão 1400x900).")
    except Exception as e:
        log_error(f"Erro ao analisar ASAR: {e}")

    backup_orig = os.path.join(app_path, "Contents", "Resources", "app.asar.orig")
    if os.path.exists(backup_orig):
        log(f"Backup original existente: {backup_orig}")


def restore_backup(app_path: str, force_kill: bool = False):
    """Restaura o backup original do app.asar."""
    asar_path = os.path.join(app_path, "Contents", "Resources", "app.asar")
    backup_orig = os.path.join(app_path, "Contents", "Resources", "app.asar.orig")
    info_plist_path = os.path.join(app_path, "Contents", "Info.plist")

    if not os.path.exists(backup_orig):
        log_error(f"Nenhum backup original encontrado em: {backup_orig}")
        sys.exit(1)

    if is_app_running(app_path):
        if force_kill:
            kill_running_app(app_path)
        else:
            log_warn("O Antigravity está em execução no momento.")
            resp = input("Deseja fechar o aplicativo para restaurar o backup? [S/n]: ").strip().lower()
            if resp in ("", "s", "sim", "y", "yes"):
                kill_running_app(app_path)
            else:
                log_error("Operação cancelada.")
                sys.exit(1)

    log(f"Restaurando {backup_orig} -> {asar_path}...")
    shutil.copy2(backup_orig, asar_path)

    # Restaura hash do backup no Info.plist
    with open(backup_orig, "rb") as f:
        orig_sha256 = hashlib.sha256(f.read()).hexdigest()

    if os.path.exists(info_plist_path):
        try:
            with open(info_plist_path, "rb") as f:
                plist = plistlib.load(f)
            if "ElectronAsarIntegrity" in plist and "Resources/app.asar" in plist["ElectronAsarIntegrity"]:
                plist["ElectronAsarIntegrity"]["Resources/app.asar"]["hash"] = orig_sha256
                with open(info_plist_path, "wb") as f:
                    plistlib.dump(plist, f)
                log_success("Info.plist restaurado.")
        except Exception as e:
            log_warn(f"Aviso ao restaurar Info.plist: {e}")

    log("Re-assinando com codesign...")
    subprocess.run(["codesign", "--force", "--deep", "-s", "-", app_path], check=False)

    log_success("Restauração concluída com sucesso! O aplicativo voltou ao estado de fábrica.")


def main():
    parser = argparse.ArgumentParser(
        description="Patch para persistir o tamanho da janela do Antigravity no macOS."
    )
    parser.add_argument(
        "--app",
        type=str,
        default=None,
        help="Caminho personalizado para o Antigravity.app (opcional).",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Verifica se o patch está ativo no app.",
    )
    parser.add_argument(
        "--restore",
        "--undo",
        action="store_true",
        help="Restaura o app.asar original de fábrica a partir do backup.",
    )
    parser.add_argument(
        "--kill",
        action="store_true",
        help="Fecha o aplicativo automaticamente sem perguntar se estiver em execução.",
    )

    args = parser.parse_args()

    app_path = find_antigravity_app(args.app)

    if args.status:
        check_status(app_path)
    elif args.restore:
        restore_backup(app_path, force_kill=args.kill)
    else:
        apply_patch(app_path, force_kill=args.kill)


if __name__ == "__main__":
    main()
