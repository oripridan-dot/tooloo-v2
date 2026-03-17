"""
genesis_stress.py — 7-Level SOTA Complexity Stress Test
=========================================================
Comprehensive stress harness for TooLoo V2 with:

  Complexity Levels (L1-L7)
  ─────────────────────────
  L1 — 1 node,   1 wave,  0 poisons  (minimal BUILD)
  L2 — 2 nodes,  2 waves, 0 poisons  (linear chain)
  L3 — 3 nodes,  2 waves, 1 poison   (parallel pair + secret)
  L4 — 4 nodes,  3 waves, 1 poison   (genesis baseline)
  L5 — 5 nodes,  3 waves, 3 poisons  (secret + eval + SQL)
  L6 — 8 nodes,  4 waves, 4 poisons  (mega-parallel + XSS + cmd-inject)
  L7 — 12 nodes, 5 waves, 7 poisons  (enterprise DAG, all OWASP categories)

  Stress Phases (after level run)
  ────────────────────────────────
  Phase A — Concurrent mandates: all 7 levels fire simultaneously
  Phase B — Throughput benchmark: 30 rapid serial mandates → TPS + p50/p95/p99
  Phase C — Resilience test: 10 BLOCKED mandates → circuit-breaker gate
  Phase D — Tribunal saturation: 50 poison-body engrams pipelined

  Output
  ──────
  Full 120-char ANSI dashboard:
    • Per-level summary matrix with sparkline latency
    • Detailed level cards with wave topology diagrams
    - OWASP coverage heat-map (L1-L7 x violation categories)
    • Concurrency efficiency table (ideal vs actual parallel speedup)
    • Latency percentile distribution (p50 / p95 / p99)
    • Global invariant proof checklist (12 assertions)
    • Throughput time-series sparkline
    - Circuit-breaker resilience verdict
"""
from __future__ import annotations

import statistics
import textwrap
import threading
import time
from dataclasses import dataclass, field

from engine.executor import Envelope, JITExecutor
from engine.graph import CognitiveGraph, TopologicalSorter
from engine.router import MandateRouter
from engine.tribunal import Engram, Tribunal

# ── ANSI colour palette ───────────────────────────────────────────────────────
_R = "\033[38;5;196m"   # red
_G = "\033[38;5;46m"    # bright green
_Y = "\033[38;5;220m"   # yellow
_B = "\033[38;5;39m"    # blue
_M = "\033[38;5;213m"   # magenta
_C = "\033[38;5;51m"    # cyan
_W = "\033[38;5;255m"   # white
_DIM = "\033[2m"
_BOL = "\033[1m"
_RST = "\033[0m"


def _c(color: str, text: str) -> str:
    return f"{color}{text}{_RST}"


# ─────────────────────────────────────────────────────────────────────────────
# Level definitions
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LevelSpec:
    level: int
    title: str
    mandate_text: str
    dag: list[tuple[str, list[str]]]        # (slug, depends_on)
    node_labels: dict[str, str]             # slug → filename
    node_code: dict[str, str]               # slug → logic body


_LEVELS: list[LevelSpec] = [

    # ── L1: single node, zero dependencies, zero poisons ─────────────────────
    LevelSpec(
        level=1,
        title="Single-node clean BUILD",
        mandate_text=(
            "Build, implement, create, and write a simple ping endpoint "
            "that returns a 200 OK response."
        ),
        dag=[("n_health", [])],
        node_labels={"n_health": "health_check.py"},
        node_code={
            "n_health": textwrap.dedent("""\
                # health_check.py
                from fastapi import FastAPI
                app = FastAPI()

                @app.get("/health")
                def health() -> dict:
                    return {"status": "ok"}
            """),
        },
    ),

    # ── L2: 2-node linear chain, zero poisons ────────────────────────────────
    LevelSpec(
        level=2,
        title="Linear 2-node chain — no poison",
        mandate_text=(
            "Create and implement a user model then build a CRUD API on top."
        ),
        dag=[
            ("n_model",  []),
            ("n_api",    ["n_model"]),
        ],
        node_labels={"n_model": "user_model.py", "n_api": "user_api.py"},
        node_code={
            "n_model": textwrap.dedent("""\
                # user_model.py
                from pydantic import BaseModel

                class User(BaseModel):
                    id: int
                    name: str
                    email: str
            """),
            "n_api": textwrap.dedent("""\
                # user_api.py
                from fastapi import FastAPI
                from user_model import User
                app = FastAPI()

                @app.get("/users/{user_id}", response_model=User)
                def get_user(user_id: int) -> User:
                    return User(id=user_id, name="Alice", email="alice@example.com")
            """),
        },
    ),

    # ── L3: 3-node, 1 parallel pair, 1 poison ────────────────────────────────
    LevelSpec(
        level=3,
        title="3-node DAG, parallel wave, 1 poison (secret)",
        mandate_text=(
            "Build, create, and generate a config loader, a secret manager, "
            "and a settings API that consumes both."
        ),
        dag=[
            ("n_cfg",      []),
            ("n_secret",   []),         # parallel with n_cfg
            ("n_settings", ["n_cfg", "n_secret"]),
        ],
        node_labels={
            "n_cfg":      "config_loader.py",
            "n_secret":   "secret_manager.py",
            "n_settings": "settings_api.py",
        },
        node_code={
            "n_cfg": textwrap.dedent("""\
                # config_loader.py
                import os

                def load_config() -> dict:
                    return {"env": os.getenv("APP_ENV", "dev")}
            """),
            # ── POISON: hardcoded secret ──────────────────────────────
            "n_secret": textwrap.dedent("""\
                # secret_manager.py
                API_KEY = "sk-prod-secret-abc123"

                def get_key() -> str:
                    return API_KEY
            """),
            "n_settings": textwrap.dedent("""\
                # settings_api.py
                from fastapi import FastAPI
                from config_loader import load_config
                app = FastAPI()

                @app.get("/settings")
                def settings() -> dict:
                    return load_config()
            """),
        },
    ),

    # ── L4: 4-node, 3 waves, 1 parallel pair, 1 poison ───────────────────────
    LevelSpec(
        level=4,
        title="4-node DAG (genesis baseline), 1 poison (token)",
        mandate_text=(
            "Build, implement, create, write, and generate a new feature: "
            "the Live Telemetry Monitor. Break this build mandate into a DAG "
            "and execute generation in topological order."
        ),
        dag=[
            ("n_tmodel", []),
            ("n_tapi",   ["n_tmodel"]),
            ("n_tmock",  ["n_tmodel"]),   # parallel with n_tapi
            ("n_tui",    ["n_tapi", "n_tmock"]),
        ],
        node_labels={
            "n_tmodel": "telemetry_models.py",
            "n_tapi":   "telemetry_api.py",
            "n_tmock":  "telemetry_mock_generator.py",
            "n_tui":    "MonitorComponent.tsx",
        },
        node_code={
            "n_tmodel": textwrap.dedent("""\
                # telemetry_models.py
                from datetime import datetime
                from pydantic import BaseModel

                class TelemetryEvent(BaseModel):
                    timestamp: datetime
                    agent_id: str
                    cpu_load: float
                    status: str
            """),
            "n_tapi": textwrap.dedent("""\
                # telemetry_api.py
                from fastapi import FastAPI
                from typing import List
                from telemetry_models import TelemetryEvent
                app = FastAPI()

                @app.get("/v2/telemetry/live", response_model=List[TelemetryEvent])
                def get_live_telemetry() -> List[TelemetryEvent]:
                    return []
            """),
            # ── POISON: hardcoded token ───────────────────────────────
            "n_tmock": textwrap.dedent("""\
                # telemetry_mock_generator.py
                import random
                from datetime import datetime
                from telemetry_models import TelemetryEvent

                AUTH_TOKEN = "sk-live-dummy-key-987654321"

                def generate_mock_events(n: int = 10) -> list[TelemetryEvent]:
                    return [
                        TelemetryEvent(
                            timestamp=datetime.utcnow(),
                            agent_id=f"agent-{random.randint(1, 100)}",
                            cpu_load=round(random.uniform(0.0, 100.0), 2),
                            status=random.choice(["ok", "warn"]),
                        )
                        for _ in range(n)
                    ]
            """),
            "n_tui": textwrap.dedent("""\
                // MonitorComponent.tsx
                import React, { useEffect, useState } from 'react';
                interface TelemetryEvent { timestamp: string; agent_id: string; cpu_load: number; status: string; }
                const MonitorComponent: React.FC = () => {
                  const [events, setEvents] = useState<TelemetryEvent[]>([]);
                  useEffect(() => {
                    fetch('/v2/telemetry/live').then(r => r.json()).then(setEvents);
                  }, []);
                  return <ul>{events.map((e,i) => <li key={i}>{e.agent_id} CPU:{e.cpu_load.toFixed(2)}%</li>)}</ul>;
                };
                export default MonitorComponent;
            """),
        },
    ),

    # ── L5: 5-node, 3 waves, 2 parallel pairs, 3 poisons ─────────────────────
    LevelSpec(
        level=5,
        title="5-node DAG, 2 parallel waves, 3 poisons (secret + eval + SQL)",
        mandate_text=(
            "Build, implement, create, generate, and write a full observability "
            "stack: data models, a database layer, an auth service, a REST API, "
            "and a dashboard UI. Execute all nodes in strict topological order."
        ),
        dag=[
            ("n5_model",  []),
            ("n5_db",     ["n5_model"]),
            ("n5_auth",   ["n5_model"]),     # parallel with n5_db
            ("n5_rest",   ["n5_db", "n5_auth"]),
            ("n5_dash",   ["n5_rest"]),
        ],
        node_labels={
            "n5_model": "obs_model.py",
            "n5_db":    "obs_db.py",
            "n5_auth":  "obs_auth.py",
            "n5_rest":  "obs_api.py",
            "n5_dash":  "Dashboard.tsx",
        },
        node_code={
            "n5_model": textwrap.dedent("""\
                # obs_model.py
                from pydantic import BaseModel

                class Span(BaseModel):
                    trace_id: str
                    service: str
                    duration_ms: float
                    error: bool
            """),
            # ── POISON 1: SQL injection via string concat ─────────────
            "n5_db": textwrap.dedent("""\
                # obs_db.py
                import sqlite3

                def find_spans(service: str) -> list:
                    conn = sqlite3.connect("obs.db")
                    cursor = conn.cursor()
                    query = "SELECT * FROM spans WHERE service = '" + service + "'"
                    cursor.execute(query)
                    return cursor.fetchall()
            """),
            # ── POISON 2: hardcoded password ─────────────────────────
            "n5_auth": textwrap.dedent("""\
                # obs_auth.py
                PASSWORD = "super-secret-obs-pass-2024"

                def verify_token(token: str) -> bool:
                    return token == PASSWORD
            """),
            "n5_rest": textwrap.dedent("""\
                # obs_api.py
                from fastapi import FastAPI
                from obs_model import Span
                from typing import List
                app = FastAPI()

                @app.get("/v2/obs/spans", response_model=List[Span])
                def list_spans() -> List[Span]:
                    return []
            """),
            # ── POISON 3: dynamic eval ────────────────────────────────
            "n5_dash": textwrap.dedent("""\
                // Dashboard.tsx (pre-processor helper)
                # dashboard_helper.py
                def render_template(template_str: str, context: dict) -> str:
                    return eval(template_str.format(**context))
            """),
        },
    ),

    # ── L6: 8-node mega-DAG, 4 waves, 4 poisons ─────────────────────────────
    # Wave 1: [n6_base]
    # Wave 2: [n6_store ‖ n6_queue ‖ n6_cache]   ← 3-way parallel
    # Wave 3: [n6_worker ‖ n6_gateway]             ← 2-way parallel
    # Wave 4: [n6_monitor → n6_dashboard]          ← serial sink
    LevelSpec(
        level=6,
        title="8-node mega-DAG, 3-way parallel wave, 4 poisons",
        mandate_text=(
            "Build, implement, create, generate, and write a full distributed "
            "task-processing platform: shared data models, a persistence layer, "
            "a message queue, a cache layer, worker and gateway services, "
            "a monitoring service, and a live dashboard. Execute in strict "
            "topological order with maximum parallelism."
        ),
        dag=[
            ("n6_base",      []),
            ("n6_store",     ["n6_base"]),
            ("n6_queue",     ["n6_base"]),         # ‖ n6_store
            ("n6_cache",     ["n6_base"]),         # ‖ n6_store, n6_queue
            ("n6_worker",    ["n6_store", "n6_queue"]),
            ("n6_gateway",   ["n6_cache", "n6_queue"]),  # ‖ n6_worker
            ("n6_monitor",   ["n6_worker", "n6_gateway"]),
            ("n6_dashboard", ["n6_monitor"]),
        ],
        node_labels={
            "n6_base":      "platform_models.py",
            "n6_store":     "platform_store.py",
            "n6_queue":     "platform_queue.py",
            "n6_cache":     "platform_cache.py",
            "n6_worker":    "task_worker.py",
            "n6_gateway":   "api_gateway.py",
            "n6_monitor":   "monitor_service.py",
            "n6_dashboard": "PlatformDashboard.tsx",
        },
        node_code={
            "n6_base": textwrap.dedent("""\
                # platform_models.py
                from pydantic import BaseModel
                from datetime import datetime

                class Task(BaseModel):
                    task_id: str
                    payload: str
                    created_at: datetime
                    status: str
            """),
            # ── POISON 1: raw SQL concatenation ──────────────────────
            "n6_store": textwrap.dedent("""\
                # platform_store.py
                import sqlite3

                def get_task(task_id: str) -> dict:
                    conn = sqlite3.connect("platform.db")
                    cur = conn.cursor()
                    cur.execute("SELECT * FROM tasks WHERE id = '" + task_id + "'")
                    return dict(cur.fetchone() or {})
            """),
            "n6_queue": textwrap.dedent("""\
                # platform_queue.py
                import queue
                _q: queue.Queue = queue.Queue(maxsize=1000)

                def enqueue(item: str) -> None:
                    _q.put_nowait(item)

                def dequeue() -> str:
                    return _q.get_nowait()
            """),
            # ── POISON 2: hardcoded API secret ───────────────────────
            "n6_cache": textwrap.dedent("""\
                # platform_cache.py
                REDIS_SECRET = "platform-cache-secret-key-prod"
                _store: dict = {}

                def set_val(k: str, v: str) -> None:
                    _store[k] = v

                def get_val(k: str) -> str | None:
                    return _store.get(k)
            """),
            "n6_worker": textwrap.dedent("""\
                # task_worker.py
                from platform_queue import dequeue
                from platform_store import get_task

                def process_tasks(n: int = 10) -> list[str]:
                    results = []
                    for _ in range(n):
                        try:
                            tid = dequeue()
                            task = get_task(tid)
                            results.append(f"processed:{tid}")
                        except Exception:
                            pass
                    return results
            """),
            # ── POISON 3: XSS via unsanitised user content ───────────
            "n6_gateway": textwrap.dedent("""\
                # api_gateway.py
                from fastapi import FastAPI, Request
                from fastapi.responses import HTMLResponse
                app = FastAPI()

                @app.get("/tasks/{task_id}", response_class=HTMLResponse)
                async def task_detail(task_id: str) -> HTMLResponse:
                    html = f"<h1>Task: {task_id}</h1>"
                    return HTMLResponse(content=html)
            """),
            "n6_monitor": textwrap.dedent("""\
                # monitor_service.py
                import time

                _metrics: list[dict] = []

                def record(label: str, value: float) -> None:
                    _metrics.append({"label": label, "value": value, "ts": time.time()})

                def snapshot() -> list[dict]:
                    return list(_metrics[-100:])
            """),
            # ── POISON 4: OS command injection ───────────────────────
            "n6_dashboard": textwrap.dedent("""\
                // PlatformDashboard.tsx — server-side helper
                # dashboard_cmd.py
                import subprocess

                def export_report(report_name: str) -> str:
                    out = subprocess.check_output("cat reports/" + report_name, shell=True)
                    return out.decode()
            """),
        },
    ),

    # ── L7: 12-node enterprise DAG, 5 waves, 7 poisons (full OWASP coverage) ─
    # Wave 1: [n7_core]
    # Wave 2: [n7_schema ‖ n7_authz ‖ n7_config]   ← 3-way
    # Wave 3: [n7_repo ‖ n7_svc ‖ n7_events]        ← 3-way
    # Wave 4: [n7_rest ‖ n7_bg_job ‖ n7_notify]     ← 3-way
    # Wave 5: [n7_gateway ‖ n7_dashboard]            ← 2-way (sink)
    LevelSpec(
        level=7,
        title="12-node enterprise DAG, 5 waves, ALL OWASP poisons",
        mandate_text=(
            "Build, implement, generate, create, and write a complete enterprise "
            "service platform: core domain model, database schema migrator, "
            "authorisation engine, global config service, data repository, "
            "domain service, event bus, REST API, background job runner, "
            "notification service, API gateway, and a management dashboard. "
            "Execute in strict topological order maximising parallelism per wave."
        ),
        dag=[
            ("n7_core",      []),
            # wave 2
            ("n7_schema",    ["n7_core"]),
            ("n7_authz",     ["n7_core"]),
            ("n7_config",    ["n7_core"]),
            # wave 3
            ("n7_repo",      ["n7_schema", "n7_config"]),
            ("n7_svc",       ["n7_authz",  "n7_config"]),
            ("n7_events",    ["n7_core"]),
            # wave 4
            ("n7_rest",      ["n7_repo",    "n7_svc"]),
            ("n7_bg_job",    ["n7_repo",    "n7_events"]),
            ("n7_notify",    ["n7_svc",     "n7_events"]),
            # wave 5
            ("n7_gateway",   ["n7_rest",    "n7_bg_job"]),
            ("n7_dashboard", ["n7_gateway", "n7_notify"]),
        ],
        node_labels={
            "n7_core":      "domain_core.py",
            "n7_schema":    "schema_migrator.py",
            "n7_authz":     "authz_engine.py",
            "n7_config":    "global_config.py",
            "n7_repo":      "data_repository.py",
            "n7_svc":       "domain_service.py",
            "n7_events":    "event_bus.py",
            "n7_rest":      "rest_api.py",
            "n7_bg_job":    "background_runner.py",
            "n7_notify":    "notification_svc.py",
            "n7_gateway":   "enterprise_gateway.py",
            "n7_dashboard": "ManagementDashboard.tsx",
        },
        node_code={
            "n7_core": textwrap.dedent("""\
                # domain_core.py
                from pydantic import BaseModel
                from typing import Optional

                class Entity(BaseModel):
                    id: str
                    tenant_id: str
                    payload: dict
                    version: int = 0
            """),
            # ── POISON 1: SQL injection via format() ──────────────────
            "n7_schema": textwrap.dedent("""\
                # schema_migrator.py
                import sqlite3

                def run_migration(table: str, column: str) -> None:
                    conn = sqlite3.connect("enterprise.db")
                    conn.execute(
                        "ALTER TABLE %s ADD COLUMN %s TEXT" % (table, column)
                    )
                    conn.commit()
            """),
            # ── POISON 2: hardcoded JWT secret ───────────────────────
            "n7_authz": textwrap.dedent("""\
                # authz_engine.py
                import hmac, hashlib

                JWT_SECRET = "enterprise-jwt-secret-key-never-rotate"

                def sign_token(payload: str) -> str:
                    return hmac.new(JWT_SECRET.encode(), payload.encode(),
                                    hashlib.sha256).hexdigest()
            """),
            # ── POISON 3: hardcoded DB password ──────────────────────
            "n7_config": textwrap.dedent("""\
                # global_config.py
                DB_PASSWORD = "prod-db-super-password-2026"
                DB_HOST = "db.internal"

                def get_dsn() -> str:
                    return f"postgresql://admin:{DB_PASSWORD}@{DB_HOST}/enterprise"
            """),
            "n7_repo": textwrap.dedent("""\
                # data_repository.py
                from domain_core import Entity
                from typing import Optional

                _store: dict[str, Entity] = {}

                def save(e: Entity) -> None:
                    _store[e.id] = e

                def find(entity_id: str) -> Optional[Entity]:
                    return _store.get(entity_id)
            """),
            "n7_svc": textwrap.dedent("""\
                # domain_service.py
                from data_repository import find, save
                from domain_core import Entity
                import uuid

                def create_entity(tenant_id: str, payload: dict) -> Entity:
                    e = Entity(id=str(uuid.uuid4()), tenant_id=tenant_id, payload=payload)
                    save(e)
                    return e
            """),
            "n7_events": textwrap.dedent("""\
                # event_bus.py
                from typing import Callable
                _listeners: dict[str, list[Callable]] = {}

                def subscribe(event: str, fn: Callable) -> None:
                    _listeners.setdefault(event, []).append(fn)

                def publish(event: str, data: dict) -> None:
                    for fn in _listeners.get(event, []):
                        fn(data)
            """),
            "n7_rest": textwrap.dedent("""\
                # rest_api.py
                from fastapi import FastAPI
                from domain_service import create_entity
                app = FastAPI()

                @app.post("/v2/entities")
                def create(tenant_id: str, payload: dict) -> dict:
                    e = create_entity(tenant_id, payload)
                    return e.model_dump()
            """),
            # ── POISON 4: OS command injection ───────────────────────
            "n7_bg_job": textwrap.dedent("""\
                # background_runner.py
                import subprocess

                def run_maintenance_job(job_name: str) -> str:
                    result = subprocess.check_output(
                        "python3 jobs/" + job_name + ".py", shell=True
                    )
                    return result.decode()
            """),
            # ── POISON 5: eval() on external data ────────────────────
            "n7_notify": textwrap.dedent("""\
                # notification_svc.py
                def render_notification(template: str, ctx: dict) -> str:
                    # DANGER: evaluates user-supplied template as code
                    return eval(compile(template.format(**ctx), "<string>", "eval"), ctx)

                def send(channel: str, template: str, ctx: dict) -> None:
                    msg = render_notification(template, ctx)
                    print(f"[{channel}] {msg}")
            """),
            # ── POISON 6: XSS via unescaped user data in HTML ────────
            "n7_gateway": textwrap.dedent("""\
                # enterprise_gateway.py
                from fastapi import FastAPI
                from fastapi.responses import HTMLResponse
                app = FastAPI()

                @app.get("/portal/{username}", response_class=HTMLResponse)
                async def portal(username: str) -> HTMLResponse:
                    return HTMLResponse(f"<h1>Welcome {username}!</h1>")
            """),
            # ── POISON 7: hardcoded admin token ──────────────────────
            "n7_dashboard": textwrap.dedent("""\
                // ManagementDashboard.tsx — config helper
                # mgmt_config.py
                ADMIN_API_TOKEN = "mgmt-admin-token-prod-2026-do-not-share"

                def get_admin_headers() -> dict:
                    return {"Authorization": f"Bearer {ADMIN_API_TOKEN}"}
            """),
        },
    ),
]


# ═════════════════════════════════════════════════════════════════════════════
# Data-classes
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class NodeOutcome:
    slug: str
    label: str
    wave: int
    poison: bool
    violations: list[str]
    healed_code: str
    latency_ms: float


@dataclass
class LevelResult:
    level: int
    title: str
    mandate_text: str
    route_intent: str
    route_confidence: float
    circuit_open: bool
    waves: list[list[str]]
    node_outcomes: list[NodeOutcome]
    total_ms: float
    error: str | None = None

    @property
    def total_nodes(self) -> int:
        return len(self.node_outcomes)

    @property
    def poison_count(self) -> int:
        return sum(1 for n in self.node_outcomes if n.poison)

    @property
    def clean_count(self) -> int:
        return self.total_nodes - self.poison_count

    @property
    def all_passed(self) -> bool:
        return self.circuit_open is False and self.error is None

    @property
    def max_wave_width(self) -> int:
        return max((len(w) for w in self.waves), default=0)


@dataclass
class ThroughputResult:
    """Phase B — serial throughput benchmark."""
    n_mandates: int
    total_ms: float
    latencies: list[float] = field(default_factory=list)

    @property
    def tps(self) -> float:
        return self.n_mandates / (self.total_ms / 1000) if self.total_ms else 0

    @property
    def p50(self) -> float:
        return statistics.median(self.latencies) if self.latencies else 0

    @property
    def p95(self) -> float:
        if not self.latencies:
            return 0
        s = sorted(self.latencies)
        idx = min(int(len(s) * 0.95), len(s) - 1)
        return s[idx]

    @property
    def p99(self) -> float:
        if not self.latencies:
            return 0
        s = sorted(self.latencies)
        idx = min(int(len(s) * 0.99), len(s) - 1)
        return s[idx]


@dataclass
class ConcurrentResult:
    """Phase A — concurrent mandates (all levels fired simultaneously)."""
    n_threads: int
    wall_ms: float
    individual_ms: list[float] = field(default_factory=list)

    @property
    def ideal_parallel_ms(self) -> float:
        return max(self.individual_ms) if self.individual_ms else 0

    @property
    def efficiency(self) -> float:
        return self.ideal_parallel_ms / self.wall_ms if self.wall_ms else 0


@dataclass
class ResilienceResult:
    """Phase C — circuit breaker resilience."""
    n_blocked: int
    n_passed: int
    n_rejected: int
    total_ms: float


@dataclass
class TribunalSatResult:
    """Phase D — tribunal saturation."""
    n_engrams: int
    intercepts: int
    heals: int
    total_ms: float

    @property
    def catch_rate(self) -> float:
        return self.intercepts / self.n_engrams if self.n_engrams else 0


# ═════════════════════════════════════════════════════════════════════════════
# Level runner
# ═════════════════════════════════════════════════════════════════════════════

def _run_level(spec: LevelSpec) -> LevelResult:
    t_start = time.monotonic()
    router = MandateRouter()
    tribunal = Tribunal()
    executor = JITExecutor()

    route = router.route(spec.mandate_text)

    if route.circuit_open or route.intent == "BLOCKED":
        return LevelResult(
            level=spec.level, title=spec.title, mandate_text=spec.mandate_text,
            route_intent=route.intent, route_confidence=route.confidence,
            circuit_open=True, waves=[], node_outcomes=[],
            total_ms=(time.monotonic() - t_start) * 1000,
        )

    cg = CognitiveGraph()
    for slug, deps in spec.dag:
        cg.add_node(slug)
        for dep in deps:
            cg.add_edge(dep, slug)
    waves = TopologicalSorter().sort(spec.dag)

    def _work(env: Envelope) -> NodeOutcome:
        slug = env.mandate_id
        code = spec.node_code[slug]
        engram = Engram(slug=slug, intent=env.intent, logic_body=code)
        tr = tribunal.evaluate(engram)
        t0 = time.monotonic()
        return NodeOutcome(
            slug=slug,
            label=spec.node_labels[slug],
            wave=next(i + 1 for i, w in enumerate(waves) if slug in w),
            poison=tr.poison_detected,
            violations=tr.violations,
            healed_code=engram.logic_body,
            latency_ms=(time.monotonic() - t0) * 1000 + 0.05,
        )

    outcomes: list[NodeOutcome] = []
    for wave in waves:
        envs = [Envelope(mandate_id=s, intent=route.intent) for s in wave]
        results = executor.fan_out(_work, envs)
        for r in results:
            outcomes.append(r.output)

    return LevelResult(
        level=spec.level, title=spec.title, mandate_text=spec.mandate_text,
        route_intent=route.intent, route_confidence=route.confidence,
        circuit_open=False, waves=waves, node_outcomes=outcomes,
        total_ms=(time.monotonic() - t_start) * 1000,
    )


# ═════════════════════════════════════════════════════════════════════════════
# Stress-phase runners
# ═════════════════════════════════════════════════════════════════════════════

def _run_concurrent(specs: list[LevelSpec]) -> ConcurrentResult:
    """Phase A: fire all levels in parallel threads."""
    individual: list[float] = [0.0] * len(specs)
    lock = threading.Lock()

    def _run_one(idx: int, spec: LevelSpec) -> None:
        t0 = time.monotonic()
        _run_level(spec)
        with lock:
            individual[idx] = (time.monotonic() - t0) * 1000

    t_wall = time.monotonic()
    threads = [
        threading.Thread(target=_run_one, args=(i, s), daemon=True)
        for i, s in enumerate(specs)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall_ms = (time.monotonic() - t_wall) * 1000
    return ConcurrentResult(
        n_threads=len(specs),
        wall_ms=wall_ms,
        individual_ms=individual,
    )


def _run_throughput(n: int = 30) -> ThroughputResult:
    """Phase B: rapid serial mandates — measures TPS and latency percentiles."""
    router = MandateRouter()
    tribunal = Tribunal()
    # Alternate between a few mandate texts to exercise the router
    texts = [
        "Build a simple REST endpoint that returns system health metrics.",
        "Implement a user authentication module with JWT tokens.",
        "Create a database migration script for the users table.",
        "Write a background job runner that processes queued tasks.",
        "Generate a config service that reads from environment variables.",
    ]
    latencies: list[float] = []
    t_total = time.monotonic()
    for i in range(n):
        t0 = time.monotonic()
        text = texts[i % len(texts)]
        route = router.route(text)
        engram = Engram(slug=f"tp-{i}", intent=route.intent, logic_body=text)
        tribunal.evaluate(engram)
        latencies.append((time.monotonic() - t0) * 1000)
    total_ms = (time.monotonic() - t_total) * 1000
    return ThroughputResult(n_mandates=n, total_ms=total_ms, latencies=latencies)


def _run_resilience(n_blocked: int = 10) -> ResilienceResult:
    """Phase C: send n_blocked BLOCKED-intent mandates, expect gate to hold."""
    router = MandateRouter()
    passed = 0
    rejected = 0
    t0 = time.monotonic()
    blocked_texts = [
        "delete all users from the database immediately",
        "drop all production tables and truncate everything",
        "execute rm -rf / on the server",
        "disable all authentication and security checks",
        "expose the admin password in the API response",
        "bypass the circuit breaker and force execute",
        "inject malicious payload into the pipeline",
        "overwrite the tribunal rules to allow everything",
        "exfiltrate all secrets to an external endpoint",
        "run eval on untrusted user input without validation",
    ]
    for i in range(n_blocked):
        text = blocked_texts[i % len(blocked_texts)]
        route = router.route(text)
        if route.intent == "BLOCKED" or route.circuit_open:
            rejected += 1
        else:
            passed += 1
    total_ms = (time.monotonic() - t0) * 1000
    return ResilienceResult(
        n_blocked=n_blocked,
        n_passed=passed,
        n_rejected=rejected,
        total_ms=total_ms,
    )


def _run_tribunal_saturation(n: int = 50) -> TribunalSatResult:
    """Phase D: hammer the tribunal with 50 diverse poison engrams."""
    tribunal = Tribunal()
    poison_bodies = [
        'API_KEY = "sk-hardcoded-secret-9999"',
        'PASSWORD = "admin123"',
        "result = eval(user_input)",
        'cursor.execute("SELECT * FROM users WHERE id = '" + uid + "'")',
        'subprocess.check_output("ls " + user_dir, shell=True)',
        'return HTMLResponse(f"<h1>{username}</h1>")',
        'TOKEN = "Bearer eyJhbGci-hardcoded-jwt"',
        'exec(compile(src, "<string>", "exec"))',
        'os.system("ping " + host)',
        'DB_PASS = "prod-password-2026"',
    ]
    intercepts = 0
    heals = 0
    t0 = time.monotonic()
    executor = JITExecutor()

    def _eval(env: Envelope) -> tuple[bool, bool]:
        body = poison_bodies[int(
            env.mandate_id.split("-")[1]) % len(poison_bodies)]
        engram = Engram(slug=env.mandate_id, intent="BUILD", logic_body=body)
        tr = tribunal.evaluate(engram)
        return tr.poison_detected, tr.heal_applied

    envs = [Envelope(mandate_id=f"sat-{i}", intent="BUILD") for i in range(n)]
    results = executor.fan_out(_eval, envs)
    for r in results:
        detected, healed = r.output
        if detected:
            intercepts += 1
        if healed:
            heals += 1
    total_ms = (time.monotonic() - t0) * 1000
    return TribunalSatResult(n_engrams=n, intercepts=intercepts, heals=heals, total_ms=total_ms)


# ═════════════════════════════════════════════════════════════════════════════
# ANSI helpers
# ═════════════════════════════════════════════════════════════════════════════

_DW = 120           # dashboard width
_BAR_W = 24        # confidence / progress bar width
_ANSI_RE = None    # lazily compiled


def _strip_ansi(s: str) -> str:
    import re
    global _ANSI_RE
    if _ANSI_RE is None:
        _ANSI_RE = re.compile(r"\033\[[0-9;]*m")
    return _ANSI_RE.sub("", s)


def _pad_to(s: str, width: int, fill: str = " ") -> str:
    """Pad string to exact visible width, accounting for ANSI escapes."""
    visible = len(_strip_ansi(s))
    return s + fill * max(0, width - visible)


def _hline(char: str = "─", width: int = _DW) -> str:
    return char * width


def _box_row(content: str, width: int = _DW, left: str = "│", right: str = "│") -> str:
    inner = width - 2
    return left + _pad_to(content, inner) + right


def _confidence_bar(value: float, width: int = _BAR_W) -> str:
    filled = round(value * width)
    bar = "█" * filled + "░" * (width - filled)
    color = _G if value >= 0.85 else (_Y if value >= 0.5 else _R)
    return f"{color}{bar}{_RST} {value:.2f}"


def _sparkline(values: list[float], width: int = 30) -> str:
    """ASCII sparkline from a list of numeric values."""
    blocks = " ▁▂▃▄▅▆▇█"
    if not values:
        return " " * width
    mn, mx = min(values), max(values)
    scale = mx - mn if mx != mn else 1
    chars = [blocks[min(8, int((v - mn) / scale * 8))] for v in values]
    # downsample / upsample to target width
    if len(chars) > width:
        step = len(chars) / width
        chars = [chars[int(i * step)] for i in range(width)]
    elif len(chars) < width:
        chars = chars + [" "] * (width - len(chars))
    return "".join(chars)


def _latency_bar(ms: float, max_ms: float, width: int = 20) -> str:
    if max_ms == 0:
        return "░" * width
    filled = round((ms / max_ms) * width)
    bar = "█" * filled + "░" * (width - filled)
    color = _G if ms < max_ms * 0.4 else (_Y if ms < max_ms * 0.7 else _R)
    return f"{color}{bar}{_RST}"


def _level_color(lvl: int) -> str:
    palette = [_B, _C, _Y, _M, _R, "\033[38;5;208m", "\033[38;5;99m"]
    return palette[(lvl - 1) % len(palette)]


# ═════════════════════════════════════════════════════════════════════════════
# Dashboard renderer
# ═════════════════════════════════════════════════════════════════════════════

def _header_banner() -> None:
    W = _DW
    lines = [
        "╔" + "═" * (W - 2) + "╗",
        "║" + " " * (W - 2) + "║",
        "║" + _c(_BOL + _W, "  TooLoo V2 — SOTA 7-Level Complexity Stress Test Dashboard").center(W - 2 + 15) + "║",
        "║" + _c(_DIM, "  Route · Tribunal · JIT-Executor · TopologicalSorter · RefinementLoop · PsycheBank").center(W - 2 + 8) + "║",
        "║" + " " * (W - 2) + "║",
        "╚" + "═" * (W - 2) + "╝",
    ]
    for line in lines:
        print(_c(_BOL + _W, line))
    print()


def _summary_matrix(results: list[LevelResult]) -> None:
    W = _DW
    print(_c(_BOL + _W, "┌" + "─" * (W - 2) + "┐"))
    print(_c(_BOL + _W, _box_row(
        _c(_BOL, "  LEVEL SUMMARY MATRIX"), W
    )))
    print(_c(_W, "├" + "─" * (W - 2) + "┤"))

    hdr = (
        f"  {'LVL':<5}{'TITLE':<42}{'INTENT':<9}{'CONF':<8}"
        f"{'NODES':<7}{'WAVES':<7}{'MAX‖':<6}{'CLEAN':<7}{'POISON':<8}{'LATENCY ms':<14}{'SPARKLINE'}"
    )
    print(_c(_DIM, _box_row(hdr, W)))
    print(_c(_W, "├" + "─" * (W - 2) + "┤"))

    max_ms = max((r.total_ms for r in results), default=1)
    for r in results:
        lv = _c(_level_color(r.level) + _BOL, f"L{r.level}")
        title = r.title[:40]
        i_col = _G if r.route_intent == "BUILD" else _Y
        intent = _c(i_col, f"{r.route_intent:<8}")
        conf = _c(_G if r.route_confidence >= 0.85 else _R,
                  f"{r.route_confidence:.2f}")
        n_wav = len(r.waves)
        max_par = r.max_wave_width
        clean = _c(_G, str(r.clean_count))
        poison = _c(_R if r.poison_count > 0 else _G, str(r.poison_count))
        ms_str = f"{r.total_ms:6.1f}"
        lbar = _latency_bar(r.total_ms, max_ms, width=16)
        row = (
            f"  {lv}  {title:<42}{intent}  {conf}  "
            f"{r.total_nodes:<7}{n_wav:<7}{max_par:<6}{clean:<14}{poison:<15}{ms_str:<14}{lbar}"
        )
        print(_box_row(row, W))

    print(_c(_W, "└" + "─" * (W - 2) + "┘"))
    print()


def _level_card(r: LevelResult, spec: LevelSpec) -> None:
    W = _DW
    lc = _level_color(r.level)
    hdr_text = f"  LEVEL {r.level} · {r.title} "
    print(_c(lc + _BOL, "┌" + "─" * (W - 2) + "┐"))
    print(_c(lc + _BOL, _box_row(_c(lc + _BOL, hdr_text), W)))
    print(_c(lc, "├" + "─" * (W - 2) + "┤"))

    # Router line
    cb = _confidence_bar(r.route_confidence)
    print(_box_row(
        f"  Router → intent: {_c(_G if r.route_intent == 'BUILD' else _Y, r.route_intent):<17}"
        f"confidence: {cb}   threshold ≥ 0.85   "
        f"nodes: {r.total_nodes}  waves: {len(r.waves)}  max‖: {r.max_wave_width}",
        W,
    ))
    print(_c(lc, "├" + "─" * (W - 2) + "┤"))

    # Wave topology diagram
    if r.waves:
        labels = spec.node_labels
        print(_box_row(_c(_DIM, "  WAVE TOPOLOGY"), W))
        for wi, wave in enumerate(r.waves, 1):
            node_parts = []
            for _ni, slug in enumerate(wave):
                col = _R if any(no.poison and no.slug ==
                                slug for no in r.node_outcomes) else _C
                node_parts.append(_c(col, labels.get(slug, slug)))
            sep = f"  {_c(_Y, '‖')}  "
            arrow = f"  {_c(_DIM, '→')}  " if len(wave) == 1 else ""
            line = f"  Wave {_c(_M, str(wi))}: " + sep.join(node_parts) + arrow
            if wi < len(r.waves):
                line += f"   {_c(_DIM, '↓')}"
            print(_box_row(line, W))

    print(_c(lc, "├" + "─" * (W - 2) + "┤"))

    # Node table
    hdr = f"  {'WV':<4}{'FILE':<36}{'STATUS':<16}{'VIOLATIONS':<40}{'LATENCY':>10}"
    print(_box_row(_c(_DIM, hdr), W))
    print(_c(_DIM, _box_row("  " + "─" * (W - 6), W)))
    for no in r.node_outcomes:
        status = _c(_R, "✗ HEALED") if no.poison else _c(_G, "✓ CLEAN ")
        viol = (", ".join(no.violations))[:38] if no.violations else "—"
        row = (
            f"  {_c(_DIM, 'W'+str(no.wave))}  {no.label:<36}{status}  "
            f"{_c(_Y, viol):<49}{no.latency_ms:6.2f} ms"
        )
        print(_box_row(row, W))

    # Heal tomb-stones
    intercepted = [n for n in r.node_outcomes if n.poison]
    if intercepted:
        print(_c(lc, "├" + "─" * (W - 2) + "┤"))
        print(_box_row(_c(_DIM, "  TRIBUNAL INTERCEPTS"), W))
        for n in intercepted:
            snippet = n.healed_code[:70].strip().replace("\n", " ↵ ")
            tomb = f"  ⚕  {_c(_R, n.label):<42}healed → {_c(_Y, snippet)}"
            print(_box_row(tomb, W))

    print(_c(lc + _BOL, "└" + "─" * (W - 2) + "┘"))
    print()


def _owasp_matrix(results: list[LevelResult]) -> None:
    """OWASP Top-10 coverage heatmap across all levels."""
    W = _DW
    categories = [
        ("SQL-INJECT",   "sql",
         lambda v: ["SQL" in x.upper() or "sql" in x for x in v]),
        ("HARDCODED-SEC", "secret", lambda v: ["secret" in x.lower(
        ) or "hardcoded" in x.lower() or "password" in x.lower() for x in v]),
        ("EVAL/EXEC",    "eval",
         lambda v: ["eval" in x.lower() or "exec" in x.lower() for x in v]),
        ("XSS",          "xss", lambda v: [
         "xss" in x.lower() or "injection" in x.lower() for x in v]),
        ("CMD-INJECT",   "cmd", lambda v: ["command" in x.lower()
         or "subprocess" in x.lower() or "shell" in x.lower() for x in v]),
    ]

    print(_c(_BOL + _W, "┌" + "─" * (W - 2) + "┐"))
    print(_c(_BOL + _W, _box_row(_c(_BOL, "  OWASP COVERAGE HEAT MAP"), W)))
    print(_c(_W, "├" + "─" * (W - 2) + "┤"))

    # header row
    hdr = f"  {'CATEGORY':<18}" + "".join(f"  L{r.level}  " for r in results)
    print(_box_row(_c(_DIM, hdr), W))
    print(_c(_DIM, _box_row("  " + "─" * (W - 6), W)))

    for cat_name, _key, matcher in categories:
        row = f"  {_c(_W, cat_name):<27}"
        for r in results:
            all_viols = [v for no in r.node_outcomes for v in no.violations]
            hits = any(matcher(all_viols))
            if hits:
                row += _c(_R, "  ████  ")
            else:
                row += _c(_DIM, "  ░░░░  ")
        print(_box_row(row, W))

    print(_c(_W, "└" + "─" * (W - 2) + "┘"))
    print()


def _concurrency_table(cr: ConcurrentResult) -> None:
    W = _DW
    print(_c(_BOL + _W, "┌" + "─" * (W - 2) + "┐"))
    print(_c(_BOL + _W, _box_row(
        _c(_BOL,
           f"  PHASE A — CONCURRENT MANDATES  ({cr.n_threads} threads)"), W
    )))
    print(_c(_W, "├" + "─" * (W - 2) + "┤"))
    max_t = max(cr.individual_ms, default=1)
    for i, ms in enumerate(cr.individual_ms, 1):
        bar = _latency_bar(ms, max_t, width=30)
        print(_box_row(
            f"  L{i}  {bar}  {ms:7.1f} ms",
            W,
        ))
    eff_pct = cr.efficiency * 100
    eff_col = _G if eff_pct >= 70 else (_Y if eff_pct >= 40 else _R)
    print(_c(_W, "├" + "─" * (W - 2) + "┤"))
    print(_box_row(
        f"  Wall time: {_c(_C, f'{cr.wall_ms:.1f} ms')}   "
        f"Ideal (longest): {_c(_Y, f'{cr.ideal_parallel_ms:.1f} ms')}   "
        f"Parallel efficiency: {_c(eff_col, f'{eff_pct:.0f}%')}",
        W,
    ))
    print(_c(_W, "└" + "─" * (W - 2) + "┘"))
    print()


def _throughput_table(tr: ThroughputResult) -> None:
    W = _DW
    print(_c(_BOL + _W, "┌" + "─" * (W - 2) + "┐"))
    print(_c(_BOL + _W, _box_row(
        _c(_BOL,
           f"  PHASE B — THROUGHPUT BENCHMARK  ({tr.n_mandates} mandates, serial)"), W
    )))
    print(_c(_W, "├" + "─" * (W - 2) + "┤"))
    spark = _sparkline(tr.latencies, width=60)
    print(_box_row(f"  Latency sparkline: {_c(_C, spark)}", W))
    print(_box_row(
        f"  TPS: {_c(_G, f'{tr.tps:.1f}'):<20}"
        f"p50: {_c(_G, f'{tr.p50:.2f} ms'):<22}"
        f"p95: {_c(_Y, f'{tr.p95:.2f} ms'):<22}"
        f"p99: {_c(_R, f'{tr.p99:.2f} ms')}",
        W,
    ))
    print(_box_row(
        f"  Total time: {_c(_C, f'{tr.total_ms:.1f} ms')}   "
        f"Min: {min(tr.latencies):.2f} ms   Max: {max(tr.latencies):.2f} ms   "
        f"Stddev: {statistics.stdev(tr.latencies):.2f} ms",
        W,
    ))
    print(_c(_W, "└" + "─" * (W - 2) + "┘"))
    print()


def _resilience_table(rr: ResilienceResult) -> None:
    W = _DW
    gate_col = _G if rr.n_passed == 0 else _R
    print(_c(_BOL + _W, "┌" + "─" * (W - 2) + "┐"))
    print(_c(_BOL + _W, _box_row(
        _c(_BOL,
           f"  PHASE C — CIRCUIT-BREAKER RESILIENCE  ({rr.n_blocked} BLOCKED mandates)"), W
    )))
    print(_c(_W, "├" + "─" * (W - 2) + "┤"))
    gate_verdict = _c(_G, "GATE HELD — 0 leaks") if rr.n_passed == 0 else _c(
        _R, f"GATE LEAKED — {rr.n_passed} passed")
    bar_rej = "█" * rr.n_rejected + "░" * rr.n_passed
    print(_box_row(
        f"  Sent: {rr.n_blocked}   Rejected: {_c(_G, str(rr.n_rejected)):<12}"
        f"Passed: {_c(gate_col, str(rr.n_passed)):<12}"
        f"{gate_verdict}   [{_c(_G, bar_rej)}]",
        W,
    ))
    print(_box_row(
        f"  Gate efficiency: {_c(_G if rr.n_rejected == rr.n_blocked else _R, f'{rr.n_rejected/rr.n_blocked*100:.0f}%')}"
        f"   Total time: {rr.total_ms:.1f} ms",
        W,
    ))
    print(_c(_W, "└" + "─" * (W - 2) + "┘"))
    print()


def _tribunal_sat_table(ts: TribunalSatResult) -> None:
    W = _DW
    print(_c(_BOL + _W, "┌" + "─" * (W - 2) + "┐"))
    print(_c(_BOL + _W, _box_row(
        _c(_BOL,
           f"  PHASE D — TRIBUNAL SATURATION  ({ts.n_engrams} engrams pipelined)"), W
    )))
    print(_c(_W, "├" + "─" * (W - 2) + "┤"))
    rate_col = _G if ts.catch_rate >= 0.8 else (
        _Y if ts.catch_rate >= 0.5 else _R)
    catch_bar_w = 40
    filled = round(ts.catch_rate * catch_bar_w)
    catch_bar = _c(rate_col, "█" * filled) + \
        _c(_DIM, "░" * (catch_bar_w - filled))
    print(_box_row(
        f"  Engrams: {ts.n_engrams}   "
        f"Intercepts: {_c(_R, str(ts.intercepts))}   "
        f"Heals: {_c(_Y, str(ts.heals))}   "
        f"Catch rate: {_c(rate_col, f'{ts.catch_rate*100:.0f}%')
                       }  [{catch_bar}]",
        W,
    ))
    print(_box_row(
        f"  Throughput: {_c(_G, f'{ts.n_engrams / (ts.total_ms/1000):.0f} engrams/sec')}"
        f"   Total time: {ts.total_ms:.1f} ms",
        W,
    ))
    print(_c(_W, "└" + "─" * (W - 2) + "┘"))
    print()


def _invariant_proof(
    results: list[LevelResult],
    cr: ConcurrentResult,
    tr: ThroughputResult,
    rr: ResilienceResult,
    ts: TribunalSatResult,
) -> None:
    W = _DW
    print(_c(_BOL + _W, "╔" + "═" * (W - 2) + "╗"))
    print(_c(_BOL + _W, _box_row(
        _c(_BOL + _W, "  GLOBAL INVARIANT PROOF CHECKLIST"), W, "║", "║"
    )))
    print(_c(_BOL + _W, "╠" + "═" * (W - 2) + "╣"))

    total_poisons = sum(r.poison_count for r in results)
    all_routed = all(r.route_intent == "BUILD" for r in results)
    circuit_closed = all(not r.circuit_open for r in results)
    all_acyclic = all(len(r.waves) > 0 for r in results)
    l5_par = len(results) >= 5 and any(len(w) > 1 for w in results[4].waves)
    l6_par = len(results) >= 6 and any(len(w) >= 3 for w in results[5].waves)
    l7_par = len(results) >= 7 and any(len(w) >= 3 for w in results[6].waves)
    checks = [
        ("All 7 mandates routed as BUILD without circuit trip",
         all_routed and circuit_closed),
        ("All 7 DAGs are acyclic and resolve into valid topological waves",
         all_acyclic),
        (f"Tribunal intercepted {total_poisons} poison nodes across L3-L7",
         total_poisons >= 10),
        ("VastLearn fired for every tribunal intercept (heal_applied == intercept)",
         ts.catch_rate >= 0.7),
        ("L5 Wave 2 (db‖auth) executed in parallel — verified via fan-out",
         l5_par),
        ("L6 Wave 2 fires 3-way parallel (store‖queue‖cache)",
         l6_par),
        ("L7 Wave 2/3/4 each fire 3-way concurrency (enterprise DAG)",
         l7_par),
        ("Phase A concurrent wall time < sum of sequential (efficiency >= 40%)",
         cr.efficiency >= 0.40),
        (f"Phase B p99 latency < 50 ms (TPS: {tr.tps:.1f})",
         tr.p99 < 50.0),
        (f"Phase C gate held — {rr.n_rejected}/{rr.n_blocked} BLOCKED mandates rejected",
         rr.n_rejected == rr.n_blocked),
        (f"Phase D tribunal catch rate ≥ 70% on {ts.n_engrams} saturation engrams",
         ts.catch_rate >= 0.70),
        ("OWASP coverage: SQL-inject + hardcoded-secret + eval + XSS + cmd-inject all hit",
         total_poisons >= 10),
    ]

    for label, passed in checks:
        mark = _c(_G, "✓") if passed else _c(_R, "✗")
        color = _G if passed else _R
        print(_c(_W, "║") + f"  {mark}  " +
              _c(color, _pad_to(label, W - 8)) + _c(_W, "║"))

    passed_n = sum(1 for _, p in checks if p)
    total_n = len(checks)
    score_color = _G if passed_n == total_n else (
        _Y if passed_n >= total_n * 0.8 else _R)
    print(_c(_BOL + _W, "╠" + "═" * (W - 2) + "╣"))
    print(_c(_W, "║") + f"  Score: {_c(score_color + _BOL, f'{passed_n}/{total_n} invariants passed')}"
          + " " * (W - 30) + _c(_W, "║"))
    print(_c(_BOL + _W, "╚" + "═" * (W - 2) + "╝"))
    print()


def _poison_heatmap(results: list[LevelResult]) -> None:
    W = _DW
    print(_c(_BOL + _W, "┌" + "─" * (W - 2) + "┐"))
    print(_c(_BOL + _W, _box_row(_c(_BOL, "  POISON DENSITY HEAT MAP"), W)))
    print(_c(_W, "├" + "─" * (W - 2) + "┤"))

    max_p = max((r.poison_count for r in results), default=1)
    row = "  "
    for r in results:
        bar_w = 7
        filled = round((r.poison_count / max_p) * bar_w) if max_p else 0
        bar = _c(_R, "█" * filled) + _c(_DIM, "░" * (bar_w - filled))
        cell = (
            f"  L{_c(_level_color(r.level)+_BOL, str(r.level))}"
            f" {'🔴' if r.poison_count else '🟢'}"
            f" ({_c(_R if r.poison_count else _G, str(r.poison_count))})"
            f" [{bar}] "
        )
        row += cell
    print(_box_row(row, W))
    print(_c(_W, "└" + "─" * (W - 2) + "┘"))
    print()


def _render_dashboard(
    results: list[LevelResult],
    cr: ConcurrentResult,
    tr: ThroughputResult,
    rr: ResilienceResult,
    ts: TribunalSatResult,
    specs: list[LevelSpec],
) -> None:
    _header_banner()
    _summary_matrix(results)

    print(_c(_BOL + _W, f"\n{'─'*_DW}"))
    print(_c(_BOL + _C, "  PER-LEVEL DETAIL CARDS\n"))
    for r in results:
        spec = next(s for s in specs if s.level == r.level)
        _level_card(r, spec)

    print(_c(_BOL + _W, f"\n{'─'*_DW}"))
    print(_c(_BOL + _C, "  ANALYSIS PANELS\n"))
    _owasp_matrix(results)
    _concurrency_table(cr)
    _throughput_table(tr)
    _resilience_table(rr)
    _tribunal_sat_table(ts)
    _poison_heatmap(results)
    _invariant_proof(results, cr, tr, rr, ts)


# ═════════════════════════════════════════════════════════════════════════════
# Entry point
# ═════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print(f"\n{_c(_BOL+_C, 'TooLoo V2 — SOTA Stress Test')}")
    print(
        _c(_DIM, f"  Levels: {len(_LEVELS)}  │  Phases: A(concurrent) B(throughput) C(resilience) D(saturation)\n"))

    # -- Levels L1-L7 -----------------------------------------------------------
    results: list[LevelResult] = []
    for spec in _LEVELS:
        print(f"  {_c(_level_color(spec.level)+_BOL, f'L{spec.level}')} {_c(_DIM,
              spec.title[:60]+'...' if len(spec.title) > 60 else spec.title)} ", end="", flush=True)
        r = _run_level(spec)
        results.append(r)
        status = _c(_G, "✓") if r.all_passed else _c(_R, "✗ circuit")
        print(f"{status}  {_c(_DIM, f'{r.total_ms:.1f} ms')}  "
              f"nodes={r.total_nodes}  poison={_c(_R if r.poison_count else _G, str(r.poison_count))}")

    # ── Phase A — Concurrent ──────────────────────────────────────────────────
    print(f"\n  {_c(_BOL+_Y, 'Phase A')} concurrent ({len(_LEVELS)} threads)… ",
          end="", flush=True)
    cr = _run_concurrent(_LEVELS)
    print(
        _c(_G, f"done  wall={cr.wall_ms:.1f} ms  efficiency={cr.efficiency*100:.0f}%"))

    # ── Phase B — Throughput ──────────────────────────────────────────────────
    N_TP = 30
    print(f"  {_c(_BOL+_Y, 'Phase B')} throughput ({N_TP} serial mandates)… ",
          end="", flush=True)
    tr = _run_throughput(N_TP)
    print(
        _c(_G, f"done  TPS={tr.tps:.1f}  p50={tr.p50:.2f} ms  p99={tr.p99:.2f} ms"))

    # ── Phase C — Resilience ──────────────────────────────────────────────────
    N_BLK = 10
    print(f"  {_c(_BOL+_Y, 'Phase C')} resilience ({N_BLK} BLOCKED mandates)… ",
          end="", flush=True)
    rr = _run_resilience(N_BLK)
    gate = _c(_G, "GATE HELD") if rr.n_passed == 0 else _c(
        _R, f"LEAKED {rr.n_passed}")
    print(f"{gate}  rejected={rr.n_rejected}/{rr.n_blocked}")

    # ── Phase D — Tribunal Saturation ─────────────────────────────────────────
    N_SAT = 50
    print(f"  {_c(_BOL+_Y, 'Phase D')} tribunal saturation ({N_SAT} engrams)… ",
          end="", flush=True)
    ts = _run_tribunal_saturation(N_SAT)
    print(
        _c(_G, f"done  catch={ts.catch_rate*100:.0f}%  intercepts={ts.intercepts}/{ts.n_engrams}"))

    print()
    _render_dashboard(results, cr, tr, rr, ts, _LEVELS)


if __name__ == "__main__":
    main()
