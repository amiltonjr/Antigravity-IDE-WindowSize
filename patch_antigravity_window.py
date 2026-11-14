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
__version__ = "1.3.8"

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
PAUSE_PATCH_MARKER = "/* __ANTIGRAVITY_PAUSE_BUTTON_PATCH_V1__ */"

PAUSE_RENDERER_JS = r"""(() => {
    if (window.__agyPausePlayControllerInstalled) return;
    window.__agyPausePlayControllerInstalled = true;

    const STYLE_ID = "agy-pause-play-styles";
    if (!document.getElementById(STYLE_ID)) {
        const style = document.createElement("style");
        style.id = STYLE_ID;
        style.textContent = `
            .agy-pause-play-slot {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
                margin-left: 4px;
                position: relative;
                flex-shrink: 0;
            }
            .agy-pause-play-slot[data-hidden="true"] {
                display: none !important;
            }
            .agy-pause-btn-wrap {
                position: relative;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
            }
            .agy-pause-btn-wrap[data-hidden="true"] {
                display: none !important;
            }
            .agy-pause-play-btn,
            .agy-pause-cancel-btn {
                width: 28px;
                height: 28px;
                border-radius: 9999px;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: opacity 150ms ease, transform 150ms ease, background-color 150ms ease, box-shadow 150ms ease;
                border: none;
                outline: none;
                padding: 0;
                position: relative;
                flex-shrink: 0;
            }
            .agy-pause-cancel-btn {
                background-color: var(--color-secondary, rgba(128, 128, 128, 0.2));
            }
            .agy-pause-cancel-btn-square {
                width: 10px;
                height: 10px;
                border-radius: 1.5px;
                background-color: #ef4444;
                pointer-events: none;
            }
            .agy-pause-play-btn[data-mode="pause"] {
                background-color: var(--color-secondary, rgba(128, 128, 128, 0.2));
                color: #f59e0b;
            }
            .agy-pause-play-btn[data-mode="play"] {
                background-color: #10b981;
                color: #ffffff;
                box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.25);
            }
            .agy-pause-play-btn:hover:not(:disabled),
            .agy-pause-cancel-btn:hover:not(:disabled) {
                opacity: 0.92;
                transform: scale(1.05);
            }
            .agy-pause-play-btn:active:not(:disabled),
            .agy-pause-cancel-btn:active:not(:disabled) {
                transform: scale(0.95);
            }
            .agy-pause-play-btn:disabled,
            .agy-pause-cancel-btn:disabled {
                opacity: 0.5;
                cursor: wait;
            }
            .agy-pause-play-badge {
                position: absolute;
                top: -4px;
                right: -4px;
                min-width: 14px;
                height: 14px;
                padding: 0 3px;
                border-radius: 9999px;
                background-color: #3b82f6;
                color: #ffffff;
                font-size: 9px;
                font-weight: 600;
                line-height: 14px;
                text-align: center;
                pointer-events: none;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.35);
            }
            .agy-pause-play-badge[data-empty="true"] {
                display: none !important;
            }
            .agy-pause-play-tooltip {
                position: absolute;
                bottom: calc(100% + 7px);
                right: 0;
                background-color: var(--color-popover, #1e1e1e);
                color: var(--color-popover-foreground, #f5f5f5);
                border: 1px solid var(--color-border, rgba(255, 255, 255, 0.12));
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 11px;
                line-height: 1.3;
                white-space: nowrap;
                pointer-events: none;
                opacity: 0;
                transform: translateY(2px);
                transition: opacity 120ms ease, transform 120ms ease;
                z-index: 9999;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.28);
            }
            .agy-pause-btn-wrap:hover .agy-pause-play-tooltip {
                opacity: 1;
                transform: translateY(0);
            }
            .agy-held-queue-card {
                border-radius: 12px;
                border: 1px solid var(--color-border, rgba(255, 255, 255, 0.1));
                background-color: var(--color-card, rgba(30, 30, 30, 0.95));
                padding: 6px 10px;
                display: flex;
                flex-direction: column;
                gap: 4px;
                font-size: 12px;
                color: var(--color-foreground, #e5e5e5);
            }
            .agy-held-queue-header {
                display: flex;
                align-items: center;
                gap: 6px;
                font-weight: 500;
                font-size: 11.5px;
            }
            .agy-held-queue-count {
                font-size: 10px;
                background-color: var(--color-secondary, rgba(128, 128, 128, 0.25));
                color: var(--color-secondary-foreground, #d4d4d4);
                border-radius: 9999px;
                padding: 1px 6px;
                line-height: 1.2;
            }
            .agy-held-queue-subtitle {
                color: var(--color-muted-foreground, #888888);
                font-weight: 400;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            .agy-held-queue-list {
                display: flex;
                flex-direction: column;
                gap: 2px;
            }
            .agy-held-queue-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 8px;
                min-height: 26px;
                padding: 2px 0;
            }
            .agy-held-queue-text {
                flex: 1;
                min-width: 0;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                color: var(--color-foreground, #e5e5e5);
            }
            .agy-held-queue-actions {
                display: inline-flex;
                align-items: center;
                gap: 2px;
                flex-shrink: 0;
            }
            .agy-held-queue-action-btn {
                width: 22px;
                height: 22px;
                border-radius: 6px;
                border: none;
                background: transparent;
                color: var(--color-muted-foreground, #999999);
                display: inline-flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                padding: 0;
            }
            .agy-held-queue-action-btn:hover {
                background-color: var(--color-secondary, rgba(128, 128, 128, 0.2));
                color: var(--color-foreground, #ffffff);
            }
            div[role="article"][aria-label="User message"][data-agy-hidden-resume="true"],
            [data-testid="user-message"][data-agy-hidden-resume="true"],
            [data-testid="pending-user-messages"] > div[data-agy-hidden-resume="true"],
            div[data-agy-hidden-turn-footer="true"],
            div[data-agy-hidden-native-queue="true"] {
                display: none !important;
                min-height: 0 !important;
                margin: 0 !important;
                padding: 0 !important;
            }
        `;
        (document.head || document.documentElement).appendChild(style);
    }

    const PAUSE_SVG = '<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="6" y="4" width="4" height="16" rx="1.5"></rect><rect x="14" y="4" width="4" height="16" rx="1.5"></rect></svg>';
    const PLAY_SVG = '<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M7 4.8C7 3.98 7.9 3.48 8.6 3.92L19.4 10.72C20.05 11.13 20.05 12.07 19.4 12.48L8.6 19.28C7.9 19.72 7 19.22 7 18.4V4.8Z"></path></svg>';
    const SEND_NOW_SVG = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>';
    const EDIT_SVG = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>';
    const DELETE_SVG = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>';

    const RESUME_PROMPT_EN = "Continue executing the previous prompt from the exact point where it was paused, without losing any context.";
    const RESUME_PROMPT_PT_LEGACY = "Continue a execução do prompt anterior exatamente de onde parou, sem perder nada do contexto.";
    const RESUME_TAG = "antigravity_pause_resume";
    const CANCELLED_TEXT_ORIG = "User cancelled agent execution.";
    const PAUSED_TEXT_REPLACEMENT = "The process has been paused.";
    const STORAGE_KEY = "agy_paused_sessions_v2";

    // Map<cascadeId, { status: "pausing" | "paused" | "resuming" | "cancelled", heldQueue: Array, capturedContext: Object | null, pausedAt: number, sawIdleAfterPause: boolean }>
    const pausedMap = new Map();

    function savePausedStateToStorage() {
        try {
            const obj = {};
            for (const [k, v] of pausedMap.entries()) {
                if (!v) continue;
                const hasHeld = Array.isArray(v.heldQueue) && v.heldQueue.length > 0;
                if (v.status === "paused" || v.status === "pausing" || (v.status === "cancelled" && hasHeld)) {
                    obj[k] = {
                        status: v.status === "cancelled" ? "cancelled" : "paused",
                        heldQueue: v.heldQueue || [],
                        capturedContext: v.capturedContext || null,
                        pausedAt: v.pausedAt || Date.now(),
                    };
                }
            }
            localStorage.setItem(STORAGE_KEY, JSON.stringify(obj));
        } catch {}
    }

    function loadPausedStateFromStorage() {
        try {
            sessionStorage.removeItem("agy_paused_sessions_v1");
            const raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return;
            const obj = JSON.parse(raw);
            if (!obj || typeof obj !== "object") return;
            for (const [k, v] of Object.entries(obj)) {
                if (v && typeof v === "object") {
                    const status = v.status === "cancelled" ? "cancelled" : "paused";
                    const heldQueue = Array.isArray(v.heldQueue) ? v.heldQueue : [];
                    if (status === "cancelled" && heldQueue.length === 0) continue;
                    pausedMap.set(k, {
                        status,
                        heldQueue,
                        capturedContext: v.capturedContext || null,
                        pausedAt: v.pausedAt || (Date.now() - 1000),
                        sawIdleAfterPause: true,
                    });
                }
            }
        } catch {}
    }

    loadPausedStateFromStorage();

    function isInternalResumePayload(payload) {
        if (!payload || typeof payload !== "object") return false;
        if (Array.isArray(payload.tags) && payload.tags.some(t => t === RESUME_TAG || String(t).includes(RESUME_TAG))) {
            return true;
        }
        if (Array.isArray(payload.commentOverrides?.tags) && payload.commentOverrides.tags.includes(RESUME_TAG)) {
            return true;
        }
        const firstVal = (payload.items?.[0]?.chunk?.value || "").trim();
        if (firstVal.startsWith(RESUME_PROMPT_EN) || firstVal.startsWith(RESUME_PROMPT_PT_LEGACY)) {
            return true;
        }
        return false;
    }

    function enqueueHeldMessage(entry, payload) {
        if (!entry || !payload || typeof payload !== "object") return false;
        const rawItems = Array.isArray(payload.items) ? payload.items : [];
        const rawMedia = Array.isArray(payload.media) ? payload.media : [];
        if (rawItems.length === 0 && rawMedia.length === 0) return false;

        let msgId = payload.clientMessageId;
        if (!msgId && Array.isArray(payload.tags)) {
            const clientTag = payload.tags.find(t => typeof t === "string" && t.startsWith("client_msg:"));
            if (clientTag) msgId = clientTag.slice("client_msg:".length);
        }
        if (!msgId) {
            msgId = `held-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
        }

        const alreadyQueued = entry.heldQueue.some(q => q && q.msgId && q.msgId === msgId);
        if (alreadyQueued) return false;

        entry.heldQueue.push({
            msgId,
            deliveryStrategy: 2,
            metadata: undefined,
            step: {
                items: [...rawItems],
                media: [...rawMedia],
                artifactComments: Array.isArray(payload.artifactComments) ? [...payload.artifactComments] : [],
                fileDiffComments: Array.isArray(payload.fileDiffComments) ? [...payload.fileDiffComments] : [],
                fileComments: Array.isArray(payload.fileComments) ? [...payload.fileComments] : [],
            },
            queuedViaHook: true,
        });
        savePausedStateToStorage();
        return true;
    }

    function clearPhantomOptimisticEffects(info) {
        if (!info || !info.rawCascadeId || !info.optProvider?.registry) return;
        try {
            const reg = info.optProvider.registry;
            const effectsMap = reg._effects;
            if (effectsMap instanceof Map) {
                const effs = effectsMap.get(info.rawCascadeId);
                if (Array.isArray(effs) && effs.length > 0) {
                    for (const eff of effs) {
                        try { eff.dispose?.(); } catch {}
                    }
                    effectsMap.set(info.rawCascadeId, []);
                    const stEntry = reg.peek?.(info.rawCascadeId);
                    stEntry?.optimisticState?.setState?.(undefined);
                }
            }
        } catch {}
    }

    function wrapSingleSubmitCtx(submitCtx, cascadeKey) {
        if (!submitCtx || typeof submitCtx !== "object") return;
        if (cascadeKey) {
            submitCtx.__agyCurrentCascadeKey = cascadeKey;
        }
        if (submitCtx.__agyPauseWrapped) return;

        const origAppend = submitCtx.appendOptimisticUserMessage;
        const origSend = submitCtx.sendMessage;
        const origCancelQuestion = submitCtx.cancelActiveQuestionBeforeSend;
        const origBeginInteraction = submitCtx.beginPromptInteraction;
        submitCtx.__agyOrigAppendOptimistic = origAppend;
        submitCtx.__agyOrigSendMessage = origSend;
        submitCtx.__agyPauseWrapped = true;

        if (typeof origCancelQuestion === "function") {
            submitCtx.cancelActiveQuestionBeforeSend = function (...args) {
                const cKey = submitCtx.__agyCurrentCascadeKey || "__default_pane__";
                const entry = pausedMap.get(cKey) || pausedMap.get("__default_pane__");
                if (entry && (entry.status === "paused" || entry.status === "pausing")) {
                    return Promise.resolve();
                }
                return origCancelQuestion.apply(this, args);
            };
        }

        if (typeof origBeginInteraction === "function") {
            submitCtx.beginPromptInteraction = function (params, ...rest) {
                const cKey = params?.cascadeId || submitCtx.__agyCurrentCascadeKey || "__default_pane__";
                const entry = pausedMap.get(cKey) || pausedMap.get("__default_pane__");
                if (entry && (entry.status === "paused" || entry.status === "pausing")) {
                    return {
                        cancelled: () => {},
                        dispatched: () => {},
                        errored: () => {},
                    };
                }
                return origBeginInteraction.call(this, params, ...rest);
            };
        }

        if (typeof origAppend === "function") {
            submitCtx.appendOptimisticUserMessage = function (params, options) {
                const cKey = params?.cascadeId || submitCtx.__agyCurrentCascadeKey || "__default_pane__";
                const entry = pausedMap.get(cKey) || pausedMap.get("__default_pane__");
                if (entry && (entry.status === "paused" || entry.status === "pausing") && !isInternalResumePayload(params)) {
                    enqueueHeldMessage(entry, params);
                    scheduleSync();
                    return {
                        dispose: () => {},
                        markAsFailed: () => {},
                        hold: () => ({ dispose: () => {} }),
                    };
                }
                return origAppend.call(this, params, options);
            };
        }

        if (typeof origSend === "function") {
            submitCtx.sendMessage = function (req, ...rest) {
                const cKey = req?.cascadeId || submitCtx.__agyCurrentCascadeKey || "__default_pane__";
                const entry = pausedMap.get(cKey) || pausedMap.get("__default_pane__");
                if (entry && (entry.status === "paused" || entry.status === "pausing") && !isInternalResumePayload(req)) {
                    enqueueHeldMessage(entry, req);
                    scheduleSync();
                    return Promise.resolve({});
                }
                return origSend.call(this, req, ...rest);
            };
        }
    }

    function wrapSubmitContext(info) {
        if (!info) return;
        const { submitCtx, submitCtxList, lsClient, optProvider, interactionTracker, cascadeKey } = info;

        if (Array.isArray(submitCtxList)) {
            for (const ctx of submitCtxList) {
                wrapSingleSubmitCtx(ctx, cascadeKey);
            }
        } else if (submitCtx) {
            wrapSingleSubmitCtx(submitCtx, cascadeKey);
        }

        // Wrap singleton OptimisticTrajectoryProvider context (FB()) so every re-render of U_(a) gets the wrapped appendOptimisticUserMessage
        if (optProvider && typeof optProvider === "object") {
            if (cascadeKey) {
                optProvider.__agyCurrentCascadeKey = cascadeKey;
            }
            if (!optProvider.__agyPauseWrapped) {
                const origOptAppend = optProvider.appendOptimisticUserMessage;
                if (typeof origOptAppend === "function") {
                    optProvider.__agyOrigAppendOptimistic = origOptAppend;
                    optProvider.__agyPauseWrapped = true;
                    optProvider.appendOptimisticUserMessage = function (params, options) {
                        const cKey = params?.cascadeId || optProvider.__agyCurrentCascadeKey || "__default_pane__";
                        const entry = pausedMap.get(cKey) || pausedMap.get("__default_pane__");
                        if (entry && (entry.status === "paused" || entry.status === "pausing") && !isInternalResumePayload(params)) {
                            enqueueHeldMessage(entry, params);
                            scheduleSync();
                            return {
                                dispose: () => {},
                                markAsFailed: () => {},
                                hold: () => ({ dispose: () => {} }),
                            };
                        }
                        return origOptAppend.call(this, params, options);
                    };
                }
            }
        }

        // Wrap singleton PromptInteractionTracker context (DXb())
        if (interactionTracker && typeof interactionTracker === "object") {
            if (cascadeKey) {
                interactionTracker.__agyCurrentCascadeKey = cascadeKey;
            }
            if (!interactionTracker.__agyPauseWrapped) {
                const origBegin = interactionTracker.begin;
                if (typeof origBegin === "function") {
                    interactionTracker.__agyOrigBegin = origBegin;
                    interactionTracker.__agyPauseWrapped = true;
                    interactionTracker.begin = function (params, ...rest) {
                        const cKey = params?.cascadeId || interactionTracker.__agyCurrentCascadeKey || "__default_pane__";
                        const entry = pausedMap.get(cKey) || pausedMap.get("__default_pane__");
                        if (entry && (entry.status === "paused" || entry.status === "pausing")) {
                            return {
                                cancelled: () => {},
                                dispatched: () => {},
                                errored: () => {},
                            };
                        }
                        return origBegin.call(this, params, ...rest);
                    };
                }
            }
        }

        if (lsClient && typeof lsClient === "object") {
            if (cascadeKey) {
                lsClient.__agyCurrentCascadeKey = cascadeKey;
            }
            if (!lsClient.__agyPauseWrapped) {
                const origLsSend = lsClient.sendUserCascadeMessage;
                if (typeof origLsSend === "function") {
                    lsClient.__agyOrigSendUserCascadeMessage = origLsSend;
                    lsClient.__agyPauseWrapped = true;
                    lsClient.sendUserCascadeMessage = function (req, ...rest) {
                        const cKey = req?.cascadeId || lsClient.__agyCurrentCascadeKey || "__default_pane__";
                        const entry = pausedMap.get(cKey) || pausedMap.get("__default_pane__");
                        if (entry && (entry.status === "paused" || entry.status === "pausing") && !isInternalResumePayload(req)) {
                            enqueueHeldMessage(entry, req);
                            scheduleSync();
                            return Promise.resolve({});
                        }
                        return origLsSend.call(this, req, ...rest);
                    };
                }
            }
        }
    }

    document.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" && !ev.shiftKey) {
            const footerEl = ev.target?.closest?.('[data-testid="agent-input-box"]')?.querySelector?.(".agy-composer-footer") || document.querySelector(".agy-composer-footer");
            if (footerEl) {
                const info = inspectFooterFiber(footerEl);
                wrapSubmitContext(info);
            }
        }
    }, true);

    document.addEventListener("click", (ev) => {
        const footerEl = ev.target?.closest?.('[data-testid="agent-input-box"]')?.querySelector?.(".agy-composer-footer") || ev.target?.closest?.(".agy-composer-footer") || document.querySelector(".agy-composer-footer");
        const info = footerEl ? inspectFooterFiber(footerEl) : null;
        if (info) {
            wrapSubmitContext(info);
        }

        // Native Cancel button clicked while running
        const nativeCancelBtn = ev.target?.closest?.('[data-testid="input-cancel-button"], [data-testid="cancel-invocation-button"]');
        if (nativeCancelBtn && info?.cascadeKey) {
            const existing = pausedMap.get(info.cascadeKey);
            if (existing && Array.isArray(existing.heldQueue) && existing.heldQueue.length > 0) {
                existing.status = "cancelled";
            } else {
                pausedMap.delete(info.cascadeKey);
            }
            savePausedStateToStorage();
            scheduleSync();
        }
    }, true);

    function getReactFiber(el) {
        if (!el || typeof el !== "object") return null;
        let fiber = null;
        for (const k of Object.keys(el)) {
            if (k.startsWith("__reactFiber$")) {
                fiber = el[k];
                break;
            }
        }
        if (!fiber) return null;
        let root = fiber;
        let guard = 0;
        while (root.return && guard < 2000) {
            root = root.return;
            guard++;
        }
        if (root.stateNode && root.stateNode.current === root) {
            return fiber;
        }
        return fiber.alternate || fiber;
    }

    function cloneQueuedInputs(list) {
        if (!Array.isArray(list) || list.length === 0) return [];
        return list.map(item => ({
            msgId: item?.msgId,
            deliveryStrategy: item?.deliveryStrategy,
            metadata: item?.metadata,
            step: item?.step ? {
                items: Array.isArray(item.step.items) ? [...item.step.items] : [],
                media: Array.isArray(item.step.media) ? [...item.step.media] : [],
                artifactComments: Array.isArray(item.step.artifactComments) ? [...item.step.artifactComments] : [],
                fileDiffComments: Array.isArray(item.step.fileDiffComments) ? [...item.step.fileDiffComments] : [],
                fileComments: Array.isArray(item.step.fileComments) ? [...item.step.fileComments] : [],
            } : { items: [], media: [], artifactComments: [], fileDiffComments: [], fileComments: [] },
        }));
    }

    function inspectFooterFiber(footerEl) {
        const startFiber = getReactFiber(footerEl);
        if (!startFiber) return null;

        let footerProps = null;
        let inputBoxFiber = null;
        let inputBoxProps = null;
        let stepHandlerCtx = null;
        let lsClient = null;
        let optProvider = null;
        let interactionTracker = null;
        let submitCtx = null;
        const submitCtxList = [];

        const examineContextValue = (val) => {
            if (!val || typeof val !== "object") return;
            if (!stepHandlerCtx && typeof val.sendMessage === "function" && val.cascadeContext) {
                stepHandlerCtx = val;
            }
            if (!lsClient && typeof val.deleteAgentMessage === "function" && typeof val.sendUserCascadeMessage === "function") {
                lsClient = val;
            }
            if (!optProvider && typeof val.appendOptimisticUserMessage === "function" && val.registry && typeof val.registry.peek === "function") {
                optProvider = val;
            }
            if (!interactionTracker && typeof val.begin === "function" && typeof val.dispose === "function") {
                interactionTracker = val;
            }
        };

        const examineFiberHooks = (fiberNode) => {
            if (!fiberNode) return;
            let hook = fiberNode.memoizedState;
            let hGuard = 0;
            while (hook && hGuard < 2000) {
                const ms = hook.memoizedState;
                const candidate = Array.isArray(ms) ? ms[0] : ms;
                if (
                    candidate &&
                    typeof candidate === "object" &&
                    typeof candidate.sendMessage === "function" &&
                    typeof candidate.appendOptimisticUserMessage === "function" &&
                    candidate.inputControls &&
                    typeof candidate.inputControls.clearInput === "function"
                ) {
                    if (!submitCtx) submitCtx = candidate;
                    if (!submitCtxList.includes(candidate)) {
                        submitCtxList.push(candidate);
                    }
                }
                hook = hook.next;
                hGuard++;
            }
        };

        let curr = startFiber;
        let depth = 0;
        while (curr && depth < 300) {
            const mp = curr.memoizedProps;
            if (mp && typeof mp === "object") {
                if (
                    !footerProps &&
                    typeof mp.cancelInvocation === "function" &&
                    typeof mp.isRunning === "boolean" &&
                    "isConvoInputEmpty" in mp
                ) {
                    footerProps = mp;
                }
                if (
                    !inputBoxProps &&
                    typeof mp.handleSubmit === "function" &&
                    typeof mp.cancelInvocation === "function" &&
                    "cascadeId" in mp
                ) {
                    inputBoxFiber = curr;
                    inputBoxProps = mp;
                }
                if ("value" in mp) {
                    examineContextValue(mp.value);
                }
            }
            examineFiberHooks(curr);
            if (curr.alternate) examineFiberHooks(curr.alternate);

            let ctxDep = curr.dependencies?.firstContext;
            let cGuard = 0;
            while (ctxDep && cGuard < 50) {
                examineContextValue(ctxDep.memoizedValue);
                examineContextValue(ctxDep.context?._currentValue);
                ctxDep = ctxDep.next;
                cGuard++;
            }
            curr = curr.return;
            depth++;
        }

        if (!footerProps && !inputBoxProps) return null;

        let queuedUserInputs = [];
        if (inputBoxFiber) {
            const queue = [inputBoxFiber.child];
            let visited = 0;
            while (queue.length > 0 && visited < 200) {
                const node = queue.shift();
                if (!node) continue;
                visited++;
                const nProps = node.memoizedProps;
                if (nProps && Array.isArray(nProps.queuedUserInputs)) {
                    queuedUserInputs = nProps.queuedUserInputs;
                    break;
                }
                if (node.child) queue.push(node.child);
                if (node.sibling) queue.push(node.sibling);
            }
        }

        const rawCascadeId = inputBoxProps?.cascadeId || stepHandlerCtx?.cascadeContext?.state?.cascadeId || undefined;
        const cascadeKey = rawCascadeId || "__default_pane__";

        let trueIsRunning = null;
        try {
            const peeked = (rawCascadeId && optProvider?.registry?.peek) ? optProvider.registry.peek(rawCascadeId) : null;
            const trueStatus = peeked?.trueState?.getState?.()?.agentState?.status;
            if (typeof trueStatus === "number") {
                trueIsRunning = (trueStatus === 2);
            } else {
                const stStatus = stepHandlerCtx?.cascadeContext?.state?.agentStateProvider?.getState?.()?.status;
                if (typeof stStatus === "number") {
                    trueIsRunning = (stStatus === 2);
                }
            }
        } catch {}

        const infoObj = {
            rawCascadeId,
            cascadeKey,
            isRunning: Boolean(inputBoxProps?.isRunning ?? footerProps?.isRunning),
            trueIsRunning,
            isConvoLoading: Boolean(inputBoxProps?.isConvoLoading ?? footerProps?.isConvoLoading),
            isInputEmpty: Boolean(footerProps?.isConvoInputEmpty ?? true),
            hasAttachments: Boolean(footerProps?.hasAttachments ?? false),
            cancelInvocation: inputBoxProps?.cancelInvocation || footerProps?.cancelInvocation,
            handleSubmit: inputBoxProps?.handleSubmit,
            footerHandleSubmit: footerProps?.handleSubmit,
            lexicalRef: footerProps?.lexicalRef,
            stepHandlerCtx,
            lsClient,
            optProvider,
            interactionTracker,
            submitCtx,
            submitCtxList,
            queuedUserInputs,
        };
        wrapSubmitContext(infoObj);
        return infoObj;
    }

    function getAgentStateSnapshot(info) {
        try {
            const peeked = (info?.rawCascadeId && info?.optProvider?.registry?.peek)
                ? info.optProvider.registry.peek(info.rawCascadeId)
                : null;
            const trueAgentState = peeked?.trueState?.getState?.()?.agentState;
            if (trueAgentState) return trueAgentState;
        } catch {}
        try {
            return info?.stepHandlerCtx?.cascadeContext?.state?.agentStateProvider?.getState?.() || null;
        } catch {
            return null;
        }
    }

    function capturePartialContext(info) {
        try {
            const state = getAgentStateSnapshot(info);
            const slice = state?.trajectorySlice;
            const steps = slice?.stepsInSlice;
            if (!Array.isArray(steps) || steps.length === 0) return null;
            const tail = [];
            for (let i = Math.max(0, steps.length - 3); i < steps.length; i++) {
                const st = steps[i];
                if (!st || !st.step) continue;
                if (st.step.case === "plannerResponse" && st.step.value) {
                    const resp = (st.step.value.response || "").trim();
                    const think = (st.step.value.thinking || "").trim();
                    if (resp || think) {
                        tail.push({
                            status: st.status,
                            response: resp,
                            thinking: think,
                        });
                    }
                }
            }
            return {
                totalStepsLength: slice?.totalStepsLength ?? steps.length,
                tail,
            };
        } catch {
            return null;
        }
    }

    function buildResumePrompt(info, captured) {
        const basePrompt = RESUME_PROMPT_EN;
        if (!captured || !Array.isArray(captured.tail) || captured.tail.length === 0) {
            return basePrompt;
        }
        try {
            const stateAfter = getAgentStateSnapshot(info);
            const stepsAfter = stateAfter?.trajectorySlice?.stepsInSlice || [];
            const lastCaptured = captured.tail[captured.tail.length - 1];
            if (!lastCaptured || (!lastCaptured.response && !lastCaptured.thinking)) {
                return basePrompt;
            }
            const stillPresent = stepsAfter.some(s => {
                if (s?.step?.case !== "plannerResponse" || !s.step.value) return false;
                const r = (s.step.value.response || "").trim();
                const t = (s.step.value.thinking || "").trim();
                return (lastCaptured.response && r === lastCaptured.response) ||
                       (lastCaptured.thinking && t === lastCaptured.thinking);
            });
            if (stillPresent) {
                return basePrompt;
            }
            const parts = [basePrompt, "[Partial context received before pause]:"];
            if (lastCaptured.thinking) {
                parts.push("Partial reasoning:\n" + lastCaptured.thinking.slice(-2000));
            }
            if (lastCaptured.response) {
                parts.push("Partial response:\n" + lastCaptured.response.slice(-2000));
            }
            return parts.join("\n\n");
        } catch {
            return basePrompt;
        }
    }

    async function handlePauseClick(footerEl) {
        const info = inspectFooterFiber(footerEl);
        if (!info || !info.isRunning || typeof info.cancelInvocation !== "function") return;

        wrapSubmitContext(info);
        const key = info.cascadeKey;
        const prevEntry = pausedMap.get(key);
        const priorHeld = (prevEntry && Array.isArray(prevEntry.heldQueue)) ? prevEntry.heldQueue : [];
        const rawSnapshot = [...priorHeld, ...cloneQueuedInputs(info.queuedUserInputs)];
        const seenIds = new Set();
        const snapshotQueue = [];
        for (const item of rawSnapshot) {
            const dedupeKey = item?.msgId || extractStepPreviewText(item?.step);
            if (dedupeKey && seenIds.has(dedupeKey)) continue;
            if (dedupeKey) seenIds.add(dedupeKey);
            snapshotQueue.push(item);
        }
        const capturedContext = capturePartialContext(info);

        pausedMap.set(key, {
            status: "pausing",
            heldQueue: snapshotQueue,
            capturedContext,
            pausedAt: Date.now(),
            sawIdleAfterPause: false,
        });
        savePausedStateToStorage();
        syncFooter(footerEl);

        // Remove live queued items from language_server before cancelling so they do not auto-fire when turn becomes IDLE
        if (snapshotQueue.length > 0 && info.lsClient && typeof info.lsClient.deleteAgentMessage === "function" && info.rawCascadeId) {
            for (const qItem of snapshotQueue) {
                if (qItem.msgId && !String(qItem.msgId).startsWith("held-")) {
                    try {
                        await info.lsClient.deleteAgentMessage({
                            messageId: qItem.msgId,
                            recipient: info.rawCascadeId,
                        });
                    } catch {}
                }
            }
        }

        try {
            await info.cancelInvocation();
        } catch (err) {
            console.error("[AntigravityPause] Error pausing invocation:", err);
        }

        // Wait until React state transitions isRunning -> false before marking status = "paused"
        const waitStart = Date.now();
        while (Date.now() - waitStart < 3500) {
            const checkInfo = inspectFooterFiber(footerEl);
            if (!checkInfo || !checkInfo.isRunning) break;
            await new Promise(r => setTimeout(r, 40));
        }

        const currentEntry = pausedMap.get(key);
        if (currentEntry) {
            const postInfo = inspectFooterFiber(footerEl) || info;
            wrapSubmitContext(postInfo);
            currentEntry.status = "paused";
            currentEntry.sawIdleAfterPause = true;
            currentEntry.pausedAt = Date.now();
            savePausedStateToStorage();
        }
        syncSessionDOM();
        syncFooter(footerEl);
    }

    async function handleCancelPausedClick(footerEl) {
        const info = inspectFooterFiber(footerEl);
        const key = info?.cascadeKey || footerEl?.__agyLastCascadeKey;

        // Cancel ONLY the paused execution while preserving any queued messages in heldQueue
        if (key && pausedMap.has(key)) {
            const entry = pausedMap.get(key);
            if (entry && Array.isArray(entry.heldQueue) && entry.heldQueue.length > 0) {
                entry.status = "cancelled";
            } else {
                pausedMap.delete(key);
            }
        }
        if (pausedMap.has("__default_pane__")) {
            const defEntry = pausedMap.get("__default_pane__");
            if (defEntry && Array.isArray(defEntry.heldQueue) && defEntry.heldQueue.length > 0) {
                defEntry.status = "cancelled";
            } else {
                pausedMap.delete("__default_pane__");
            }
        }
        savePausedStateToStorage();

        syncSessionDOM();
        syncFooter(footerEl);
    }

    async function dispatchItem(info, items, media, deliveryStrategy, commentOverrides) {
        const comments = commentOverrides || {
            artifactComments: [],
            fileDiffComments: [],
            fileComments: [],
        };
        if (info.stepHandlerCtx && typeof info.stepHandlerCtx.sendMessage === "function" && info.rawCascadeId) {
            return await info.stepHandlerCtx.sendMessage({
                type: 1,
                source: "mcp",
                cascadeId: info.rawCascadeId,
                items,
                media: media || [],
                deliveryStrategy,
                commentOverrides: comments,
            });
        }
        if (typeof info.handleSubmit === "function") {
            const editor = info.lexicalRef?.current;
            const savedState = (!info.isInputEmpty && editor && typeof editor.getEditorState === "function")
                ? editor.getEditorState()
                : null;
            const res = await info.handleSubmit(
                items,
                media || [],
                () => {},
                undefined,
                deliveryStrategy,
                comments
            );
            if (savedState && editor && typeof editor.setEditorState === "function") {
                try { editor.setEditorState(savedState); } catch {}
            }
            return res;
        }
    }

    async function handlePlayClick(footerEl) {
        const info = inspectFooterFiber(footerEl);
        if (!info) return;

        const key = info.cascadeKey;
        const entry = pausedMap.get(key);
        if (!entry || entry.status !== "paused") return;

        entry.status = "resuming";
        syncFooter(footerEl);

        try {
            const queueToRestore = [...(entry.heldQueue || [])];

            const liveQueue = cloneQueuedInputs(info.queuedUserInputs);
            if (liveQueue.length > 0 && info.lsClient && typeof info.lsClient.deleteAgentMessage === "function" && info.rawCascadeId) {
                for (const qItem of liveQueue) {
                    if (queueToRestore.length === 0) {
                        queueToRestore.push(qItem);
                    }
                    if (qItem.msgId) {
                        try {
                            await info.lsClient.deleteAgentMessage({
                                messageId: qItem.msgId,
                                recipient: info.rawCascadeId,
                            });
                        } catch {}
                    }
                }
                await new Promise(r => setTimeout(r, 75));
            }

            const resumeText = buildResumePrompt(info, entry.capturedContext);
            const resumeItems = [{
                $typeName: "exa.codeium_common_pb.TextOrScopeItem",
                chunk: { case: "text", value: resumeText },
            }];

            await dispatchItem(info, resumeItems, [], 1, {
                artifactComments: [],
                fileDiffComments: [],
                fileComments: [],
                tags: [RESUME_TAG],
            });

            if (queueToRestore.length > 0) {
                const waitStart = Date.now();
                while (Date.now() - waitStart < 4500) {
                    const latest = inspectFooterFiber(footerEl);
                    if (latest && latest.isRunning) break;
                    await new Promise(r => setTimeout(r, 60));
                }
                await new Promise(r => setTimeout(r, 120));
                const latestInfo = inspectFooterFiber(footerEl) || info;
                for (const qItem of queueToRestore) {
                    const st = qItem.step || {};
                    await dispatchItem(
                        latestInfo,
                        st.items || [],
                        st.media || [],
                        2, // WHEN_IDLE (Queue)
                        {
                            artifactComments: st.artifactComments || [],
                            fileDiffComments: st.fileDiffComments || [],
                            fileComments: st.fileComments || [],
                        }
                    );
                }
            }
        } catch (err) {
            console.error("[AntigravityPause] Error resuming execution:", err);
        } finally {
            pausedMap.delete(key);
            savePausedStateToStorage();
            syncFooter(footerEl);
        }
    }

    function extractStepPreviewText(step) {
        if (!step || !Array.isArray(step.items)) return "Queued message";
        const parts = [];
        for (const it of step.items) {
            if (!it || !it.chunk) continue;
            if (it.chunk.case === "text" && typeof it.chunk.value === "string") {
                parts.push(it.chunk.value);
            } else if (it.chunk.case === "item" && it.chunk.value?.scopeItem) {
                const si = it.chunk.value.scopeItem;
                const label = si.value?.itemLabel || si.value?.name || si.value?.title || si.case || "item";
                parts.push(`@${label}`);
            }
        }
        const text = parts.join("").replace(/\s+/g, " ").trim();
        if (text) return text;
        if (Array.isArray(step.media) && step.media.length > 0) {
            return `${step.media.length} attachment(s)`;
        }
        return "Queued message";
    }

    function syncHeldQueueCard(footerEl, info, entry) {
        const inputBoxEl = footerEl.closest('[data-testid="agent-input-box"]');
        if (!inputBoxEl) return;
        const floatingContainer = inputBoxEl.firstElementChild;
        if (!floatingContainer) return;

        let card = floatingContainer.querySelector(":scope > .agy-held-queue-card");
        const items = (entry && (entry.status === "paused" || entry.status === "pausing" || entry.status === "cancelled") && Array.isArray(entry.heldQueue))
            ? entry.heldQueue
            : [];

        if (items.length === 0) {
            if (card) card.remove();
            for (const child of Array.from(floatingContainer.children)) {
                if (child.hasAttribute("data-agy-hidden-native-queue")) {
                    child.removeAttribute("data-agy-hidden-native-queue");
                }
            }
            if (entry && entry.status === "cancelled" && info?.cascadeKey) {
                pausedMap.delete(info.cascadeKey);
                savePausedStateToStorage();
            }
            return;
        }

        // Prevent duplicate stacked queue cards while React unmounts its native Queued Messages block
        for (const child of Array.from(floatingContainer.children)) {
            if (child === card || child.classList.contains("agy-held-queue-card")) continue;
            if ((child.textContent || "").includes("Queued Messages")) {
                child.setAttribute("data-agy-hidden-native-queue", "true");
            }
        }

        if (!card) {
            card = document.createElement("div");
            card.className = "agy-held-queue-card";
            floatingContainer.insertBefore(card, floatingContainer.firstChild);
        }

        const sig = `${entry.status}:` + items.map(it => `${it.msgId || ""}:${extractStepPreviewText(it.step)}`).join("|");
        if (card.getAttribute("data-sig") === sig) return;
        card.setAttribute("data-sig", sig);
        card.innerHTML = "";

        const header = document.createElement("div");
        header.className = "agy-held-queue-header";

        const titleSpan = document.createElement("span");
        titleSpan.textContent = "Queued Messages";
        const countSpan = document.createElement("span");
        countSpan.className = "agy-held-queue-count";
        countSpan.textContent = String(items.length);
        const subSpan = document.createElement("span");
        subSpan.className = "agy-held-queue-subtitle";
        subSpan.textContent = entry.status === "cancelled"
            ? "Sends after next prompt finishes (or click → to send now)"
            : "Sends after agent finishes working";

        header.appendChild(titleSpan);
        header.appendChild(countSpan);
        header.appendChild(subSpan);
        card.appendChild(header);

        const listEl = document.createElement("div");
        listEl.className = "agy-held-queue-list";

        items.forEach((qItem, idx) => {
            const row = document.createElement("div");
            row.className = "agy-held-queue-row";

            const textEl = document.createElement("div");
            textEl.className = "agy-held-queue-text";
            textEl.textContent = extractStepPreviewText(qItem.step);

            const actionsEl = document.createElement("div");
            actionsEl.className = "agy-held-queue-actions";

            const sendNowBtn = document.createElement("button");
            sendNowBtn.type = "button";
            sendNowBtn.className = "agy-held-queue-action-btn";
            sendNowBtn.title = "Send Now";
            sendNowBtn.innerHTML = SEND_NOW_SVG;
            sendNowBtn.addEventListener("click", (ev) => {
                ev.preventDefault();
                ev.stopPropagation();
                const latestInfo = inspectFooterFiber(footerEl) || info;
                const target = entry.heldQueue.splice(idx, 1)[0];
                const remaining = [...entry.heldQueue];
                if (latestInfo?.cascadeKey) {
                    pausedMap.delete(latestInfo.cascadeKey);
                }
                savePausedStateToStorage();
                syncSessionDOM();
                syncFooter(footerEl);
                if (target && latestInfo) {
                    void (async () => {
                        try {
                            const st = target.step || {};
                            await dispatchItem(latestInfo, st.items || [], st.media || [], 1, {
                                artifactComments: st.artifactComments || [],
                                fileDiffComments: st.fileDiffComments || [],
                                fileComments: st.fileComments || [],
                            });
                            if (remaining.length > 0) {
                                const waitStart = Date.now();
                                while (Date.now() - waitStart < 4500) {
                                    const check = inspectFooterFiber(footerEl);
                                    if (check && check.isRunning) break;
                                    await new Promise(r => setTimeout(r, 60));
                                }
                                await new Promise(r => setTimeout(r, 120));
                                const afterInfo = inspectFooterFiber(footerEl) || latestInfo;
                                for (const rem of remaining) {
                                    const rst = rem.step || {};
                                    await dispatchItem(afterInfo, rst.items || [], rst.media || [], 2, {
                                        artifactComments: rst.artifactComments || [],
                                        fileDiffComments: rst.fileDiffComments || [],
                                        fileComments: rst.fileComments || [],
                                    });
                                }
                            }
                        } catch (err) {
                            console.error("[AntigravityPause] Error sending queued item now:", err);
                        }
                    })();
                }
            });

            const editBtn = document.createElement("button");
            editBtn.type = "button";
            editBtn.className = "agy-held-queue-action-btn";
            editBtn.title = "Edit queued message";
            editBtn.innerHTML = EDIT_SVG;
            editBtn.addEventListener("click", (ev) => {
                ev.preventDefault();
                ev.stopPropagation();
                const latestInfo = inspectFooterFiber(footerEl) || info;
                const removed = entry.heldQueue.splice(idx, 1)[0];
                if (entry.status === "cancelled" && entry.heldQueue.length === 0 && latestInfo?.cascadeKey) {
                    pausedMap.delete(latestInfo.cascadeKey);
                }
                savePausedStateToStorage();
                if (removed && latestInfo?.submitCtx?.inputControls?.restoreInput) {
                    try {
                        latestInfo.submitCtx.inputControls.restoreInput(removed.step?.items || [], removed.step?.media || []);
                        latestInfo.lexicalRef?.current?.focus?.();
                    } catch {}
                }
                syncFooter(footerEl);
            });

            const delBtn = document.createElement("button");
            delBtn.type = "button";
            delBtn.className = "agy-held-queue-action-btn";
            delBtn.title = "Delete queued message";
            delBtn.innerHTML = DELETE_SVG;
            delBtn.addEventListener("click", (ev) => {
                ev.preventDefault();
                ev.stopPropagation();
                entry.heldQueue.splice(idx, 1);
                if (entry.status === "cancelled" && entry.heldQueue.length === 0 && info?.cascadeKey) {
                    pausedMap.delete(info.cascadeKey);
                }
                savePausedStateToStorage();
                syncFooter(footerEl);
            });

            actionsEl.appendChild(sendNowBtn);
            actionsEl.appendChild(editBtn);
            actionsEl.appendChild(delBtn);
            row.appendChild(textEl);
            row.appendChild(actionsEl);
            listEl.appendChild(row);
        });

        card.appendChild(listEl);
    }

    function ensureSlot(footerEl) {
        const rightContainer = footerEl.lastElementChild;
        if (!rightContainer) return null;

        let slot = rightContainer.querySelector(":scope > .agy-pause-play-slot");
        if (!slot) {
            slot = document.createElement("div");
            slot.className = "agy-pause-play-slot";
            slot.setAttribute("data-hidden", "true");

            // 1. Cancel button for paused state
            const cancelWrap = document.createElement("div");
            cancelWrap.className = "agy-pause-btn-wrap agy-cancel-wrap";
            cancelWrap.setAttribute("data-hidden", "true");

            const cancelBtn = document.createElement("button");
            cancelBtn.type = "button";
            cancelBtn.className = "agy-pause-cancel-btn";
            cancelBtn.setAttribute("data-testid", "input-cancel-paused-button");
            cancelBtn.setAttribute("aria-label", "Cancel paused execution");
            const cancelSquare = document.createElement("div");
            cancelSquare.className = "agy-pause-cancel-btn-square";
            cancelBtn.appendChild(cancelSquare);

            const cancelTooltip = document.createElement("div");
            cancelTooltip.className = "agy-pause-play-tooltip";
            cancelTooltip.textContent = "Cancel paused execution";

            cancelBtn.addEventListener("click", (ev) => {
                ev.preventDefault();
                ev.stopPropagation();
                void handleCancelPausedClick(footerEl);
            });

            cancelWrap.appendChild(cancelBtn);
            cancelWrap.appendChild(cancelTooltip);

            // 2. Pause / Play button
            const playWrap = document.createElement("div");
            playWrap.className = "agy-pause-btn-wrap agy-play-wrap";

            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "agy-pause-play-btn";
            btn.setAttribute("data-mode", "pause");
            btn.setAttribute("data-testid", "input-pause-button");
            btn.innerHTML = PAUSE_SVG;

            const badge = document.createElement("span");
            badge.className = "agy-pause-play-badge";
            badge.setAttribute("data-empty", "true");
            btn.appendChild(badge);

            const tooltip = document.createElement("div");
            tooltip.className = "agy-pause-play-tooltip agy-play-tooltip";
            tooltip.textContent = "Pause execution";

            btn.addEventListener("click", (ev) => {
                ev.preventDefault();
                ev.stopPropagation();
                const mode = btn.getAttribute("data-mode");
                if (mode === "pause") {
                    void handlePauseClick(footerEl);
                } else if (mode === "play") {
                    void handlePlayClick(footerEl);
                }
            });

            playWrap.appendChild(btn);
            playWrap.appendChild(tooltip);

            slot.appendChild(cancelWrap);
            slot.appendChild(playWrap);
            rightContainer.appendChild(slot);
        } else if (rightContainer.lastElementChild !== slot) {
            rightContainer.appendChild(slot);
        }
        return slot;
    }

    function syncFooter(footerEl) {
        if (!footerEl || !footerEl.isConnected) return;
        const info = inspectFooterFiber(footerEl);
        const slot = ensureSlot(footerEl);
        if (!slot) return;

        if (!info) {
            slot.setAttribute("data-hidden", "true");
            return;
        }

        wrapSubmitContext(info);

        // Migrate temporary pane key if cascadeId just resolved on a new conversation
        const prevKey = footerEl.__agyLastCascadeKey;
        if (prevKey && prevKey === "__default_pane__" && info.cascadeKey !== "__default_pane__" && pausedMap.has(prevKey)) {
            pausedMap.set(info.cascadeKey, pausedMap.get(prevKey));
            pausedMap.delete(prevKey);
            savePausedStateToStorage();
        }
        footerEl.__agyLastCascadeKey = info.cascadeKey;

        let entry = pausedMap.get(info.cascadeKey);
        const reallyRunning = (typeof info.trueIsRunning === "boolean") ? info.trueIsRunning : info.isRunning;

        if (entry && (entry.status === "paused" || entry.status === "pausing") && !reallyRunning) {
            clearPhantomOptimisticEffects(info);
        }

        if (entry && entry.status === "pausing" && !reallyRunning) {
            entry.status = "paused";
            entry.sawIdleAfterPause = true;
            entry.pausedAt = Date.now();
            savePausedStateToStorage();
        }

        const flushHeldQueueAfterStart = (queueToFlush) => {
            if (!Array.isArray(queueToFlush) || queueToFlush.length === 0) return;
            void (async () => {
                await new Promise(r => setTimeout(r, 150));
                const latestInfo = inspectFooterFiber(footerEl) || info;
                for (const qItem of queueToFlush) {
                    const st = qItem.step || {};
                    try {
                        await dispatchItem(
                            latestInfo,
                            st.items || [],
                            st.media || [],
                            2, // WHEN_IDLE (Queue)
                            {
                                artifactComments: st.artifactComments || [],
                                fileDiffComments: st.fileDiffComments || [],
                                fileComments: st.fileComments || [],
                            }
                        );
                    } catch (err) {
                        console.error("[AntigravityPause] Error flushing preserved queue:", err);
                    }
                }
            })();
        };

        if (entry && entry.status === "paused") {
            if (!reallyRunning) {
                entry.sawIdleAfterPause = true;
            } else if (entry.sawIdleAfterPause && (Date.now() - entry.pausedAt > 800)) {
                const queueToFlush = Array.isArray(entry.heldQueue) ? [...entry.heldQueue] : [];
                pausedMap.delete(info.cascadeKey);
                savePausedStateToStorage();
                entry = undefined;
                flushHeldQueueAfterStart(queueToFlush);
            }
        }

        // If user cancelled the paused prompt (keeping heldQueue) and then sent a new prompt directly,
        // flush the preserved heldQueue into language_server (WHEN_IDLE) so they run right after the new prompt finishes.
        if (entry && entry.status === "cancelled" && reallyRunning) {
            const queueToFlush = Array.isArray(entry.heldQueue) ? [...entry.heldQueue] : [];
            pausedMap.delete(info.cascadeKey);
            savePausedStateToStorage();
            entry = undefined;
            flushHeldQueueAfterStart(queueToFlush);
        }

        syncHeldQueueCard(footerEl, info, entry);

        const cancelWrap = slot.querySelector(".agy-cancel-wrap");
        const cancelBtn = slot.querySelector(".agy-pause-cancel-btn");
        const btn = slot.querySelector(".agy-pause-play-btn");
        const badge = slot.querySelector(".agy-pause-play-badge");
        const tooltip = slot.querySelector(".agy-play-tooltip");
        if (!btn || !badge || !tooltip || !cancelWrap || !cancelBtn) return;

        if (entry && (entry.status === "pausing" || entry.status === "paused" || entry.status === "resuming")) {
            slot.setAttribute("data-hidden", "false");
            cancelWrap.setAttribute("data-hidden", "false");

            if (btn.getAttribute("data-mode") !== "play") {
                btn.setAttribute("data-mode", "play");
                btn.setAttribute("data-testid", "input-play-button");
                btn.setAttribute("aria-label", "Resume execution (Play)");
                btn.innerHTML = PLAY_SVG;
                btn.appendChild(badge);
            }
            const busy = entry.status === "pausing" || entry.status === "resuming";
            btn.disabled = busy;
            cancelBtn.disabled = busy;

            const qLen = Math.max(info.queuedUserInputs?.length || 0, entry.heldQueue?.length || 0);
            if (qLen > 0) {
                badge.textContent = String(qLen);
                badge.setAttribute("data-empty", "false");
            } else {
                badge.textContent = "";
                badge.setAttribute("data-empty", "true");
            }

            if (entry.status === "pausing") {
                tooltip.textContent = "Pausing execution…";
            } else if (entry.status === "resuming") {
                tooltip.textContent = "Resuming execution…";
            } else {
                tooltip.textContent = qLen > 0
                    ? `Play: Resume execution (${qLen} queued preserved)`
                    : "Play: Resume execution from where it stopped";
            }
        } else if (info.isRunning) {
            slot.setAttribute("data-hidden", "false");
            cancelWrap.setAttribute("data-hidden", "true");

            if (btn.getAttribute("data-mode") !== "pause") {
                btn.setAttribute("data-mode", "pause");
                btn.setAttribute("data-testid", "input-pause-button");
                btn.setAttribute("aria-label", "Pause execution");
                btn.innerHTML = PAUSE_SVG;
                btn.appendChild(badge);
            }
            btn.disabled = false;
            badge.textContent = "";
            badge.setAttribute("data-empty", "true");
            tooltip.textContent = "Pause execution";
        } else {
            slot.setAttribute("data-hidden", "true");
            cancelWrap.setAttribute("data-hidden", "true");
        }
    }

    function isResumeUserMessage(msgEl) {
        if (!msgEl) return false;
        let rawText = (msgEl.textContent || "").trim();
        const srOnlyHeading = msgEl.firstElementChild;
        if (srOnlyHeading && srOnlyHeading.tagName === "H5" && srOnlyHeading.classList.contains("sr-only")) {
            const headingText = (srOnlyHeading.textContent || "").trim();
            if (headingText && rawText.startsWith(headingText)) {
                rawText = rawText.slice(headingText.length).trim();
            }
        }
        rawText = rawText.replace(/^You said\s*/i, "");
        if (
            rawText.startsWith(RESUME_PROMPT_EN) ||
            rawText.startsWith(RESUME_PROMPT_PT_LEGACY)
        ) {
            return true;
        }
        const seeds = [];
        const stepEl = msgEl.querySelector('[data-testid="user-input-step"]');
        if (stepEl) {
            const stepFiber = getReactFiber(stepEl);
            if (stepFiber) {
                if (stepFiber.return) seeds.push(stepFiber.return);
                seeds.push(stepFiber);
            }
        }
        const startFiber = getReactFiber(msgEl);
        if (startFiber) seeds.push(startFiber);

        if (seeds.length > 0) {
            const queue = seeds.slice();
            const seen = new Set();
            let visited = 0;
            while (queue.length > 0 && visited < 30) {
                const f = queue.shift();
                if (!f || seen.has(f)) continue;
                seen.add(f);
                visited++;
                const mp = f.memoizedProps;
                if (mp && typeof mp === "object") {
                    const tags = mp.step?.tags || mp.userStep?.step?.value?.tags;
                    if (Array.isArray(tags) && tags.includes(RESUME_TAG)) {
                        return true;
                    }
                    const items = mp.step?.items || mp.userStep?.step?.value?.items;
                    if (Array.isArray(items)) {
                        for (const it of items) {
                            const val = (it?.chunk?.value || it?.text || "").trim();
                            if (val.startsWith(RESUME_PROMPT_EN) || val.startsWith(RESUME_PROMPT_PT_LEGACY)) {
                                return true;
                            }
                        }
                    }
                }
                if (f.child) queue.push(f.child);
                if (f !== startFiber && f.sibling) queue.push(f.sibling);
            }
        }
        return false;
    }

    function syncSessionDOM() {
        const footerEl = document.querySelector(".agy-composer-footer");
        const activeKey = footerEl?.__agyLastCascadeKey;
        const activeEntry = activeKey ? pausedMap.get(activeKey) : undefined;
        const isCurrentlyPaused = Boolean(activeEntry && (activeEntry.status === "paused" || activeEntry.status === "pausing"));

        // 1. Toggle notice text based on whether the active session is currently paused
        const cancelNotices = document.querySelectorAll("div.text-secondary-foreground, [aria-live]");
        for (let i = 0; i < cancelNotices.length; i++) {
            const el = cancelNotices[i];
            if (el.childNodes.length === 1 && el.firstChild && el.firstChild.nodeType === 3) {
                if (isCurrentlyPaused) {
                    if (el.firstChild.nodeValue === CANCELLED_TEXT_ORIG) {
                        el.firstChild.nodeValue = PAUSED_TEXT_REPLACEMENT;
                    }
                } else {
                    if (el.firstChild.nodeValue === PAUSED_TEXT_REPLACEMENT) {
                        el.firstChild.nodeValue = CANCELLED_TEXT_ORIG;
                    }
                }
            }
        }

        // 2. Hide internal continuation prompts from the session UI
        const userMsgs = document.querySelectorAll('div[role="article"][aria-label="User message"], [data-testid="user-message"]');
        const resumeTurnOuters = new Set();

        for (let i = 0; i < userMsgs.length; i++) {
            const msgEl = userMsgs[i];
            const isResume = isResumeUserMessage(msgEl);
            const pendingRow = msgEl.closest('[data-testid="pending-user-messages"] > div');

            if (isResume) {
                if (msgEl.getAttribute("data-agy-hidden-resume") !== "true") {
                    msgEl.setAttribute("data-agy-hidden-resume", "true");
                }
                if (pendingRow) {
                    if (pendingRow.getAttribute("data-agy-hidden-resume") !== "true") {
                        pendingRow.setAttribute("data-agy-hidden-resume", "true");
                    }
                } else {
                    const turnInner = msgEl.closest('[data-turn-content]') || msgEl.parentElement;
                    const turnOuter = turnInner ? turnInner.parentElement : null;
                    if (turnOuter) {
                        resumeTurnOuters.add(turnOuter);
                    }
                }
            } else {
                if (msgEl.hasAttribute("data-agy-hidden-resume")) {
                    msgEl.removeAttribute("data-agy-hidden-resume");
                }
                if (pendingRow && pendingRow.hasAttribute("data-agy-hidden-resume")) {
                    pendingRow.removeAttribute("data-agy-hidden-resume");
                }
            }
        }

        // Hide pending-user-messages container if all pending rows are hidden resume prompts
        const pendingContainers = document.querySelectorAll('[data-testid="pending-user-messages"]');
        for (let i = 0; i < pendingContainers.length; i++) {
            const pc = pendingContainers[i];
            const children = pc.children;
            let anyVisible = false;
            for (let j = 0; j < children.length; j++) {
                if (children[j].getAttribute("data-agy-hidden-resume") !== "true") {
                    anyVisible = true;
                    break;
                }
            }
            if (!anyVisible && children.length > 0) {
                pc.style.setProperty("display", "none", "important");
            } else {
                pc.style.removeProperty("display");
            }
        }

        // Hide intermediate turn feedback footer (div.pt-3) on turns that continue into a resumed turn
        const prevHiddenFooters = document.querySelectorAll('div[data-agy-hidden-turn-footer="true"]');
        for (let i = 0; i < prevHiddenFooters.length; i++) {
            const footerDiv = prevHiddenFooters[i];
            const turnOuter = footerDiv.parentElement?.parentElement;
            const nextTurnOuter = turnOuter ? turnOuter.nextElementSibling : null;
            if (!nextTurnOuter || !resumeTurnOuters.has(nextTurnOuter)) {
                footerDiv.removeAttribute("data-agy-hidden-turn-footer");
            }
        }
        for (const resumeOuter of resumeTurnOuters) {
            const prevTurnOuter = resumeOuter.previousElementSibling;
            if (prevTurnOuter) {
                const prevInner = prevTurnOuter.firstElementChild;
                if (prevInner) {
                    const children = prevInner.children;
                    for (let j = 0; j < children.length; j++) {
                        const ch = children[j];
                        if (ch.tagName === "DIV" && ch.classList.contains("pt-3")) {
                            if (ch.getAttribute("data-agy-hidden-turn-footer") !== "true") {
                                ch.setAttribute("data-agy-hidden-turn-footer", "true");
                            }
                        }
                    }
                }
            }
        }
    }

    function syncAllFooters() {
        const footers = document.querySelectorAll(".agy-composer-footer");
        for (let i = 0; i < footers.length; i++) {
            syncFooter(footers[i]);
        }
        syncSessionDOM();
    }

    let rafPending = false;
    function scheduleSync() {
        if (rafPending) return;
        rafPending = true;
        requestAnimationFrame(() => {
            rafPending = false;
            syncAllFooters();
        });
    }

    const observer = new MutationObserver(scheduleSync);
    observer.observe(document.documentElement, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ["class", "disabled", "data-testid", "aria-label"],
    });

    setInterval(syncAllFooters, 250);
    syncAllFooters();
})();"""


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
        return len(get_running_app_pids(app_paths)) > 0


def get_running_app_pids(app_paths: AppPaths) -> list:
    """Returns a list of PIDs belonging to the running Antigravity application."""
    if not app_paths:
        return []
    pids = []
    my_pid = os.getpid()

    if sys.platform == "win32":
        try:
            res = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Antigravity.exe", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in res.stdout.strip().splitlines():
                parts = line.split('","')
                if len(parts) >= 2:
                    pid_str = parts[1].replace('"', "").strip()
                    if pid_str.isdigit() and int(pid_str) != my_pid:
                        pids.append(int(pid_str))
        except Exception:
            pass
    elif sys.platform == "darwin":
        try:
            bin_target = f"{app_paths.app_root}/Contents/MacOS/Antigravity"
            res = subprocess.run(["pgrep", "-f", bin_target], capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout:
                for line in res.stdout.strip().split():
                    if line.isdigit() and int(line) != my_pid:
                        pids.append(int(line))
        except Exception:
            pass
    else:
        # Linux: Inspect /proc for exact binary paths inside app_root
        app_root_real = os.path.realpath(app_paths.app_root)
        try:
            for entry in os.listdir("/proc"):
                if not entry.isdigit():
                    continue
                pid = int(entry)
                if pid in (my_pid, 1):
                    continue
                try:
                    exe_path = os.path.realpath(os.path.join("/proc", entry, "exe"))
                    if exe_path.startswith(app_root_real):
                        pids.append(pid)
                        continue
                    with open(os.path.join("/proc", entry, "cmdline"), "rb") as f:
                        cmdline = f.read().decode("utf-8", "ignore")
                    if (app_root_real in cmdline or app_paths.app_root in cmdline) and "patch_antigravity" not in cmdline:
                        pids.append(pid)
                except Exception:
                    continue
        except Exception:
            pass
    return pids


def is_running_inside_app(app_paths: AppPaths) -> bool:
    """Checks if the current Python script is running as a child or descendant of Antigravity."""
    if sys.platform != "linux" or not app_paths:
        return False
    app_pids = set(get_running_app_pids(app_paths))
    curr = os.getppid()
    visited = set()
    while curr > 1 and curr not in visited:
        visited.add(curr)
        if curr in app_pids:
            return True
        try:
            with open(f"/proc/{curr}/stat", "r") as f:
                parts = f.read().split()
                curr = int(parts[3])
        except Exception:
            break
    return False


def kill_running_app(app_paths: AppPaths):
    """Terminates running instances of Antigravity safely."""
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
        # Linux: Terminate targeted PIDs directly without pkill to avoid self-termination
        import signal
        pids = get_running_app_pids(app_paths)
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            except Exception as e:
                log_warn(f"Notice while terminating PID {pid}: {e}")

        for _ in range(10):
            remaining = get_running_app_pids(app_paths)
            if not remaining:
                break
            time.sleep(0.3)

        remaining = get_running_app_pids(app_paths)
        for pid in remaining:
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass

    # Ensure processes have completely exited and released file locks across all platforms
    for _ in range(10):
        if not is_app_running(app_paths):
            break
        time.sleep(0.5)
    time.sleep(1.0 if sys.platform == "win32" else 0.5)


def safe_copy_tree(src_dir: str, dst_dir: str):
    """Recursively copies src_dir into dst_dir, unlinking existing files first.

    Unlinking existing files first avoids ETXTBSY on Linux when updating binaries or
    shared libraries that are currently open/mapped in memory.
    """
    for root, dirs, files in os.walk(src_dir):
        rel_path = os.path.relpath(root, src_dir)
        target_dir = dst_dir if rel_path == "." else os.path.join(dst_dir, rel_path)
        os.makedirs(target_dir, exist_ok=True)
        for f in files:
            src_file = os.path.join(root, f)
            dst_file = os.path.join(target_dir, f)
            if os.path.islink(dst_file) or os.path.exists(dst_file):
                try:
                    os.unlink(dst_file)
                except Exception:
                    try:
                        os.remove(dst_file)
                    except Exception:
                        pass
            if os.path.islink(src_file):
                link_target = os.readlink(src_file)
                os.symlink(link_target, dst_file)
            else:
                shutil.copy2(src_file, dst_file)


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


def is_native_window_persistence_supported(header_or_app_paths, code: str = None) -> bool:
    """Checks whether Antigravity natively persists window state (v2.29.0+)."""
    if code and ("trackWindowState" in code or "resolveInitialWindowState" in code):
        return True

    if isinstance(header_or_app_paths, dict):
        dist_files = header_or_app_paths.get("files", {}).get("dist", {}).get("files", {})
        if "windowState.js" in dist_files:
            return True

    if hasattr(header_or_app_paths, "is_unpacked") and header_or_app_paths.is_unpacked:
        if header_or_app_paths.app_dir:
            ws_path = os.path.join(header_or_app_paths.app_dir, "dist", "windowState.js")
            if os.path.exists(ws_path):
                return True

    return False


def generate_patched_utils_js(original_code: str) -> str:
    """Injects window persistence logic into dist/utils.js."""
    if PATCH_MARKER in original_code:
        return original_code

    if is_native_window_persistence_supported(None, original_code):
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

    # Target 1: createWindow signature (compatible with 2 or 3 parameters)
    if target_create_window not in original_code:
        match_cw = re.search(r"function\s+createWindow\s*\(\s*url\s*,\s*storageManager(?:\s*,\s*options)?\s*\)\s*\{", original_code)
        if match_cw:
            target_create_window = match_cw.group(0)
            replacement_create_window = f"""{target_create_window}
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


def is_pause_patch_up_to_date(code: str) -> bool:
    """Checks whether the currently injected Pause/Play renderer script matches the latest version."""
    if PAUSE_PATCH_MARKER not in code:
        return False
    expected_decl = f"const _ANTIGRAVITY_PAUSE_PLAY_SCRIPT = {json.dumps(PAUSE_RENDERER_JS)};"
    return expected_decl in code


def generate_pause_patched_utils_js(original_code: str) -> str:
    """Injects or updates the Pause/Play prompt execution button in dist/utils.js via webContents."""
    encoded_script = json.dumps(PAUSE_RENDERER_JS)
    expected_decl = f"const _ANTIGRAVITY_PAUSE_PLAY_SCRIPT = {encoded_script};"

    if PAUSE_PATCH_MARKER in original_code:
        if expected_decl in original_code:
            return original_code
        updated = re.sub(
            r"const\s+_ANTIGRAVITY_PAUSE_PLAY_SCRIPT\s*=\s*[^\r\n]+",
            lambda _: expected_decl,
            original_code,
            count=1,
        )
        if expected_decl in updated:
            return updated

    pause_prelude = f"\n{PAUSE_PATCH_MARKER}\n{expected_decl}\n"

    pause_listeners = f"""    {PAUSE_PATCH_MARKER}
    const _agyPauseWc = (typeof getHubWebContents === "function" ? getHubWebContents(win) : null) || win.webContents;
    const _injectAntigravityPausePlay = () => {{
        if (win.isDestroyed() || !_agyPauseWc || (typeof _agyPauseWc.isDestroyed === "function" && _agyPauseWc.isDestroyed())) return;
        _agyPauseWc.executeJavaScript(_ANTIGRAVITY_PAUSE_PLAY_SCRIPT).catch(() => {{}});
    }};
    if (_agyPauseWc && !(typeof _agyPauseWc.isDestroyed === "function" && _agyPauseWc.isDestroyed())) {{
        _agyPauseWc.on("dom-ready", _injectAntigravityPausePlay);
        _agyPauseWc.on("did-finish-load", _injectAntigravityPausePlay);
    }}"""

    target_load_url = "void win.loadURL(url);"
    if target_load_url in original_code:
        target_to_replace = target_load_url
        replacement_to_use = f"{pause_listeners}\n\n    {target_load_url}"
    else:
        match_lu = re.search(r"void\s+win\.loadURL\s*\(\s*url\s*\)\s*;", original_code)
        if match_lu:
            target_to_replace = match_lu.group(0)
            replacement_to_use = f"{pause_listeners}\n\n    {target_to_replace}"
        else:
            raise RuntimeError("Snippet 'void win.loadURL(url);' not found in dist/utils.js")

    return pause_prelude + original_code.replace(target_to_replace, replacement_to_use, 1)


def apply_patch(app_paths: AppPaths, force_kill: bool = False, add_pause: bool = False):
    """Applies the window size persistence patch and/or Pause/Play button patch to the targeted installation."""
    if app_paths.is_unpacked:
        utils_path = os.path.join(app_paths.app_dir, "dist", "utils.js")
        if not os.path.exists(utils_path):
            app_ver = extract_app_version_from_dir(app_paths.app_dir)
            log_success(f"Detected Antigravity IDE v{app_ver} ({app_paths.app_root}).")
            log_success(
                "Antigravity IDE natively persists window geometry (width, height, coordinates, and maximized state)."
            )
            if add_pause:
                log_warn("Note: --add-pause requires dist/utils.js (Electron shell), which was not found in this layout.")
            else:
                log("No patch required. Enjoy official window persistence out of the box!")
            remove_patch_info(app_paths)
            return

        with open(utils_path, "r", encoding="utf-8") as f:
            code = f.read()

        is_native = is_native_window_persistence_supported(app_paths, code)
        has_window_patch = PATCH_MARKER in code
        has_pause_patch = PAUSE_PATCH_MARKER in code
        pause_up_to_date = is_pause_patch_up_to_date(code)

        need_window_patch = (not is_native) and (not has_window_patch)
        need_pause_patch = add_pause and (not pause_up_to_date)

        if not need_window_patch and not need_pause_patch:
            app_ver = extract_app_version_from_dir(app_paths.app_dir)
            if add_pause and pause_up_to_date:
                log_warn("Pause/Play button patch (--add-pause) is already applied and up to date!")
                return
            if is_native:
                log_success(f"Detected Antigravity v{app_ver} ({app_paths.app_root}).")
                log_success(
                    "Antigravity natively persists window geometry (width, height, coordinates, and maximized state)."
                )
                if has_pause_patch:
                    log_success("Pause/Play prompt button (--add-pause) is also ACTIVE.")
                else:
                    log("No window patch required. (Tip: use --add-pause to add the Pause/Play prompt button!)")
                    remove_patch_info(app_paths)
                return
            log_warn("Window persistence patch is already applied to this installation!")
            return

        patched_code = code
        if need_window_patch:
            log("Injecting geometry persistence logic into dist/utils.js...")
            patched_code = generate_patched_utils_js(patched_code)
        if need_pause_patch:
            if has_pause_patch:
                log("Updating Pause/Play prompt execution button logic (--add-pause) in dist/utils.js...")
            else:
                log("Injecting Pause/Play prompt execution button logic (--add-pause) into dist/utils.js...")
            patched_code = generate_pause_patched_utils_js(patched_code)

        if is_app_running(app_paths):
            if force_kill:
                kill_running_app(app_paths)
            else:
                log_warn("Antigravity is currently running.")
                if sys.stdin.isatty():
                    try:
                        resp = input("Do you want to close Antigravity to apply the patch now? [y/N]: ").strip().lower()
                        if resp in ("y", "yes", "s", "sim"):
                            kill_running_app(app_paths)
                        else:
                            log_error("Operation aborted. Please close Antigravity before applying the patch.")
                            sys.exit(1)
                    except (EOFError, KeyboardInterrupt):
                        log_error("\nOperation aborted.")
                        sys.exit(1)
                else:
                    log_error("Antigravity is running. Close it or use --kill to automatically terminate it.")
                    sys.exit(1)
        backup_file = os.path.join(app_paths.app_dir, "dist", "utils.js.orig")
        if not os.path.exists(backup_file) and not has_window_patch and not has_pause_patch:
            shutil.copy2(utils_path, backup_file)
        with open(utils_path, "w", encoding="utf-8") as f:
            f.write(patched_code)
        log_success("PATCH APPLIED SUCCESSFULLY to unpacked installation!")
        return

    asar_path = app_paths.asar_path

    if not asar_path or not os.path.exists(asar_path):
        log_error(f"app.asar not found at: {asar_path}")
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

    is_native = is_native_window_persistence_supported(header, original_utils_code)
    has_window_patch = PATCH_MARKER in original_utils_code
    has_pause_patch = PAUSE_PATCH_MARKER in original_utils_code
    pause_up_to_date = is_pause_patch_up_to_date(original_utils_code)

    need_window_patch = (not is_native) and (not has_window_patch)
    need_pause_patch = add_pause and (not pause_up_to_date)

    if not need_window_patch and not need_pause_patch:
        if add_pause and pause_up_to_date:
            log_warn("Pause/Play button patch (--add-pause) is already applied and up to date!")
            if is_native:
                log_success(f"Native window state persistence is also active (v{app_version}).")
            elif has_window_patch:
                log_success("Window persistence patch is also active.")
            return

        if is_native:
            log_success(f"Detected Antigravity v{app_version} with official native window state persistence!")
            log_success(
                "Antigravity natively persists window geometry (width, height, coordinates, and maximized state) in this version."
            )
            if has_pause_patch:
                log_success("Pause/Play prompt button patch (--add-pause) is currently ACTIVE.")
            else:
                log("No window persistence ASAR patch required. Enjoy official window persistence out of the box!")
                log("Tip: Run with --add-pause if you want to inject the Pause/Play prompt execution button.")
                remove_patch_info(app_paths)
            return

        log_warn("Window persistence patch is already applied to this installation!")
        if not has_pause_patch:
            log("Tip: Run with --add-pause if you also want to inject the Pause/Play prompt execution button.")
        return

    patched_utils_code = original_utils_code
    if need_window_patch:
        log("Injecting geometry persistence logic (size, position, maximized state)...")
        patched_utils_code = generate_patched_utils_js(patched_utils_code)
    elif is_native:
        log_success(f"Antigravity v{app_version} natively persists window geometry; keeping native window state manager intact.")

    if need_pause_patch:
        if has_pause_patch:
            log("Updating Pause/Play prompt execution button logic (--add-pause)...")
        else:
            log("Injecting Pause/Play prompt execution button logic (--add-pause)...")
        patched_utils_code = generate_pause_patched_utils_js(patched_utils_code)

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

    if is_app_running(app_paths):
        if force_kill:
            kill_running_app(app_paths)
        else:
            log_warn("Antigravity is currently running.")
            if sys.stdin.isatty():
                try:
                    resp = input("Do you want to close Antigravity to apply the patch now? [y/N]: ").strip().lower()
                    if resp in ("y", "yes", "s", "sim"):
                        kill_running_app(app_paths)
                    else:
                        log_error("Operation aborted. Please close Antigravity before applying the patch.")
                        sys.exit(1)
                except (EOFError, KeyboardInterrupt):
                    log_error("\nOperation aborted.")
                    sys.exit(1)
            else:
                log_error("Antigravity is running. Close it or use --kill to automatically terminate it.")
                sys.exit(1)

    try:
        with open(asar_path, "rb") as f:
            current_asar_hash = hashlib.sha256(f.read()).hexdigest()

        already_patched = has_window_patch or has_pause_patch
        existing_info = load_patch_info(app_paths) or {}
        original_clean_hash = existing_info.get("original_asar_sha256") or current_asar_hash

        # Check if backup_orig already exists from an older version (only update if current ASAR is clean stock)
        if not already_patched:
            original_clean_hash = current_asar_hash
            if os.path.exists(backup_orig):
                with open(backup_orig, "rb") as f:
                    old_backup_hash = hashlib.sha256(f.read()).hexdigest()
                if old_backup_hash != current_asar_hash:
                    log_warn("Detected a newly updated stock Antigravity installation!")
                    prev_backup = f"{backup_orig}.prev-{time.strftime('%Y%m%d-%H%M%S')}"
                    log(f"Archiving previous backup to: {prev_backup}")
                    shutil.copy2(backup_orig, prev_backup)
                    log(f"Updating master factory backup to current stock version: {backup_orig}")
                    shutil.copy2(asar_path, backup_orig)
            else:
                log(f"Creating permanent original backup at: {backup_orig}")
                shutil.copy2(asar_path, backup_orig)
        elif not os.path.exists(backup_orig):
            log(f"Creating backup at: {backup_orig}")
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
                "pause_patch_marker": PAUSE_PATCH_MARKER if PAUSE_PATCH_MARKER in patched_utils_code else None,
                "window_patch_applied": bool(PATCH_MARKER in patched_utils_code),
                "pause_patch_applied": bool(PAUSE_PATCH_MARKER in patched_utils_code),
                "app_version": app_version,
                "original_asar_sha256": original_clean_hash,
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
    if PATCH_MARKER in patched_utils_code or is_native:
        print("  • Antigravity will persist window size, position, and maximized state.")
    if PAUSE_PATCH_MARKER in patched_utils_code:
        print("  • Pause/Play button (--add-pause) enabled next to Queue message / Cancel.")
        print("  • Pausing freezes current prompt execution and preserves queued messages.")
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
                            rb'(?:P\x00r\x00o\x00d\x00u\x00c\x00t\x00|F\x00i\x00l\x00e\x00)V\x00e\x00r\x00s\x00i\x00o\x00n\x00\x00\x00((?:[0-9.]\x00)+)',
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

    Only applies to Antigravity IDE targets (which use product.json / Cloud Run feed).
    Returns a dict with update info if an update is available, or None.
    """
    if not app_paths:
        return None
    try:
        product = get_app_product_info(app_paths)
        is_ide = (
            app_paths.is_unpacked
            or "ideVersion" in product
            or product.get("applicationName") == "antigravity-ide"
            or product.get("nameShort") == "Antigravity IDE"
        )
        if not is_ide:
            return None

        machine = platform.machine().lower()
        arch = "arm64" if machine in ("arm64", "aarch64") else "x64"

        if sys.platform == "darwin":
            platform_arch = f"darwin-{arch}"
        elif sys.platform == "win32":
            platform_arch = f"win32-{arch}-user"
        else:
            platform_arch = f"linux-{arch}"

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


def apply_pending_update(app_paths: AppPaths, force_kill: bool = False, add_pause: bool = False):
    """Applies a pending official update and automatically reapplies the window persistence patch."""
    prev_info = load_patch_info(app_paths) or {}
    effective_add_pause = bool(add_pause or prev_info.get("pause_patch_applied"))
    if not effective_add_pause:
        try:
            if app_paths.is_unpacked and app_paths.app_dir:
                upath = os.path.join(app_paths.app_dir, "dist", "utils.js")
                if os.path.exists(upath):
                    with open(upath, "r", encoding="utf-8", errors="ignore") as f:
                        if PAUSE_PATCH_MARKER in f.read():
                            effective_add_pause = True
            elif app_paths.asar_path and os.path.exists(app_paths.asar_path):
                h, p = parse_asar(app_paths.asar_path)
                ue = h["files"]["dist"]["files"]["utils.js"]
                uc = p[int(ue["offset"]) : int(ue["offset"]) + ue["size"]].decode("utf-8", "ignore")
                if PAUSE_PATCH_MARKER in uc:
                    effective_add_pause = True
        except Exception:
            pass

    update_file, update_version = find_pending_update()

    if not update_file:
        product = get_app_product_info(app_paths)
        is_ide = (
            app_paths.is_unpacked
            or "ideVersion" in product
            or product.get("applicationName") == "antigravity-ide"
            or product.get("nameShort") == "Antigravity IDE"
        )
        if is_ide:
            log("Checking official Antigravity IDE update server for available updates...")
            online_update = check_online_update(app_paths)
            if not online_update:
                log_success("Antigravity IDE is already up to date! No updates available.")
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
        else:
            log_warn("No pending official update found in local updater cache.")
            log("If Antigravity recently notified you of an update, ensure it has finished downloading.")
            log("You can also download the latest version directly from https://antigravity.google/download")
            return

    if update_file and update_version == "latest" and update_file.lower().endswith((".tar.gz", ".tgz", ".tar")):
        try:
            import tarfile
            with tarfile.open(update_file, "r:*") as tf:
                for member in tf.getmembers():
                    if member.name.endswith("resources/app/product.json"):
                        f = tf.extractfile(member)
                        if f:
                            pdata = json.load(f)
                            update_version = pdata.get("ideVersion") or pdata.get("productVersion") or "latest"
                            break
        except Exception:
            pass
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
            apply_patch(new_app_paths, force_kill=force_kill, add_pause=effective_add_pause)
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

    def prompt_close_app_for_update() -> bool:
        if is_app_running(app_paths):
            # On Linux, check if the updater is being run from inside Antigravity itself
            if sys.platform.startswith("linux") and is_running_inside_app(app_paths):
                log_warn("Antigravity is currently running (updater launched from inside its integrated terminal).")
                log("Applying update in-place safely without terminating current session...")
                log("Please restart Antigravity IDE after the update completes to load the new version.")
                return True

            if force_kill:
                kill_running_app(app_paths)
                return True

            log_warn("Antigravity is currently running. It must be closed to apply the update.")
            if sys.platform.startswith("linux"):
                if sys.stdin.isatty():
                    try:
                        ans = input("Close Antigravity automatically and continue with update? [Y/n]: ").strip().lower()
                        if ans and ans not in ("y", "yes", "s", "sim"):
                            log("Applying update in-place without closing. Please restart Antigravity IDE when done.")
                            return True
                        kill_running_app(app_paths)
                        return True
                    except (EOFError, KeyboardInterrupt):
                        log_error("\nUpdate cancelled.")
                        return False
                else:
                    log("Applying update in-place safely without closing. Please restart Antigravity IDE when done.")
                    return True
            else:
                if sys.stdin.isatty():
                    try:
                        ans = input("Close Antigravity automatically and continue with update? [Y/n]: ").strip().lower()
                        if ans and ans not in ("y", "yes", "s", "sim"):
                            log_error("Update cancelled by user.")
                            return False
                        kill_running_app(app_paths)
                        return True
                    except (EOFError, KeyboardInterrupt):
                        log_error("\nUpdate cancelled.")
                        return False
                else:
                    log_error("Antigravity is running. Close it or use --kill to automatically terminate it before updating.")
                    sys.exit(1)
        return True

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

            if not prompt_close_app_for_update():
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
                if not prompt_close_app_for_update():
                    return
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
                if not prompt_close_app_for_update():
                    return
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
                if not prompt_close_app_for_update():
                    return
                log(f"Replacing AppImage at {app_paths.app_root}...")
                if os.path.exists(app_paths.app_root):
                    try:
                        os.unlink(app_paths.app_root)
                    except Exception:
                        pass
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
                if not prompt_close_app_for_update():
                    return
                log(f"Installing update files into {app_paths.app_root}...")
                safe_copy_tree(source_dir, app_paths.app_root)
            else:
                with zipfile.ZipFile(update_file, "r") as zf:
                    zf.extractall(temp_dir)
                extracted_items = [i for i in os.listdir(temp_dir) if not i.startswith(".")]
                if len(extracted_items) == 1 and os.path.isdir(os.path.join(temp_dir, extracted_items[0])):
                    source_dir = os.path.join(temp_dir, extracted_items[0])
                else:
                    source_dir = temp_dir
                if not prompt_close_app_for_update():
                    return
                log(f"Installing update files into {app_paths.app_root}...")
                safe_copy_tree(source_dir, app_paths.app_root)

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

        log_success(f"Official update v{update_version} files installed successfully!")

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    # Clean up all pending updater caches across candidate paths
    log("Cleaning up updater cache...")
    try:
        if os.path.isfile(update_file):
            os.remove(update_file)
        shutil.rmtree(os.path.dirname(update_file), ignore_errors=True)
    except Exception:
        pass

    for cdir in [
        os.path.expanduser("~/.cache/com.google.antigravity/pending"),
        os.path.expanduser("~/.cache/antigravity-updater/pending"),
        os.path.expanduser("~/.cache/antigravity-ide-updater/pending"),
        os.path.expanduser("~/.cache/Antigravity IDE/pending"),
        os.path.expanduser("~/.config/Antigravity IDE/pending"),
        os.path.expanduser("~/.config/antigravity-ide/pending"),
    ]:
        if os.path.exists(cdir):
            try:
                shutil.rmtree(cdir, ignore_errors=True)
            except Exception:
                pass

    # Re-apply persistence patch to the fresh install
    log("Applying window persistence patch to new installation...")
    new_app_paths = find_antigravity_app(app_paths.app_root)
    apply_patch(new_app_paths, force_kill=False, add_pause=effective_add_pause)
    if sys.platform.startswith("linux"):
        ensure_linux_desktop_entry(new_app_paths)

    final_ver = (
        extract_app_version_from_dir(new_app_paths.app_dir)
        if new_app_paths.is_unpacked
        else update_version
    )
    log_success(f"All set! Antigravity is now updated to v{final_ver} with window persistence active.")
    if is_app_running(new_app_paths):
        log("\033[1;33m[!] Notice: Antigravity is currently running. Please restart the application to launch the newly installed version.\033[0m")


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
                log_success("Status: Window persistence PATCH IS ACTIVE and functioning (unpacked).")
            elif is_native_window_persistence_supported(app_paths, code):
                log_success("Status: Native window state persistence is officially built-in (v2.29.0+).")
                log("Antigravity natively persists window dimensions, screen coordinates, and maximized state.")
            else:
                log_warn("Status: Window persistence PATCH NOT APPLIED (window uses default 1400x900 size).")
            if PAUSE_PATCH_MARKER in code:
                log_success("Pause/Play Button (--add-pause): ACTIVE and functioning.")
            else:
                log("Pause/Play Button (--add-pause): Not applied (use --add-pause to enable).")
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
    is_pause_patched = False
    code = ""
    try:
        utils_entry = header["files"]["dist"]["files"]["utils.js"]
        old_offset = int(utils_entry["offset"])
        old_size = utils_entry["size"]
        code = payload[old_offset : old_offset + old_size].decode("utf-8", "ignore")
        if PATCH_MARKER in code:
            is_patched = True
        if PAUSE_PATCH_MARKER in code:
            is_pause_patched = True
    except Exception as e:
        log_error(f"Error inspecting ASAR: {e}")

    if is_patched:
        log_success("Status: Window persistence PATCH IS ACTIVE and functioning.")
        if patch_info and patch_info.get("patched_at"):
            log(f"Patched at: {patch_info['patched_at']}")
    elif is_native_window_persistence_supported(header, code):
        log_success("Status: Native window state persistence is officially built-in (v2.29.0+).")
        log("Antigravity natively persists window dimensions, screen coordinates, and maximized state.")
    else:
        log_warn("Status: Window persistence PATCH NOT APPLIED (window uses default 1400x900 size).")
        if patch_info and patch_info.get("app_version") and patch_info["app_version"] != app_version:
            log_warn(
                f"Notice: App was previously patched on version {patch_info['app_version']}, "
                f"but has since been officially updated to {app_version}."
            )
            log("Run without arguments to apply persistence to this new version.")

    if is_pause_patched:
        log_success("Pause/Play Button (--add-pause): ACTIVE and functioning.")
        if not is_patched and patch_info and patch_info.get("patched_at"):
            log(f"Patched at: {patch_info['patched_at']}")
    else:
        log("Pause/Play Button (--add-pause): Not applied (use --add-pause to enable).")

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

    if not asar_path or not os.path.exists(asar_path):
        log_error(f"app.asar not found at: {asar_path}")
        sys.exit(1)

    if not os.path.exists(backup_orig):
        try:
            curr_header, curr_payload = parse_asar(asar_path)
            app_version = extract_app_version_from_asar(curr_header, curr_payload)
            utils_entry = curr_header["files"]["dist"]["files"]["utils.js"]
            curr_utils_code = curr_payload[
                int(utils_entry["offset"]) : int(utils_entry["offset"]) + utils_entry["size"]
            ].decode("utf-8", "ignore")
            has_any_patch = (PATCH_MARKER in curr_utils_code) or (PAUSE_PATCH_MARKER in curr_utils_code)
            if is_native_window_persistence_supported(curr_header, curr_utils_code) and not has_any_patch:
                log_success(f"Antigravity v{app_version} already features official native window state persistence.")
                log("The application is in stock factory state with native window persistence active. No restoration needed.")
                remove_patch_info(app_paths)
                return
            elif not has_any_patch:
                log_warn(f"Antigravity v{app_version} is already running in stock factory state without patches.")
                return
        except Exception:
            pass

        log_error(f"No original backup found at: {backup_orig}")
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

    # Check 2: Check if current ASAR has patch marker or native persistence
    current_is_patched = False
    is_native_persisted = False
    app_version = "unknown"
    try:
        curr_header, curr_payload = parse_asar(asar_path)
        app_version = extract_app_version_from_asar(curr_header, curr_payload)
        utils_entry = curr_header["files"]["dist"]["files"]["utils.js"]
        curr_utils_code = curr_payload[
            int(utils_entry["offset"]) : int(utils_entry["offset"]) + utils_entry["size"]
        ].decode("utf-8", "ignore")
        if PATCH_MARKER in curr_utils_code or PAUSE_PATCH_MARKER in curr_utils_code:
            current_is_patched = True
        if is_native_window_persistence_supported(curr_header, curr_utils_code):
            is_native_persisted = True
    except Exception:
        pass

    if is_native_persisted and not current_is_patched:
        log_success(f"Antigravity v{app_version} already features official native window state persistence.")
        log("The application is in stock factory state with native window persistence active. No restoration needed.")
        remove_patch_info(app_paths)
        return

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
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program's version number and exit.",
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
    parser.add_argument(
        "--add-pause",
        action="store_true",
        help="Inject a Pause/Play button next to Queue message / Cancel to pause and resume running prompts while preserving queued messages.",
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
    elif args.shortcut:
        log_warn("The --shortcut option is only applicable on Linux desktop environments.")

    if args.shortcut:
        return

    if args.status:
        check_status(app_paths)
    elif args.restore:
        restore_backup(app_paths, force_kill=args.kill, force=args.force)
    elif args.update:
        apply_pending_update(app_paths, force_kill=args.kill, add_pause=args.add_pause)
    else:
        apply_patch(app_paths, force_kill=args.kill, add_pause=args.add_pause)


if __name__ == "__main__":
    main()
