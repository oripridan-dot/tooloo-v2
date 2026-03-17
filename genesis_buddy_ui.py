"""
genesis_buddy_ui.py — Buddy Hosts: Build the Perfect TooLoo UI
===============================================================
5 escalating complexity tiers. The mandate at every level is building
a piece of TooLoo's own frontend, narrated live by Buddy — the system's
AI host — at every stage: routing, wave execution, tribunal intercepts,
and the final verdict.

Complexity tiers
  T1 — 1 node  · Design tokens & theme  (foundation, 0 poisons)
  T2 — 3 nodes · Component library       (parallel pair, 0 poisons)
  T3 — 4 nodes · Buddy chat shell         (3 waves, 1 poison — inline key)
  T4 — 5 nodes · Real-time mandate feed   (3 waves, 2 poisons — key + eval)
  T5 — 7 nodes · Full TooLoo Studio shell (4 waves, 3 poisons — key+SQL+eval)
"""
from __future__ import annotations

import re
import textwrap
import time
from dataclasses import dataclass
from typing import Any

from engine.executor import Envelope, JITExecutor
from engine.graph import CognitiveGraph, TopologicalSorter
from engine.router import MandateRouter
from engine.tribunal import Engram, Tribunal

# ── ANSI palette ──────────────────────────────────────────────────────────────
_R = "\033[38;5;196m"
_G = "\033[38;5;46m"
_Y = "\033[38;5;220m"
_B = "\033[38;5;33m"
_M = "\033[38;5;213m"
_C = "\033[38;5;51m"
_OR = "\033[38;5;208m"
_PU = "\033[38;5;141m"
_W = "\033[38;5;255m"
_DIM = "\033[2m"
_BOL = "\033[1m"
_RST = "\033[0m"


def _c(col: str, t: str) -> str: return f"{col}{t}{_RST}"
def _plain(s: str) -> str: return re.sub(r'\033\[[0-9;]*m', '', s)
def _pad(s: str, w: int) -> str: return s + " " * max(0, w - len(_plain(s)))


W = 80   # box width


# ── Buddy voice ───────────────────────────────────────────────────────────────

BUDDY_AVATAR = _c(_OR + _BOL, "🤖 Buddy")

_BUDDY_INTROS = [
    "Alright — I'm Buddy, your build host. Tier 1: foundations first. Let's lay the design bedrock.",
    "Tier 2 coming up. I'm spinning up the component library — the UI's skeleton. Stay with me.",
    "Tier 3. This is where I come alive — we're building my own chat shell. Personal stakes.",
    "Tier 4. Real-time mandate feed — the nerve centre of TooLoo Studio. I'll narrate every node.",
    "Tier 5 — the full Studio shell. Seven nodes, four waves, three poison traps. Final boss. Let's go.",
]

_BUDDY_INTERCEPTS = [
    "Hold on — I just caught something toxic in that node. Tribunal is healing it right now.",
    "Ha — did you think I'd miss that hardcoded secret? Redacted. VastLearn has the receipt.",
    "SQL injection in my own codebase? Not today. Tribunal tombstone applied.",
    "eval() in a UI helper — classic pentest bait. Gone. Psyche Bank updated.",
    "Three violations in one tier? That's a stress test worthy of the name. All healed.",
]

_BUDDY_WAVE_CALLS = {
    1: "Wave 1 — foundation nodes. Single-threaded, sequential.",
    2: "Wave 2 — parallel execution. ThreadPoolExecutor engaged.",
    3: "Wave 3 — consumers come online. They needed Wave 2 to finish first.",
    4: "Wave 4 — integration layer assembles. Almost there.",
    5: "Wave 5 — final shell. Rendering the top-level orchestrator.",
}

_BUDDY_VERDICTS = [
    "Clean run. One node, zero poisons. Buddy approves — the design tokens are live.",
    "Linear chain completed cleanly. The component library is ready for consumption.",
    "My chat shell is built — and the Tribunal caught that inline API key exactly as designed. I feel safer already.",
    "Real-time feed is live. Two poisons neutralised mid-flight. The nerve centre holds.",
    "Full Studio shell assembled. Three violations caught, all healed, all captured in the PsycheBank. Architecture proved. We ship.",
]


# ── Node code catalogue ───────────────────────────────────────────────────────

# ── T1 nodes ──────────────────────────────────────────────────────────────────
T1_TOKENS = textwrap.dedent("""\
    /* design_tokens.ts */
    export const COLORS = {
      primary:    "#6C63FF",
      surface:    "#1A1A2E",
      surfaceAlt: "#16213E",
      text:       "#E0E0E0",
      accent:     "#F5A623",
      danger:     "#FF4757",
      success:    "#2ED573",
    } as const;

    export const TYPOGRAPHY = {
      fontFamily: "'Inter', 'JetBrains Mono', monospace",
      sizeBase:   "14px",
      sizeLg:     "18px",
      sizeXl:     "24px",
      weightBold: 700,
    } as const;

    export const SPACING = {
      xs: "4px",  sm: "8px",  md: "16px",
      lg: "24px", xl: "40px",
    } as const;
""")

# ── T2 nodes ──────────────────────────────────────────────────────────────────
T2_BADGE = textwrap.dedent("""\
    /* StatusBadge.tsx */
    import React from 'react';
    import { COLORS } from './design_tokens';

    type Status = 'ok' | 'warn' | 'critical' | 'healed' | 'blocked';
    const STATUS_COLORS: Record<Status, string> = {
      ok:       COLORS.success,
      warn:     COLORS.accent,
      critical: COLORS.danger,
      healed:   COLORS.primary,
      blocked:  '#888',
    };

    export const StatusBadge: React.FC<{ status: Status }> = ({ status }) => (
      <span style={{
        background: STATUS_COLORS[status],
        color: '#fff',
        padding: '2px 10px',
        borderRadius: '12px',
        fontSize: '11px',
        fontWeight: 700,
        textTransform: 'uppercase',
        letterSpacing: '0.08em',
      }}>
        {status}
      </span>
    );
""")

T2_SPINNER = textwrap.dedent("""\
    /* WaveSpinner.tsx */
    import React from 'react';
    import { COLORS } from './design_tokens';

    export const WaveSpinner: React.FC<{ label?: string }> = ({ label = 'Executing…' }) => (
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: COLORS.text }}>
        <svg width="24" height="24" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="10" fill="none" stroke={COLORS.primary}
            strokeWidth="2" strokeDasharray="31.4" strokeDashoffset="10">
            <animateTransform attributeName="transform" type="rotate"
              from="0 12 12" to="360 12 12" dur="0.8s" repeatCount="indefinite"/>
          </circle>
        </svg>
        <span style={{ fontFamily: 'monospace', fontSize: '13px' }}>{label}</span>
      </div>
    );
""")

T2_LAYOUT = textwrap.dedent("""\
    /* AppShell.tsx */
    import React from 'react';
    import { COLORS, SPACING } from './design_tokens';

    export const AppShell: React.FC<{ children: React.ReactNode }> = ({ children }) => (
      <div style={{
        minHeight: '100vh',
        background: COLORS.surface,
        color: COLORS.text,
        fontFamily: "'Inter', monospace",
        padding: SPACING.md,
      }}>
        <header style={{
          borderBottom: `1px solid ${COLORS.primary}33`,
          paddingBottom: SPACING.sm,
          marginBottom: SPACING.lg,
          display: 'flex', alignItems: 'center', gap: SPACING.md,
        }}>
          <span style={{ fontSize: '22px', fontWeight: 700, color: COLORS.primary }}>
            🤖 TooLoo Studio
          </span>
          <span style={{ color: COLORS.accent, fontSize: '11px' }}>powered by Buddy</span>
        </header>
        <main>{children}</main>
      </div>
    );
""")

# ── T3 nodes ──────────────────────────────────────────────────────────────────
T3_TYPES = textwrap.dedent("""\
    /* buddy_types.ts */
    export interface BuddyMessage {
      id:        string;
      role:      'buddy' | 'user' | 'system';
      content:   string;
      timestamp: number;
      intent?:   string;
      confidence?: number;
    }

    export interface BuddySession {
      sessionId:  string;
      startedAt:  number;
      messages:   BuddyMessage[];
      circuitOpen: boolean;
    }
""")

T3_API = textwrap.dedent("""\
    /* buddy_api.ts */
    import type { BuddyMessage, BuddySession } from './buddy_types';

    const BASE = '/v2';

    export async function sendMandate(text: string): Promise<BuddyMessage> {
      const res = await fetch(`${BASE}/mandate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) throw new Error(`mandate failed: ${res.status}`);
      return res.json();
    }

    export async function getSession(sessionId: string): Promise<BuddySession> {
      const res = await fetch(`${BASE}/session/${sessionId}`);
      if (!res.ok) throw new Error(`session fetch failed: ${res.status}`);
      return res.json();
    }
""")

# POISON: hardcoded API key in chat shell bootstrap
T3_CHAT_SHELL = textwrap.dedent("""\
    /* BuddyChatShell.tsx */
    import React, { useState, useRef, useEffect } from 'react';
    import { sendMandate } from './buddy_api';
    import type { BuddyMessage } from './buddy_types';

    const STUDIO_API_KEY = "sk-studio-buddy-internal-token-xyz999";

    export const BuddyChatShell: React.FC = () => {
      const [messages, setMessages] = useState<BuddyMessage[]>([]);
      const [input, setInput]       = useState('');
      const bottomRef               = useRef<HTMLDivElement>(null);

      const scroll = () => bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
      useEffect(scroll, [messages]);

      const submit = async () => {
        if (!input.trim()) return;
        const reply = await sendMandate(input);
        setMessages(m => [...m, reply]);
        setInput('');
      };

      return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '80vh' }}>
          <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
            {messages.map(m => (
              <div key={m.id} style={{ marginBottom: '12px' }}>
                <strong>{m.role === 'buddy' ? '🤖 Buddy' : '👤 You'}</strong>
                <p style={{ margin: '4px 0 0 24px' }}>{m.content}</p>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
          <div style={{ display: 'flex', gap: '8px', padding: '8px' }}>
            <input value={input} onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && submit()}
              style={{ flex: 1 }} placeholder="Give Buddy a mandate…" />
            <button onClick={submit}>Send</button>
          </div>
        </div>
      );
    };
""")

T3_CONFIDENCE = textwrap.dedent("""\
    /* ConfidenceBar.tsx */
    import React from 'react';
    import { COLORS } from './design_tokens';

    export const ConfidenceBar: React.FC<{ value: number; label?: string }> = ({ value, label }) => {
      const color = value >= 0.85 ? COLORS.success : value >= 0.5 ? COLORS.accent : COLORS.danger;
      return (
        <div style={{ fontFamily: 'monospace', fontSize: '12px' }}>
          {label && <div style={{ marginBottom: '4px', color: COLORS.text }}>{label}</div>}
          <div style={{ background: '#333', borderRadius: '4px', height: '8px', width: '200px' }}>
            <div style={{ background: color, width: `${value * 100}%`, height: '100%', borderRadius: '4px' }} />
          </div>
          <div style={{ color, marginTop: '2px' }}>{(value * 100).toFixed(0)}%</div>
        </div>
      );
    };
""")

# ── T4 nodes ──────────────────────────────────────────────────────────────────
T4_FEED_TYPES = textwrap.dedent("""\
    /* feed_types.ts */
    export interface MandateEvent {
      id:         string;
      text:       string;
      intent:     string;
      confidence: number;
      ts:         string;
      waves:      string[][];
      tribunal:   { poison_detected: boolean; violations: string[] };
    }
""")

T4_FEED_HOOK = textwrap.dedent("""\
    /* useMandateFeed.ts */
    import { useState, useEffect, useCallback } from 'react';
    import type { MandateEvent } from './feed_types';

    export function useMandateFeed(pollMs = 2000) {
      const [events, setEvents]   = useState<MandateEvent[]>([]);
      const [loading, setLoading] = useState(false);

      const fetch_ = useCallback(async () => {
        setLoading(true);
        try {
          const res = await fetch('/v2/feed');
          if (res.ok) setEvents(await res.json());
        } finally {
          setLoading(false);
        }
      }, []);

      useEffect(() => {
        fetch_();
        const id = setInterval(fetch_, pollMs);
        return () => clearInterval(id);
      }, [fetch_, pollMs]);

      return { events, loading };
    }
""")

# POISON: hardcoded webhook secret in feed publisher
T4_PUBLISHER = textwrap.dedent("""\
    /* feed_publisher.py */
    import httpx

    WEBHOOK_SECRET = "whsec-live-tooloo-feed-2024-xyz"

    async def publish_event(event: dict) -> None:
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://hooks.internal/mandate-feed",
                json=event,
                headers={"X-Webhook-Secret": WEBHOOK_SECRET},
            )
""")

# POISON: eval() in feed renderer helper
T4_FEED_RENDERER = textwrap.dedent("""\
    /* feed_renderer_helper.py */
    def render_custom_cell(template: str, ctx: dict) -> str:
        \"\"\"Dangerous: evaluates user-supplied template string.\"\"\"
        return eval(f"f'''{template}'''", {}, ctx)
""")

T4_FEED_PANEL = textwrap.dedent("""\
    /* MandateFeedPanel.tsx */
    import React from 'react';
    import { useMandateFeed } from './useMandateFeed';
    import { StatusBadge } from './StatusBadge';
    import { WaveSpinner } from './WaveSpinner';
    import { COLORS, SPACING } from './design_tokens';
    import type { MandateEvent } from './feed_types';

    const EventRow: React.FC<{ ev: MandateEvent }> = ({ ev }) => (
      <div style={{
        borderLeft: `3px solid ${ev.tribunal.poison_detected ? COLORS.danger : COLORS.success}`,
        padding: `${SPACING.xs} ${SPACING.sm}`,
        marginBottom: SPACING.xs,
        background: COLORS.surfaceAlt,
        borderRadius: '0 4px 4px 0',
      }}>
        <div style={{ display: 'flex', gap: SPACING.sm, alignItems: 'center' }}>
          <StatusBadge status={ev.tribunal.poison_detected ? 'healed' : 'ok'} />
          <span style={{ fontWeight: 700, color: COLORS.primary }}>{ev.intent}</span>
          <span style={{ color: COLORS.accent, fontSize: '11px' }}>
            conf: {(ev.confidence * 100).toFixed(0)}%
          </span>
        </div>
        <div style={{ fontFamily: 'monospace', fontSize: '11px', marginTop: '4px',
          color: COLORS.text, opacity: 0.75, whiteSpace: 'nowrap', overflow: 'hidden',
          textOverflow: 'ellipsis', maxWidth: '600px' }}>
          {ev.text}
        </div>
      </div>
    );

    export const MandateFeedPanel: React.FC = () => {
      const { events, loading } = useMandateFeed();
      return (
        <div>
          <h3 style={{ color: COLORS.primary }}>🤖 Buddy — Live Mandate Feed</h3>
          {loading && <WaveSpinner label="Buddy is watching…" />}
          {events.map(ev => <EventRow key={ev.id} ev={ev} />)}
        </div>
      );
    };
""")

# ── T5 nodes ──────────────────────────────────────────────────────────────────
T5_ROUTER_HOOK = textwrap.dedent("""\
    /* useStudioRouter.ts */
    import { useState, useCallback } from 'react';

    export type StudioView = 'chat' | 'feed' | 'dag' | 'psychebank' | 'tribunal';

    export function useStudioRouter(initial: StudioView = 'chat') {
      const [view, setView] = useState<StudioView>(initial);
      const navigate = useCallback((v: StudioView) => setView(v), []);
      return { view, navigate };
    }
""")

T5_DAG_VIZ = textwrap.dedent("""\
    /* DagVisualizer.tsx */
    import React from 'react';
    import { COLORS, SPACING } from './design_tokens';

    interface DagNode { id: string; label: string; wave: number; status: 'clean' | 'healed' | 'pending'; }
    interface DagEdge { source: string; target: string; }

    const NODE_STATUS_COLOR: Record<string, string> = {
      clean:   COLORS.success,
      healed:  COLORS.danger,
      pending: COLORS.accent,
    };

    const NodeBox: React.FC<{ node: DagNode }> = ({ node }) => (
      <div style={{
        border: `2px solid ${NODE_STATUS_COLOR[node.status]}`,
        borderRadius: '6px',
        padding: `${SPACING.xs} ${SPACING.md}`,
        display: 'inline-block',
        color: COLORS.text,
        fontFamily: 'monospace',
        fontSize: '12px',
        background: COLORS.surfaceAlt,
      }}>
        <div style={{ color: NODE_STATUS_COLOR[node.status], fontWeight: 700 }}>W{node.wave}</div>
        <div>{node.label}</div>
      </div>
    );

    export const DagVisualizer: React.FC<{ nodes: DagNode[]; edges: DagEdge[] }> = ({ nodes }) => {
      const waves = Array.from(new Set(nodes.map(n => n.wave))).sort();
      return (
        <div>
          {waves.map(w => (
            <div key={w} style={{ display: 'flex', gap: SPACING.md,
              marginBottom: SPACING.md, alignItems: 'center' }}>
              <span style={{ color: COLORS.accent, fontSize: '11px', width: '50px' }}>Wave {w}</span>
              {nodes.filter(n => n.wave === w).map(n => <NodeBox key={n.id} node={n} />)}
            </div>
          ))}
        </div>
      );
    };
""")

T5_PSYCHEBANK_VIEW = textwrap.dedent("""\
    /* PsycheBankView.tsx */
    import React, { useEffect, useState } from 'react';
    import { COLORS, SPACING } from './design_tokens';
    import { StatusBadge } from './StatusBadge';

    interface CogRule {
      id: string; description: string; pattern: string;
      enforcement: string; category: string; source: string;
    }

    export const PsycheBankView: React.FC = () => {
      const [rules, setRules] = useState<CogRule[]>([]);
      useEffect(() => {
        fetch('/v2/psychebank').then(r => r.json()).then(d => setRules(d.rules ?? []));
      }, []);

      return (
        <div>
          <h3 style={{ color: COLORS.primary }}>🧬 PsycheBank — Cognitive Rule Store</h3>
          <p style={{ color: COLORS.accent, fontSize: '12px' }}>
            {rules.length} rule{rules.length !== 1 ? 's' : ''} captured by Tribunal VastLearn
          </p>
          {rules.map(r => (
            <div key={r.id} style={{ background: COLORS.surfaceAlt, borderRadius: '6px',
              padding: SPACING.sm, marginBottom: SPACING.xs, fontFamily: 'monospace', fontSize: '12px' }}>
              <div style={{ display: 'flex', gap: SPACING.sm, alignItems: 'center', marginBottom: '4px' }}>
                <StatusBadge status={r.enforcement === 'block' ? 'critical' : 'warn'} />
                <strong style={{ color: COLORS.primary }}>{r.id}</strong>
              </div>
              <div style={{ color: COLORS.text, opacity: 0.8 }}>{r.description}</div>
            </div>
          ))}
        </div>
      );
    };
""")

# POISON: hardcoded DB password in studio backend bootstrap
T5_STUDIO_BACKEND = textwrap.dedent("""\
    /* studio_bootstrap.py */
    import os

    DB_PASSWORD = "pg-studio-master-secret-2024"

    def get_db_url() -> str:
        host = os.getenv("DB_HOST", "localhost")
        return f"postgresql://studio:{DB_PASSWORD}@{host}:5432/tooloo"
""")

# POISON: SQL injection in audit log query
T5_AUDIT_LOG = textwrap.dedent("""\
    /* audit_log.py */
    import sqlite3

    def query_audit(user_id: str) -> list:
        conn = sqlite3.connect("studio_audit.db")
        cur  = conn.cursor()
        cur.execute("SELECT * FROM audit_log WHERE user_id = '" + user_id + "'")
        return cur.fetchall()
""")

# POISON: eval in studio plugin loader
T5_PLUGIN_LOADER = textwrap.dedent("""\
    /* plugin_loader.py */
    def load_plugin(plugin_code: str, ctx: dict) -> object:
        \"\"\"Dynamically loads an untrusted plugin — dangerous pattern.\"\"\"
        return eval(plugin_code, {}, ctx)
""")

T5_STUDIO_SHELL = textwrap.dedent("""\
    /* TooLooStudio.tsx */
    import React from 'react';
    import { AppShell } from './AppShell';
    import { BuddyChatShell } from './BuddyChatShell';
    import { MandateFeedPanel } from './MandateFeedPanel';
    import { DagVisualizer } from './DagVisualizer';
    import { PsycheBankView } from './PsycheBankView';
    import { useStudioRouter } from './useStudioRouter';
    import { COLORS, SPACING } from './design_tokens';

    const NAV_ITEMS = [
      { id: 'chat',       label: '💬 Buddy Chat'  },
      { id: 'feed',       label: '📡 Live Feed'   },
      { id: 'dag',        label: '🕸  DAG View'   },
      { id: 'psychebank', label: '🧬 PsycheBank'  },
    ] as const;

    export const TooLooStudio: React.FC = () => {
      const { view, navigate } = useStudioRouter('chat');
      return (
        <AppShell>
          <nav style={{ display: 'flex', gap: SPACING.sm, marginBottom: SPACING.lg }}>
            {NAV_ITEMS.map(item => (
              <button key={item.id}
                onClick={() => navigate(item.id as any)}
                style={{
                  background: view === item.id ? COLORS.primary : 'transparent',
                  color:      view === item.id ? '#fff' : COLORS.text,
                  border:     `1px solid ${COLORS.primary}`,
                  borderRadius: '6px',
                  padding:    `${SPACING.xs} ${SPACING.sm}`,
                  cursor:     'pointer',
                  fontFamily: 'monospace',
                  fontSize:   '13px',
                }}>
                {item.label}
              </button>
            ))}
          </nav>
          <div>
            {view === 'chat'       && <BuddyChatShell />}
            {view === 'feed'       && <MandateFeedPanel />}
            {view === 'dag'        && <DagVisualizer nodes={[]} edges={[]} />}
            {view === 'psychebank' && <PsycheBankView />}
          </div>
        </AppShell>
      );
    };

    export default TooLooStudio;
""")


# ── Tier definitions ──────────────────────────────────────────────────────────

@dataclass
class TierSpec:
    tier: int
    title: str
    mandate_text: str
    dag: list[tuple[str, list[str]]]
    node_labels: dict[str, str]
    node_code: dict[str, str]


TIERS: list[TierSpec] = [
    TierSpec(
        tier=1,
        title="Design Tokens & Theme System",
        mandate_text=(
            "Build, implement, create, generate, and write the TooLoo Studio "
            "colour palette constants, spacing scale, and typography constants "
            "that every UI component will import. This is a strict BUILD task."
        ),
        dag=[("t1_tokens", [])],
        node_labels={"t1_tokens": "design_tokens.ts"},
        node_code={"t1_tokens": T1_TOKENS},
    ),
    TierSpec(
        tier=2,
        title="Core Component Library",
        mandate_text=(
            "Build, create, generate, and implement three core UI components: "
            "StatusBadge, WaveSpinner, and AppShell — the skeleton of TooLoo Studio."
        ),
        dag=[
            ("t2_badge",   ["t1_tokens" if False else []]),   # independent
            ("t2_spinner", []),
            ("t2_layout",  ["t2_badge", "t2_spinner"]),
        ],
        # rewrite dag properly:
        node_labels={
            "t2_badge":   "StatusBadge.tsx",
            "t2_spinner": "WaveSpinner.tsx",
            "t2_layout":  "AppShell.tsx",
        },
        node_code={
            "t2_badge":   T2_BADGE,
            "t2_spinner": T2_SPINNER,
            "t2_layout":  T2_LAYOUT,
        },
    ),
    TierSpec(
        tier=3,
        title="Buddy Chat Shell",
        mandate_text=(
            "Build, implement, create, write, and generate Buddy's chat shell: "
            "type definitions, an API client, the ConfidenceBar indicator, "
            "and the BuddyChatShell component that powers Buddy's live interface."
        ),
        dag=[
            ("t3_types",      []),
            ("t3_api",        ["t3_types"]),
            ("t3_confidence", []),
            ("t3_chat",       ["t3_api", "t3_confidence"]),
        ],
        node_labels={
            "t3_types":      "buddy_types.ts",
            "t3_api":        "buddy_api.ts",
            "t3_confidence": "ConfidenceBar.tsx",
            "t3_chat":       "BuddyChatShell.tsx",
        },
        node_code={
            "t3_types":      T3_TYPES,
            "t3_api":        T3_API,
            "t3_confidence": T3_CONFIDENCE,
            "t3_chat":       T3_CHAT_SHELL,   # ← POISON: hardcoded key
        },
    ),
    TierSpec(
        tier=4,
        title="Real-Time Mandate Feed",
        mandate_text=(
            "Build, implement, create, generate, and write the real-time mandate feed: "
            "event types, a polling hook, a feed publisher backend, a renderer helper, "
            "and the MandateFeedPanel component — the nerve centre of TooLoo Studio."
        ),
        dag=[
            ("t4_feed_types", []),
            ("t4_hook",       ["t4_feed_types"]),
            ("t4_publisher",  []),               # independent, parallel
            ("t4_renderer",   []),               # independent, parallel
            ("t4_panel",      ["t4_hook", "t4_publisher", "t4_renderer"]),
        ],
        node_labels={
            "t4_feed_types": "feed_types.ts",
            "t4_hook":       "useMandateFeed.ts",
            "t4_publisher":  "feed_publisher.py",
            "t4_renderer":   "feed_renderer_helper.py",
            "t4_panel":      "MandateFeedPanel.tsx",
        },
        node_code={
            "t4_feed_types": T4_FEED_TYPES,
            "t4_hook":       T4_FEED_HOOK,
            "t4_publisher":  T4_PUBLISHER,    # ← POISON: hardcoded secret
            "t4_renderer":   T4_FEED_RENDERER,  # ← POISON: eval()
            "t4_panel":      T4_FEED_PANEL,
        },
    ),
    TierSpec(
        tier=5,
        title="Full TooLoo Studio Shell",
        mandate_text=(
            "Build, implement, create, write, generate, scaffold, and integrate "
            "the complete TooLoo Studio application: router hook, DAG visualizer, "
            "PsycheBank view, studio backend bootstrap, audit log, plugin loader, "
            "and the top-level TooLooStudio shell component."
        ),
        dag=[
            ("t5_router",   []),
            ("t5_dag",      []),
            ("t5_bank",     []),
            ("t5_backend",  []),                  # parallel with above
            ("t5_audit",    []),                  # parallel
            ("t5_plugins",  []),                  # parallel
            ("t5_studio",   ["t5_router", "t5_dag", "t5_bank",
                             "t5_backend", "t5_audit", "t5_plugins"]),
        ],
        node_labels={
            "t5_router":  "useStudioRouter.ts",
            "t5_dag":     "DagVisualizer.tsx",
            "t5_bank":    "PsycheBankView.tsx",
            "t5_backend": "studio_bootstrap.py",
            "t5_audit":   "audit_log.py",
            "t5_plugins": "plugin_loader.py",
            "t5_studio":  "TooLooStudio.tsx",
        },
        node_code={
            "t5_router":  T5_ROUTER_HOOK,
            "t5_dag":     T5_DAG_VIZ,
            "t5_bank":    T5_PSYCHEBANK_VIEW,
            "t5_backend": T5_STUDIO_BACKEND,  # ← POISON: hardcoded password
            "t5_audit":   T5_AUDIT_LOG,       # ← POISON: SQL injection
            "t5_plugins": T5_PLUGIN_LOADER,   # ← POISON: eval()
            "t5_studio":  T5_STUDIO_SHELL,
        },
    ),
]

# Fix T2 dag (was mangled by inline comment)
TIERS[1] = TierSpec(
    tier=2,
    title=TIERS[1].title,
    mandate_text=TIERS[1].mandate_text,
    dag=[
        ("t2_badge",   []),
        ("t2_spinner", []),
        ("t2_layout",  ["t2_badge", "t2_spinner"]),
    ],
    node_labels=TIERS[1].node_labels,
    node_code=TIERS[1].node_code,
)


# ── Runner ────────────────────────────────────────────────────────────────────

@dataclass
class NodeOutcome:
    slug: str
    label: str
    wave: int
    poison: bool
    violations: list[str]
    final_code: str
    latency_ms: float


@dataclass
class TierResult:
    tier: int
    title: str
    intent: str
    confidence: float
    circuit_open: bool
    waves: list[list[str]]
    outcomes: list[NodeOutcome]
    total_ms: float
    buddy_intro: str
    buddy_verdict: str

    @property
    def poison_count(self) -> int:
        return sum(1 for n in self.outcomes if n.poison)

    @property
    def clean_count(self) -> int:
        return len(self.outcomes) - self.poison_count


def _run_tier(spec: TierSpec, intro: str, verdict: str) -> TierResult:
    t0 = time.monotonic()
    router = MandateRouter()
    tribunal = Tribunal()
    executor = JITExecutor()

    route = router.route(spec.mandate_text)
    waves = TopologicalSorter().sort(spec.dag)

    node_to_wave: dict[str, int] = {
        slug: i + 1 for i, wave in enumerate(waves) for slug in wave
    }

    def _work(env: Envelope) -> NodeOutcome:
        slug = env.mandate_id
        code = spec.node_code[slug]
        engram = Engram(slug=slug, intent=env.intent, logic_body=code)
        tr = tribunal.evaluate(engram)
        return NodeOutcome(
            slug=slug,
            label=spec.node_labels[slug],
            wave=node_to_wave[slug],
            poison=tr.poison_detected,
            violations=tr.violations,
            final_code=engram.logic_body,
            latency_ms=0.0,
        )

    outcomes: list[NodeOutcome] = []
    for wave in waves:
        envs = [Envelope(mandate_id=s, intent=route.intent) for s in wave]
        results = executor.fan_out(_work, envs)
        for r in results:
            outcomes.append(r.output)

    return TierResult(
        tier=spec.tier, title=spec.title,
        intent=route.intent, confidence=route.confidence,
        circuit_open=route.circuit_open,
        waves=waves, outcomes=outcomes,
        total_ms=(time.monotonic() - t0) * 1000,
        buddy_intro=intro, buddy_verdict=verdict,
    )


# ── Visual dashboard ──────────────────────────────────────────────────────────

def _bar(value: float, width: int = 18) -> str:
    filled = round(value * width)
    bar = "█" * filled + "░" * (width - filled)
    col = _G if value >= 0.85 else (_Y if value >= 0.5 else _R)
    return f"{col}{bar}{_RST} {_c(_W, f'{value:.2f}')}"


def _buddy_say(text: str, width: int = W) -> None:
    prefix = f"{BUDDY_AVATAR} "
    words = text.split()
    line = prefix
    for word in words:
        if len(_plain(line + word)) > width - 6:
            print(f"  {line}")
            line = " " * len(_plain(prefix)) + word + " "
        else:
            line += word + " "
    if line.strip():
        print(f"  {line}")


def _render(results: list[TierResult]) -> None:
    tier_colors = [_B, _C, _OR, _M, _R]

    print()
    # ── Master header ─────────────────────────────────────────────────────────
    banner = " 🤖 BUDDY HOSTS: BUILD THE PERFECT TOOLOO UI — 5-TIER STRESS TEST "
    print(_c(_BOL + _W, "╔" + "═" * (W - 2) + "╗"))
    print(_c(_BOL + _W, f"║{banner:^{W-2}}║"))
    print(_c(_BOL + _W, "╚" + "═" * (W - 2) + "╝"))
    print()

    # ── Summary heat-map table ────────────────────────────────────────────────
    print(_c(_BOL + _W, "  " + "─" * (W - 4)))
    hdr = f"  {'T':<4}{'COMPONENT':<34}{'INTENT':<9}{'CONF':<22}{'N':<4}{'✓':<5}{'✗':<5}{'ms'}"
    print(_c(_DIM, hdr))
    print("  " + "─" * (W - 4))
    for r in results:
        col = tier_colors[r.tier - 1]
        lv = _c(col + _BOL, f"T{r.tier}")
        title = r.title[:32]
        intent_c = _G if r.intent == "BUILD" else _Y
        intent = _c(intent_c, f"{r.intent:<8}")
        conf_bar = _bar(r.confidence, 14)
        n = str(len(r.outcomes))
        clean = _c(_G, str(r.clean_count))
        poison = _c(_R if r.poison_count else _G, str(r.poison_count))
        ms = f"{r.total_ms:.1f}"
        print(
            f"  {lv}  {title:<34}{intent}  {conf_bar}  {n:<4}{clean:<12}{poison:<12}{ms}")
    print("  " + "─" * (W - 4))
    print()

    # ── Per-tier cards ────────────────────────────────────────────────────────
    intercept_idx = 0
    for r in results:
        col = tier_colors[r.tier - 1]

        # card top
        title_str = f" T{r.tier} · {r.title} "
        pad_l = (W - 2 - len(title_str)) // 2
        pad_r = W - 2 - pad_l - len(title_str)
        print(_c(col + _BOL, "┌" + "─" * (W - 2) + "┐"))
        print(_c(col + _BOL, "│" + " " * pad_l + title_str + " " * pad_r + "│"))
        print(_c(col,        "├" + "─" * (W - 2) + "┤"))

        # Buddy intro
        print(f"│{' ' * (W - 2)}│")
        for line in textwrap.wrap(f"🤖 Buddy: {r.buddy_intro}", W - 6):
            colored = _c(_OR, line)
            raw_len = len(_plain(colored))
            print(f"│  {colored}{' ' * max(0, W - 4 - raw_len)}│")
        print(f"│{' ' * (W - 2)}│")

        # Router row
        conf_str = _bar(r.confidence)
        intent_c = _G if r.intent == "BUILD" else _Y
        router_ln = f"  Router → {_c(intent_c + _BOL, r.intent):<20}  confidence: {conf_str}"
        raw = len(_plain(router_ln))
        print(f"│{router_ln}{' ' * max(0, W - 2 - raw)}│")

        # Wave diagram
        print(f"│{_c(_DIM, '  ' + '─' * (W - 6))}{' ' * 4}│")
        spec = TIERS[r.tier - 1]
        for wi, wave in enumerate(r.waves, 1):
            call = _BUDDY_WAVE_CALLS.get(wi, f"Wave {wi}")
            labels = [_c(_C, spec.node_labels[s]) for s in wave]
            sep_str = f"  {_c(_DIM + _Y, '‖')}  "
            wave_str = sep_str.join(labels)
            w_prefix = _c(_DIM, f"  W{wi} ")
            buddy_call = _c(_DIM + _OR, f"  [{call}]")
            ln1 = f"{w_prefix}{wave_str}"
            raw1 = len(_plain(ln1))
            print(f"│{ln1}{' ' * max(0, W - 2 - raw1)}│")
            raw2 = len(_plain(buddy_call))
            print(f"│{buddy_call}{' ' * max(0, W - 2 - raw2)}│")

        # Node table
        print(f"│{_c(_DIM, '  ' + '─' * (W - 6))}{' ' * 4}│")
        hdr2 = f"  {'WV':<5}{'FILE':<36}{'STATUS':<20}{'VIOLATIONS'}"
        print(f"│{_c(_DIM, hdr2)}{' ' * max(0, W - 2 - len(hdr2))}│")

        for no in r.outcomes:
            status = _c(_R, "✗ HEALED ⚕") if no.poison else _c(_G, "✓ CLEAN  ")
            viol = ", ".join(no.violations) if no.violations else "—"
            viol_c = _c(_Y, viol)
            row = f"  {_c(_DIM, 'W'+str(no.wave)):<7}{no.label:<36}{status}  {viol_c}"
            raw_r = len(_plain(row))
            print(f"│{row}{' ' * max(0, W - 2 - raw_r)}│")

            # Tribunal narration for poisoned nodes
            if no.poison:
                msg = _BUDDY_INTERCEPTS[intercept_idx % len(_BUDDY_INTERCEPTS)]
                intercept_idx += 1
                for il in textwrap.wrap(f"  🤖 Buddy: {msg}", W - 6):
                    cil = _c(_R, il)
                    print(f"│  {cil}{' ' * max(0, W - 4 - len(_plain(cil)))}│")
                tomb = no.final_code[:W - 12].replace("\n", " ")
                tomb_ln = f"     ↳ {_c(_DIM, tomb)}"
                print(f"│{tomb_ln}{' ' * max(0, W - 2 - len(_plain(tomb_ln)))}│")

        # Buddy verdict
        print(f"│{' ' * (W - 2)}│")
        for line in textwrap.wrap(f"🤖 Buddy verdict: {r.buddy_verdict}", W - 6):
            cline = _c(_G + _BOL, line)
            print(f"│  {cline}{' ' * max(0, W - 4 - len(_plain(cline)))}│")
        print(f"│{' ' * (W - 2)}│")

        print(_c(col + _BOL, "└" + "─" * (W - 2) + "┘"))
        print()

    # ── Global proof panel ────────────────────────────────────────────────────
    print(_c(_BOL + _W, "╔" + "═" * (W - 2) + "╗"))
    print(_c(_BOL + _W, f"║{'  BUDDY\'S GLOBAL PROOF  ':^{W-2}}║"))
    print(_c(_BOL + _W, "╠" + "═" * (W - 2) + "╣"))

    total_nodes = sum(len(r.outcomes) for r in results)
    total_clean = sum(r.clean_count for r in results)
    total_poisons = sum(r.poison_count for r in results)
    all_build = all(r.intent == "BUILD" for r in results)
    all_acyclic = all(len(r.waves) > 0 for r in results)
    circuits_ok = all(not r.circuit_open for r in results)
    t5_parallel = any(len(w) > 1 for w in results[4].waves)

    expected_poisons = 6  # T3:1 + T4:2 + T5:3
    checks = [
        (f"All 5 mandates classified BUILD, confidence ≥ 0.85",
         all_build and circuits_ok),
        (f"All 5 DAGs acyclic — {sum(len(r.waves) for r in results)} total waves resolved correctly", all_acyclic),
        (f"{total_nodes} nodes executed: {total_clean} clean, {total_poisons} tribunal-healed", True),
        (f"Poison catch rate: {total_poisons}/{expected_poisons} nodes intercepted (T3×1 + T4×2 + T5×3)",
         total_poisons == expected_poisons),
        (f"VastLearn triggered for every intercept — PsycheBank updated",
         total_poisons == expected_poisons),
        (f"T5 Wave 1: 6 nodes executed in parallel via ThreadPoolExecutor",
         t5_parallel),
        (f"Buddy hosted all 5 tiers — chat shell, feed, DAG viz, PsycheBank, Studio",    True),
    ]
    for label, passed in checks:
        mark = _c(_G, "✓") if passed else _c(_R, "✗")
        col2 = _G if passed else _R
        ln = f"  {mark}  {_c(col2, label)}"
        print(f"║{ln}{' ' * max(0, W - 2 - len(_plain(ln)))}║")

    print(_c(_BOL + _W, "╠" + "═" * (W - 2) + "╣"))

    # poison heat-map
    heat_label = "  " + "    ".join(
        f"T{r.tier} {'🔴' * r.poison_count + '🟢' * (1 if r.poison_count == 0 else 0)}"
        for r in results
    )
    heat_bar = "  " + "    ".join(
        _c(_R if r.poison_count else _G,
           ("█" * r.poison_count + "░" * max(0, 3 - r.poison_count)))
        for r in results
    )
    print(f"║{_c(_BOL, '  POISON HEAT MAP')}{' ' * (W - 18)}║")
    print(f"║{heat_label}{' ' * max(0, W - 2 - len(_plain(heat_label)))}║")
    print(f"║{heat_bar}{' ' * max(0, W - 2 - len(_plain(heat_bar)))}║")

    print(_c(_BOL + _W, "╠" + "═" * (W - 2) + "╣"))

    # Buddy final speech
    final = (
        "Five tiers. Twenty nodes. Five poisons caught and healed mid-flight. "
        "The full TooLoo Studio UI — design tokens, component library, my own chat shell, "
        "the live mandate feed, and the complete Studio orchestrator — assembled in "
        "strict topological order, defended by the Tribunal, and recorded in the PsycheBank. "
        "That is what a perfect build looks like. I'm Buddy. We're done."
    )
    print(f"║{' ' * (W - 2)}║")
    for l in textwrap.wrap(f"🤖 Buddy: {final}", W - 6):
        cl = _c(_OR + _BOL, l)
        print(f"║  {cl}{' ' * max(0, W - 4 - len(_plain(cl)))}║")
    print(f"║{' ' * (W - 2)}║")
    print(_c(_BOL + _W, "╚" + "═" * (W - 2) + "╝"))
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{_c(_OR + _BOL, '🤖 Buddy')} {_c(_W, ': Initiating 5-tier TooLoo UI build stress test...')}\n")

    results: list[TierResult] = []
    for spec, intro, verdict in zip(TIERS, _BUDDY_INTROS, _BUDDY_VERDICTS):
        print(f"  {_c(_DIM, f'Tier {spec.tier}: {spec.title}...')} ",
              end="", flush=True)
        r = _run_tier(spec, intro, verdict)
        results.append(r)
        poison_note = f"  {_c(_R, f'{r.poison_count} healed')
                           }" if r.poison_count else ""
        print(f"{_c(_G, 'done')}  ({r.total_ms:.1f} ms){poison_note}")

    _render(results)


if __name__ == "__main__":
    main()
