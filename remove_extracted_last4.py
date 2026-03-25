import ast
import re

with open("studio/api.py") as f:
    source = f.read()

tree = ast.parse(source)

names_to_remove = {
    # Knowledge
    "knowledge_health", "knowledge_dashboard", "get_knowledge_bank", "get_bank_signals", 
    "KnowledgeQueryRequest", "query_knowledge", "KnowledgeIngestRequest", "ingest_knowledge", 
    "run_full_sota_ingestion", "get_intent_signals",
    # VLT
    "vlt_demo", "vlt_audit", "vlt_render", "VLTPatchRequest", "vlt_patch",
    # Core
    "ParallelValidateRequest", "parallel_validate", "alerts_list", "alerts_pending", "alerts_confirm", 
    "alerts_dismiss", "alerts_publish", "stance_get", "StanceOverrideRequest", "stance_set", "stance_detect", "distill_hot_memory",
    # Studio
    "_new_session", "serve_studio", "studio_styles", "ws_studio"
}

lines = source.splitlines()

# Delete specific global assignments for Studio
globals_to_remove = ["_image_gen_engine", "_creative_director", "_prototype_gen_engine", "_studio_sessions"]
to_remove = []

for i, line in enumerate(lines):
    if any(line.startswith(f"{g} =") or line.startswith(f"{g}:") for g in globals_to_remove):
        to_remove.append((i+1, i+1))

for node in tree.body:
    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        if node.name in names_to_remove:
            start_line = node.lineno
            if getattr(node, "decorator_list", []):
                start_line = min(d.lineno for d in node.decorator_list)
            end_line = node.end_lineno
            to_remove.append((start_line, end_line))

# remove lines backwards
for start, end in sorted(to_remove, reverse=True):
    del lines[start-1:end]

new_source = "\n".join(lines) + "\n"

# Remove the section headers manually
headers = [
    r"\n# ── Knowledge Banks ──+.*?(\n|$)",
    r"\n# ── VLT \(Vector Layout Tree\) endpoints ──+.*?(\n|$)",
    r"\n# ── Parallel Validation endpoint ──+.*?(\n|$)",
    r"\n# ── NotificationBus endpoints ──+.*?(\n|$)",
    r"\n# ── Cognitive Stance endpoints ──+.*?(\n|$)",
    r"\n# ── AI Creation Studio V2 — Buddy-guided design-to-prototype pipeline ──+.*?(\n|$)",
    r"\nfrom engine\.vlt_schema import VectorTree, VLTAuditReport, demo_vlt  # noqa: E402\n",
    r"\nfrom engine\.image_gen import ImageGenEngine.*?\n",
    r"\nfrom engine\.creative_director import CreativeDirector.*?\n",
    r"\nfrom engine\.prototype_gen import PrototypeGenEngine.*?\n"
]
for header in headers:
    new_source = re.sub(header, "\n", new_source)

new_source = re.sub(r"\n{4,}", "\n\n\n", new_source)

# Add wiring
insertion_str = """from studio.routes import knowledge as _knowledge_routes
from studio.routes import vlt as _vlt_routes
from studio.routes import core as _core_routes
from studio.routes import studio as _studio_routes

_knowledge_routes.init(
    bank_manager=_bank_manager,
    sota_ingestion=_sota_ingestion,
    broadcast_fn=_broadcast,
)
_vlt_routes.init(
    broadcast_fn=_broadcast,
)
_core_routes.init(
    parallel_validation=_parallel_validation,
    notification_bus=_notification_bus,
    stance_engine=_stance_engine,
    broadcast_fn=_broadcast,
)

app.include_router(_knowledge_routes.router)
app.include_router(_vlt_routes.router)
app.include_router(_core_routes.router)
app.include_router(_studio_routes.router)
"""

# Find where to insert it: after app.include_router(_sandbox_routes.router)
final_source = new_source.replace(
    "app.include_router(_sandbox_routes.router)\n", 
    f"app.include_router(_sandbox_routes.router)\n{insertion_str}"
)

with open("studio/api.py", "w") as f:
    f.write(final_source)

print(f"Removed {len(to_remove)} AST nodes for last 4 routes.")
