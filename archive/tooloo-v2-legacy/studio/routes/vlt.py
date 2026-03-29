"""
studio/routes/vlt.py — Vector Layout Tree spatial engine endpoints.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from engine.vlt_schema import VectorTree, VLTAuditReport, demo_vlt

router = APIRouter(tags=["vlt"])

_broadcast_fn = lambda _: None  # noqa: E731

def init(*, broadcast_fn):
    global _broadcast_fn
    _broadcast_fn = broadcast_fn

@router.get("/v2/vlt/demo")
async def vlt_demo() -> dict[str, Any]:
    tree = demo_vlt()
    audit: VLTAuditReport = tree.full_audit()
    _broadcast_fn({"type": "vlt_rendered", "tree_id": tree.tree_id,
                "verdict": audit.verdict, "violations": audit.total_violations})
    return {
        "tree":  tree.model_dump(),
        "audit": audit.model_dump(),
    }

@router.post("/v2/vlt/audit")
async def vlt_audit(req: dict[str, Any]) -> dict[str, Any]:
    if "tree" not in req and "tree_id" not in req:
        raise HTTPException(status_code=422, detail="Missing required field: 'tree'")
    try:
        tree = VectorTree.model_validate(req.get("tree", req))
    except Exception as exc:
        return {"error": f"Invalid VLT payload: {exc}"}
    audit: VLTAuditReport = tree.full_audit()
    _broadcast_fn({"type": "vlt_audit_complete", "tree_id": tree.tree_id,
                "verdict": audit.verdict, "violations": audit.total_violations})
    return audit.model_dump()

@router.post("/v2/vlt/render")
async def vlt_render(req: dict[str, Any]) -> dict[str, Any]:
    try:
        tree = VectorTree.model_validate(req)
    except Exception as exc:
        return {"error": f"Invalid VLT payload: {exc}"}
    audit: VLTAuditReport = tree.full_audit()
    _broadcast_fn({
        "type":       "vlt_push",
        "tree":        tree.model_dump(),
        "audit":       audit.model_dump(),
        "verdict":     audit.verdict,
        "violations":  audit.total_violations,
    })
    return {
        "tree_id":    tree.tree_id,
        "audit":      audit.model_dump(),
        "broadcast":  True,
    }

class VLTPatchRequest(BaseModel):
    tree_id: str = ""
    patches: list[dict[str, Any]]
    transition_ms: int = Field(400, ge=0, le=5000)

@router.post("/v2/vlt/patch")
async def vlt_patch(req: VLTPatchRequest) -> dict[str, Any]:
    validated_patches = []
    for p in req.patches:
        node_id = p.get("node_id", "")
        if not node_id or not isinstance(node_id, str):
            continue
        if "material" in p:
            from engine.vlt_schema import MaterialProps
            try:
                MaterialProps.model_validate(p["material"])
            except Exception:
                p.pop("material")
        validated_patches.append(p)

    _broadcast_fn({
        "type":          "vlt_patch",
        "tree_id":       req.tree_id,
        "patches":       validated_patches,
        "transition_ms": req.transition_ms,
    })
    return {
        "tree_id":         req.tree_id,
        "patches_applied": len(validated_patches),
        "broadcast":       True,
    }
