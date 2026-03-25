import ast
import re

with open("studio/api.py") as f:
    source = f.read()

tree = ast.parse(source)

names_to_remove = {
    # Pipeline
    "PipelineRequest", "LockedIntentRequest", "run_pipeline", "run_pipeline_direct",
    "NStrokeRequest", "run_n_stroke", "run_n_stroke_async", "n_stroke_benchmark", "mcp_tool_manifest",
    "BranchSpecRequest", "BranchRequest", "run_branches", "list_branches",
    # Sandbox
    "SandboxSpawnRequest", "RoadmapItemRequest", "spawn_sandbox", "list_sandboxes", "get_sandbox",
    "get_roadmap", "add_roadmap_item", "run_roadmap_sandboxes", "roadmap_similar", "promote_roadmap_item",
    "_VALID_BRANCH_TYPES"  # also remove this global
}

lines = source.splitlines()

# We also want to delete line representing `_VALID_BRANCH_TYPES = {...}`
valid_branch_idx = -1
for i, line in enumerate(lines):
    if line.startswith("_VALID_BRANCH_TYPES ="):
        valid_branch_idx = i
        break

to_remove = []
if valid_branch_idx >= 0:
    to_remove.append((valid_branch_idx + 1, valid_branch_idx + 1))

for node in tree.body:
    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        if node.name in names_to_remove:
            start_line = node.lineno
            if getattr(node, "decorator_list", []):
                start_line = min(d.lineno for d in node.decorator_list)
            end_line = node.end_lineno
            
            # walk backwards to capture any attached comments if we want, but let's just stick to exact AST range
            to_remove.append((start_line, end_line))

# remove lines backwards to not mess up offsets
for start, end in sorted(to_remove, reverse=True):
    # also try to remove the preceding blank lines or comment headers if we can do it simply
    # but exact AST deletion is safer first.
    del lines[start-1:end]

new_source = "\n".join(lines) + "\n"

# Remove the section headers manually
new_source = re.sub(r"\n# ── Two-Stroke Pipeline endpoint ──+\n", "", new_source)
new_source = re.sub(r"\n# ── N-Stroke pipeline endpoints ──+\n", "", new_source)
new_source = re.sub(r"\n# ── Sandbox endpoints ──+\n", "", new_source)
new_source = re.sub(r"\n# ── Roadmap endpoints ──+\n", "", new_source)
new_source = re.sub(r"\n# ── Branch Executor endpoints ──+\n", "", new_source)
new_source = re.sub(r"\n# ── Roadmap promote endpoint ──+\n", "", new_source)

# Cleanup excessive newlines
new_source = re.sub(r"\n{4,}", "\n\n\n", new_source)

with open("studio/api.py", "w") as f:
    f.write(new_source)

print(f"Removed {len(to_remove)} AST nodes.")
