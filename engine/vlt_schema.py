# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining vlt_schema.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.923179
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

"""
engine/vlt_schema.py — Vector Layout Tree (VLT) Schema

Foundational mathematical schema for TooLoo's spatial UI engine.
Replaces raw HTML/CSS generation with pure numeric constraints.

Architecture:
  VectorTree   — top-level container with viewport math context
  VectorNode   — recursive spatial node (container / text / interactive / image / canvas)
  Dimensions   — width/height as percentage of parent + aspect ratio lock
  Coordinates  — z-index + 3D depth/rotation (z_depth, rotation_x/y/z)
  Constraints  — flex-layout math (direction, alignment, gap/padding in 8px grid units)
  StyleTokens  — design-system token references (no raw hex codes allowed)
  MaterialProps  — physically-based rendering properties (roughness, metalness, glass, emissive)
  LightSource    — scene light definitions (point / directional / ambient)
  SensorBindings — hardware→property routing table (mic FFT, camera face position)

Math Proofs (run by ux_eval node):
  VectorTree.check_collisions()   — AABB bounding-box overlap detection
  VectorTree.check_overflow()     — child dimensions vs. parent container bounds
  VectorTree.check_contrast()     — WCAG 4.5:1 ratio via token-to-luminance mapping
  VectorTree.full_audit()         — run all three proofs, return VLTAuditReport

Security:
  - No eval/exec anywhere in this module.
  - No hex codes allowed in StyleTokens (enforced via validator).
  - All field constraints validated by Pydantic v2.
"""
from __future__ import annotations

import math
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Enums ─────────────────────────────────────────────────────────────────────

class NodeType(str, Enum):
    CONTAINER = "container"
    TEXT = "text"
    INTERACTIVE = "interactive"
    IMAGE = "image"
    CANVAS = "canvas"


class FlexDirection(str, Enum):
    ROW = "row"
    COLUMN = "column"


class JustifyContent(str, Enum):
    FLEX_START = "flex-start"
    FLEX_END = "flex-end"
    CENTER = "center"
    SPACE_BETWEEN = "space-between"
    SPACE_AROUND = "space-around"
    SPACE_EVENLY = "space-evenly"


class AlignItems(str, Enum):
    STRETCH = "stretch"
    FLEX_START = "flex-start"
    FLEX_END = "flex-end"
    CENTER = "center"
    BASELINE = "baseline"


class MaterialType(str, Enum):
    """PBR material archetypes for 3D spatial nodes."""
    GLASS = "glass"
    METAL = "metal"
    BRUSHED_STEEL = "brushed_steel"
    MATTE = "matte"
    EMISSIVE = "emissive"
    HOLOGRAPHIC = "holographic"


class SpatialLayer(int, Enum):
    """Three-layer depth architecture for the spatial UI environment."""
    ENVIRONMENT = 0       # Z: -100 — ambient glow, particles, background lighting
    DATA_LOGIC = 1        # Z: 0    — DAG nodes, signal tubes, data orbs
    INTERACTION_GLASS = 2  # Z: 100  — glassmorphic controls closest to the user


# ── 3D Spatial Sub-models ─────────────────────────────────────────────────────

class MaterialProps(BaseModel):
    """Physically-Based Rendering (PBR) material properties for a spatial node."""
    material_type: MaterialType = Field(
        MaterialType.GLASS,
        description="Archetype driving pre-set PBR defaults (glass, metal, …)")
    roughness: float = Field(
        0.1, ge=0.0, le=1.0,
        description="Surface roughness (0=mirror, 1=fully diffuse)")
    metalness: float = Field(
        0.0, ge=0.0, le=1.0,
        description="Metallic factor (0=dielectric, 1=metal)")
    transmission: float = Field(
        0.85, ge=0.0, le=1.0,
        description="Glass transmission opacity (0=opaque, 1=fully transparent)")
    emissive: float = Field(
        0.0, ge=0.0, le=4.0,
        description="Emissive glow intensity — driven by mic FFT when sensor-bound")
    emissive_token: Optional[str] = Field(
        None,
        description="Design-system token for emissive colour (e.g. 'text-cyan')")


class LightSource(BaseModel):
    """A single light in the 3D scene."""
    light_type: str = Field(
        "point",
        description="'point' | 'directional' | 'ambient'")
    intensity: float = Field(1.0, ge=0.0, le=10.0)
    position: tuple[float, float, float] = Field(
        (0.0, 5.0, 5.0),
        description="World-space (X, Y, Z) position (ignored for ambient)")
    color_token: Optional[str] = Field(
        None,
        description="Design-system token for light colour (default: white)")


class SensorBindings(BaseModel):
    """Routes hardware sensor inputs to node material/transform properties.

    Bindings are evaluated per-frame in the UniformBridge.  Any combination
    can be activated independently — all default to False (passive node).
    """
    microphone_fft_to_emissive: bool = Field(
        False,
        description="Map real-time microphone FFT energy → emissive intensity")
    microphone_volume_to_scale: bool = Field(
        False,
        description="Map microphone volume level → uniform scale pulse")
    camera_x_to_rotation_y: bool = Field(
        False,
        description="Map tracked face X position → node Y rotation (parallax)")
    camera_y_to_rotation_x: bool = Field(
        False,
        description="Map tracked face Y position → node X rotation (parallax)")
    ambient_light_to_roughness: bool = Field(
        False,
        description="Map room brightness (camera luminance) → material roughness")
    custom_bindings: dict[str, str] = Field(
        default_factory=dict,
        description="Free-form sensor→property routing table: {'mic_bass': 'emissive'}")


# ── Sub-models ────────────────────────────────────────────────────────────────

class Dimensions(BaseModel):
    """Width/height expressed as percentages of parent container (0-100)."""
    width_pct:    Optional[int] = Field(None, ge=0, le=100,
                                        description="Width as percentage of parent (0-100)")
    height_pct:   Optional[int] = Field(None, ge=0, le=100,
                                        description="Height as percentage of parent (0-100)")
    aspect_ratio: Optional[float] = Field(None, gt=0,
                                          description="Enforced aspect ratio (e.g. 1.77 for 16:9)")

    def resolved_px(self, parent_w: float, parent_h: float) -> tuple[float, float]:
        """Return (width_px, height_px) given parent pixel dimensions."""
        w = (self.width_pct / 100.0 *
             parent_w) if self.width_pct is not None else parent_w
        if self.aspect_ratio is not None:
            h = w / self.aspect_ratio
        else:
            h = (self.height_pct / 100.0 *
                 parent_h) if self.height_pct is not None else parent_h
        return round(w, 2), round(h, 2)


class Coordinates(BaseModel):
    """Stacking order, optional absolute overrides, and 3D spatial transform."""
    z_index: int = Field(
        0, description="CSS/SVG stacking order.  Mathematical 2D overlap uses this.")
    # Absolute overrides (pixels from top-left of parent).
    # When None, position is derived from Constraints (flex layout).
    abs_x:   Optional[float] = Field(
        None, description="Absolute X override in pixels")
    abs_y:   Optional[float] = Field(
        None, description="Absolute Y override in pixels")
    # ── 3D spatial transform (Three.js scene units) ────────────────────────
    z_depth: float = Field(
        0.0,
        description="Depth along the camera Z axis in scene units.  "
                    "Negative = further away, positive = closer to viewer.")
    rotation_x: float = Field(
        0.0, ge=-180.0, le=180.0,
        description="Initial rotation around X axis (degrees). Sensor-modulated.")
    rotation_y: float = Field(
        0.0, ge=-180.0, le=180.0,
        description="Initial rotation around Y axis (degrees). Sensor-modulated.")
    rotation_z: float = Field(
        0.0, ge=-180.0, le=180.0,
        description="Initial rotation around Z axis (degrees).")
    spatial_layer: SpatialLayer = Field(
        SpatialLayer.DATA_LOGIC,
        description="Which of the 3 depth layers hosts this node.")


class Constraints(BaseModel):
    """Flex-layout math constraints.  All spacing in strict 8-px grid units."""
    flex_direction:  FlexDirection = Field(FlexDirection.COLUMN,
                                           description="'row' or 'column'")
    justify_content: JustifyContent = Field(JustifyContent.FLEX_START,
                                            description="Main axis alignment")
    align_items:     AlignItems = Field(AlignItems.STRETCH,
                                        description="Cross axis alignment")
    gap_units:       int = Field(0, ge=0, le=128,
                                 description="Gap between children (1 unit = 8 px)")
    padding_units:   int = Field(0, ge=0, le=64,
                                 description="Internal padding (1 unit = 8 px)")

    @property
    def gap_px(self) -> int:
        return self.gap_units * 8

    @property
    def padding_px(self) -> int:
        return self.padding_units * 8


# ── Design-system token catalogue ─────────────────────────────────────────────
# Maps token names → (R, G, B) for WCAG contrast math.
# No hex codes ever appear in VectorNode payloads — only token names.

_TOKEN_LUMINANCE: dict[str, tuple[int, int, int]] = {
    # Backgrounds
    "surface-primary":   (13,  13,  18),   # --bg  #0D0D12
    "surface-alt":       (22,  33,  62),   # --surface-alt #16213E
    "surface-card":      (31,  31,  56),   # --surface-card #1f1f38
    "surface-inverse":   (224, 224, 224),  # near-white
    # Text
    "text-body":         (224, 224, 224),  # --text #E0E0E0
    "text-muted":        (122, 122, 154),  # --muted #7a7a9a
    "text-heading-1":    (255, 255, 255),  # pure white
    "text-heading-2":    (240, 240, 255),
    "text-accent":       (245, 166,  35),  # --accent #F5A623
    "text-danger":       (255,  71,  87),  # --danger #FF4757
    "text-success":      (46,  213, 115),  # --success #2ED573
    "text-cyan":         (0,   229, 255),  # --cyan #00E5FF
    "text-purple":       (179, 136, 255),  # --purple-deep #B388FF
    "text-primary":      (108,  99, 255),  # --primary #6C63FF
    # Interaction states
    "hover-glow":        (108,  99, 255),
    "active-press":      (85,   78, 200),
    "focus-ring":        (0,   229, 255),
    "disabled":          (60,   60,  80),
}


def _relative_luminance(r: int, g: int, b: int) -> float:
    """WCAG 2.1 relative luminance (0..1)."""
    def _channel(c: int) -> float:
        s = c / 255.0
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def _contrast_ratio(tok_a: str, tok_b: str) -> float:
    """Return WCAG contrast ratio between two design-system tokens."""
    rgb_a = _TOKEN_LUMINANCE.get(tok_a)
    rgb_b = _TOKEN_LUMINANCE.get(tok_b)
    if rgb_a is None or rgb_b is None:
        return -1.0  # unknown token → signal as unknown
    L1 = _relative_luminance(*rgb_a)
    L2 = _relative_luminance(*rgb_b)
    lighter, darker = (L1, L2) if L1 > L2 else (L2, L1)
    return round((lighter + 0.05) / (darker + 0.05), 2)


class StyleTokens(BaseModel):
    """Pure design-system token references.  Hex codes are forbidden."""
    bg_token:          Optional[str] = Field(None,
                                             description="e.g. 'surface-primary', 'surface-card'")
    text_token:        Optional[str] = Field(None,
                                             description="e.g. 'text-body', 'text-heading-1'")
    interaction_token: Optional[str] = Field(None,
                                             description="e.g. 'hover-glow', 'active-press'")

    @field_validator("bg_token", "text_token", "interaction_token", mode="before")
    @classmethod
    def _no_hex(cls, v: Any) -> Any:
        if isinstance(v, str) and v.startswith("#"):
            raise ValueError(
                f"Raw hex codes are forbidden in StyleTokens. "
                f"Use a design-system token name instead of '{v}'."
            )
        return v

    def contrast_ratio(self) -> float:
        """WCAG contrast ratio between text_token and bg_token (-1 if unknown)."""
        if self.text_token and self.bg_token:
            return _contrast_ratio(self.text_token, self.bg_token)
        return -1.0

    def wcag_aa_pass(self) -> bool:
        """Return True if contrast ratio meets WCAG AA (≥4.5:1 for normal text)."""
        ratio = self.contrast_ratio()
        return ratio >= 4.5


# ── Core VectorNode ───────────────────────────────────────────────────────────

class VectorNode(BaseModel):
    """A single spatial node in the Vector Layout Tree."""
    node_id:      str = Field(...,
                              description="Unique deterministic ID (e.g. 'nav-container')")
    type:         NodeType
    dimensions:   Dimensions = Field(default_factory=Dimensions)
    coordinates:  Coordinates = Field(default_factory=Coordinates)
    constraints:  Constraints = Field(default_factory=Constraints)
    style_tokens: StyleTokens = Field(default_factory=StyleTokens)
    content:      Optional[str] = Field(None,
                                        description="Raw text (TEXT node) or URI (IMAGE node)")
    # ── 3D Spatial properties ─────────────────────────────────────────────────
    material: MaterialProps = Field(
        default_factory=MaterialProps,
        description="PBR material: roughness, metalness, transmission, emissive glow")
    sensor_bindings: SensorBindings = Field(
        default_factory=SensorBindings,
        description="Hardware→property routing: mic FFT, camera face-position, etc.")
    lights: list[LightSource] = Field(
        default_factory=list,
        description="Point/directional lights owned by this node (applied in scene layer)")
    # Recursive spatial nesting
    children: list["VectorNode"] = Field(default_factory=list)

    # ── Bounding-box math ─────────────────────────────────────────────────────

    def bounding_box(self, parent_w: float = 100.0, parent_h: float = 100.0,
                     origin_x: float = 0.0, origin_y: float = 0.0) -> dict[str, float]:
        """Compute absolute bounding box (AABB) for collision detection.

        Returns: {x1, y1, x2, y2, z}  (pixel units relative to viewport root).
        """
        if self.coordinates.abs_x is not None:
            ox = origin_x + self.coordinates.abs_x
        else:
            ox = origin_x

        if self.coordinates.abs_y is not None:
            oy = origin_y + self.coordinates.abs_y
        else:
            oy = origin_y

        w, h = self.dimensions.resolved_px(parent_w, parent_h)
        return {
            "x1": ox,
            "y1": oy,
            "x2": ox + w,
            "y2": oy + h,
            "z":  self.coordinates.z_index,
        }

    def child_layout_boxes(
        self, parent_w: float = 100.0, parent_h: float = 100.0,
        origin_x: float = 0.0, origin_y: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Compute bounding boxes for all *direct* children using flex layout math."""
        if not self.children:
            return []

        p = self.constraints.padding_px
        gap = self.constraints.gap_px
        inner_w = max(parent_w - 2 * p, 0.0)
        inner_h = max(parent_h - 2 * p, 0.0)
        is_row = self.constraints.flex_direction == FlexDirection.ROW

        boxes: list[dict[str, Any]] = []
        cursor = 0.0  # advances along the main axis

        for child in self.children:
            cw, ch = child.dimensions.resolved_px(inner_w, inner_h)

            if is_row:
                cx = origin_x + p + cursor
                cy = origin_y + p
                cursor += cw + gap
            else:
                cx = origin_x + p
                cy = origin_y + p + cursor
                cursor += ch + gap

            boxes.append({
                "node_id": child.node_id,
                "x1": cx,
                "y1": cy,
                "x2": cx + cw,
                "y2": cy + ch,
                "z":  child.coordinates.z_index,
            })

        return boxes


# Needed for recursive self-reference in Pydantic v2
VectorNode.model_rebuild()


# ── Top-level VectorTree ──────────────────────────────────────────────────────

class VectorTree(BaseModel):
    """Complete spatial layout tree with viewport context for math proofs."""
    tree_id:         str = Field(..., description="Unique tree identifier")
    viewport_width:  int = Field(1920, ge=320, le=7680,
                                 description="Simulated viewport width for math proofs")
    viewport_height: int = Field(1080, ge=200, le=4320,
                                 description="Simulated viewport height for math proofs")
    root_node:       VectorNode

    # ── Collision Detection ───────────────────────────────────────────────────

    def _collect_boxes(
        self, node: VectorNode,
        parent_w: float, parent_h: float,
        origin_x: float = 0.0, origin_y: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Recursively collect bounding boxes for all nodes."""
        box = node.bounding_box(parent_w, parent_h, origin_x, origin_y)
        all_boxes: list[dict[str, Any]] = [{"node_id": node.node_id, **box}]

        if node.children:
            child_boxes = node.child_layout_boxes(
                parent_w, parent_h, origin_x, origin_y)
            for i, child in enumerate(node.children):
                cb = child_boxes[i]
                child_w = cb["x2"] - cb["x1"]
                child_h = cb["y2"] - cb["y1"]
                all_boxes.extend(
                    self._collect_boxes(
                        child, child_w, child_h, cb["x1"], cb["y1"]
                    )
                )
        return all_boxes

    def _aabb_overlap(self, a: dict[str, Any], b: dict[str, Any]) -> bool:
        """True if two AABB boxes overlap (same z-plane only)."""
        if a["z"] != b["z"]:
            return False  # different stacking layers → no visual collision
        return (
            a["x1"] < b["x2"] and a["x2"] > b["x1"]
            and a["y1"] < b["y2"] and a["y2"] > b["y1"]
        )

    def check_collisions(self) -> list[dict[str, str]]:
        """AABB collision detection for SIBLING nodes within each flex container.

        Only siblings (children of the same parent) are compared.  Parent-child
        containment is expected and never flagged as a collision.  Returns list
        of collision pairs: [{node_a, node_b, type}].
        """
        return self._check_sibling_collisions(
            self.root_node,
            float(self.viewport_width),
            float(self.viewport_height),
        )

    def _check_sibling_collisions(
        self, node: VectorNode, parent_w: float, parent_h: float
    ) -> list[dict[str, Any]]:
        """Recursively compare only sibling boxes within each container level."""
        if not node.children:
            return []

        collisions: list[dict[str, Any]] = []
        child_boxes = node.child_layout_boxes(
            parent_w, parent_h, 0.0, 0.0
        )

        # Compare all sibling pairs at this level
        for i in range(len(child_boxes)):
            for j in range(i + 1, len(child_boxes)):
                if self._aabb_overlap(child_boxes[i], child_boxes[j]):
                    collisions.append({
                        "node_a": child_boxes[i]["node_id"],
                        "node_b": child_boxes[j]["node_id"],
                        "type": "aabb_overlap",
                    })

        # Recurse into each child
        for i, child in enumerate(node.children):
            cb = child_boxes[i]
            child_w = cb["x2"] - cb["x1"]
            child_h = cb["y2"] - cb["y1"]
            collisions.extend(self._check_sibling_collisions(
                child, child_w, child_h))

        return collisions

    # ── Overflow Check ────────────────────────────────────────────────────────

    def _collect_overflow(
        self, node: VectorNode,
        parent_w: float, parent_h: float,
    ) -> list[dict[str, Any]]:
        """Return list of overflow violations.

        Detects two categories:
        1. **Cumulative flex overflow** — the total main-axis extent of ALL
           children (dimensions + gaps) exceeds the parent inner bounds.
        2. **Individual child overflow** — a single child’s resolved dimension
           exceeds the parent inner bounds on either axis.

        Child dimensions are resolved relative to the parent’s *inner* bounds
        (after subtracting padding), so a single 100%-wide child never overflows
        by definition.  Overflow arises when multiple children together exceed
        the available space or when gap pushes them past the boundary.
        """
        violations: list[dict[str, Any]] = []
        if not node.children:
            return violations

        p = node.constraints.padding_px
        gap = node.constraints.gap_px
        inner_w = max(parent_w - 2 * p, 0.0)
        inner_h = max(parent_h - 2 * p, 0.0)
        is_row = node.constraints.flex_direction == FlexDirection.ROW

        total_main = 0.0
        for i, child in enumerate(node.children):
            cw, ch = child.dimensions.resolved_px(inner_w, inner_h)
            total_main += (cw if is_row else ch)
            if i > 0:
                total_main += gap

        limit = inner_w if is_row else inner_h
        if total_main > limit + 0.5:
            violations.append({
                "parent":    node.node_id,
                "child":     "__flex_children__",
                "axis":      "width" if is_row else "height",
                "child_px":  round(total_main, 1),
                "parent_inner_px": round(limit, 1),
                "overflow_px": round(total_main - limit, 1),
            })

        # Recurse into children using their flex-computed boxes
        child_boxes = node.child_layout_boxes(parent_w, parent_h, 0.0, 0.0)
        for i, child in enumerate(node.children):
            cb = child_boxes[i]
            child_w = cb["x2"] - cb["x1"]
            child_h = cb["y2"] - cb["y1"]
            violations.extend(self._collect_overflow(child, child_w, child_h))

        return violations

    def check_overflow(self) -> list[dict[str, Any]]:
        """Overflow check: any child whose resolved dimensions exceed parent inner bounds."""
        return self._collect_overflow(
            self.root_node,
            float(self.viewport_width),
            float(self.viewport_height),
        )

    # ── WCAG Contrast Math ────────────────────────────────────────────────────

    def _collect_contrast_failures(self, node: VectorNode) -> list[dict[str, Any]]:
        """Recursively find nodes where text/bg contrast < WCAG 4.5:1."""
        failures: list[dict[str, Any]] = []
        st = node.style_tokens
        if st.text_token and st.bg_token:
            ratio = st.contrast_ratio()
            if 0 < ratio < 4.5:
                failures.append({
                    "node_id":    node.node_id,
                    "text_token": st.text_token,
                    "bg_token":   st.bg_token,
                    "ratio":      ratio,
                    "required":   4.5,
                    "delta":      round(4.5 - ratio, 2),
                })
        for child in node.children:
            failures.extend(self._collect_contrast_failures(child))
        return failures

    def check_contrast(self) -> list[dict[str, Any]]:
        """Return list of WCAG AA contrast failures across all TEXT nodes."""
        return self._collect_contrast_failures(self.root_node)

    # ── Full Audit ────────────────────────────────────────────────────────────

    def full_audit(self) -> "VLTAuditReport":
        """Run all three math proofs and return a structured audit report."""
        collisions = self.check_collisions()
        overflows = self.check_overflow()
        contrast_fails = self.check_contrast()

        total_violations = len(collisions) + \
            len(overflows) + len(contrast_fails)
        verdict = "PASS" if total_violations == 0 else (
            "WARN" if total_violations <= 2 else "FAIL"
        )

        return VLTAuditReport(
            tree_id=self.tree_id,
            verdict=verdict,
            total_violations=total_violations,
            collisions=collisions,
            overflows=overflows,
            contrast_failures=contrast_fails,
            patch_hints=_generate_patch_hints(
                collisions, overflows, contrast_fails),
        )


# ── Audit Report ─────────────────────────────────────────────────────────────

class VLTAuditReport(BaseModel):
    """Structured output of VectorTree.full_audit()."""
    tree_id:           str
    verdict:           str  # "PASS" | "WARN" | "FAIL"
    total_violations:  int
    collisions:        list[dict[str, Any]] = Field(default_factory=list)
    overflows:         list[dict[str, Any]] = Field(default_factory=list)
    contrast_failures: list[dict[str, Any]] = Field(default_factory=list)
    patch_hints:       list[str] = Field(default_factory=list)


def _generate_patch_hints(
    collisions: list[dict[str, Any]],
    overflows:  list[dict[str, Any]],
    contrast_fails: list[dict[str, Any]],
) -> list[str]:
    """Generate actionable patch instructions from audit violations."""
    hints: list[str] = []

    for col in collisions:
        hints.append(
            f"COLLISION: '{col['node_a']}' ↔ '{col['node_b']}' — "
            f"increase gap_units on shared parent by at least 1 (adds 8 px)."
        )

    for ov in overflows:
        hints.append(
            f"OVERFLOW ({ov['axis']}): '{ov['child']}' in '{ov['parent']}' "
            f"exceeds by {ov['overflow_px']} px — "
            f"reduce child {ov['axis']}_pct or increase parent container {ov['axis']}_pct."
        )

    for cf in contrast_fails:
        hints.append(
            f"CONTRAST: '{cf['node_id']}' text_token='{cf['text_token']}' on "
            f"bg_token='{cf['bg_token']}' ratio={cf['ratio']} (need ≥4.5) — "
            f"switch to 'text-heading-1' or darker bg token."
        )

    return hints


# ── Demo VLT factory ──────────────────────────────────────────────────────────

def demo_vlt() -> VectorTree:
    """Return a production-quality demo VLT for the TooLoo Studio dashboard."""
    return VectorTree(
        tree_id="tooloo-studio-demo",
        viewport_width=1920,
        viewport_height=1080,
        root_node=VectorNode(
            node_id="root",
            type=NodeType.CONTAINER,
            dimensions=Dimensions(width_pct=100, height_pct=100),
            constraints=Constraints(
                flex_direction=FlexDirection.ROW,
                gap_units=0,
                padding_units=0,
            ),
            style_tokens=StyleTokens(bg_token="surface-primary"),
            children=[
                # Sidebar panel
                VectorNode(
                    node_id="sidebar",
                    type=NodeType.CONTAINER,
                    dimensions=Dimensions(width_pct=18, height_pct=100),
                    coordinates=Coordinates(z_index=2),
                    constraints=Constraints(
                        flex_direction=FlexDirection.COLUMN,
                        gap_units=1,
                        padding_units=2,
                    ),
                    style_tokens=StyleTokens(bg_token="surface-alt"),
                    children=[
                        VectorNode(
                            node_id="sidebar-logo",
                            type=NodeType.CONTAINER,
                            dimensions=Dimensions(width_pct=100, height_pct=8),
                            style_tokens=StyleTokens(
                                bg_token="surface-alt",
                                text_token="text-accent",
                            ),
                            content="TooLoo V2",
                        ),
                        VectorNode(
                            node_id="nav-chat",
                            type=NodeType.INTERACTIVE,
                            dimensions=Dimensions(width_pct=100, height_pct=6),
                            style_tokens=StyleTokens(
                                bg_token="surface-card",
                                text_token="text-body",
                                interaction_token="hover-glow",
                            ),
                            content="💬 Buddy Chat",
                        ),
                        VectorNode(
                            node_id="nav-vlt",
                            type=NodeType.INTERACTIVE,
                            dimensions=Dimensions(width_pct=100, height_pct=6),
                            style_tokens=StyleTokens(
                                bg_token="surface-card",
                                text_token="text-cyan",
                                interaction_token="hover-glow",
                            ),
                            content="⬡ VLT Spatial Engine",
                        ),
                        VectorNode(
                            node_id="nav-pipeline",
                            type=NodeType.INTERACTIVE,
                            dimensions=Dimensions(width_pct=100, height_pct=6),
                            style_tokens=StyleTokens(
                                bg_token="surface-card",
                                text_token="text-body",
                                interaction_token="hover-glow",
                            ),
                            content="⚡ Pipeline",
                        ),
                    ],
                ),
                # Main content area
                VectorNode(
                    node_id="main-content",
                    type=NodeType.CONTAINER,
                    dimensions=Dimensions(width_pct=82, height_pct=100),
                    coordinates=Coordinates(z_index=1),
                    constraints=Constraints(
                        flex_direction=FlexDirection.COLUMN,
                        gap_units=2,
                        padding_units=3,
                    ),
                    style_tokens=StyleTokens(bg_token="surface-primary"),
                    children=[
                        # Header
                        VectorNode(
                            node_id="header-bar",
                            type=NodeType.CONTAINER,
                            dimensions=Dimensions(width_pct=100, height_pct=8),
                            constraints=Constraints(
                                flex_direction=FlexDirection.ROW,
                                align_items=AlignItems.CENTER,
                                gap_units=2,
                                padding_units=1,
                            ),
                            style_tokens=StyleTokens(
                                bg_token="surface-alt",
                                text_token="text-heading-1",
                            ),
                            content="⬡ Vector Layout Engine — Spatial Canvas",
                        ),
                        # Canvas region
                        VectorNode(
                            node_id="vlt-canvas",
                            type=NodeType.CANVAS,
                            dimensions=Dimensions(
                                width_pct=100, height_pct=60),
                            coordinates=Coordinates(z_index=1),
                            style_tokens=StyleTokens(bg_token="surface-card"),
                        ),
                        # Stats row
                        VectorNode(
                            node_id="stats-row",
                            type=NodeType.CONTAINER,
                            dimensions=Dimensions(
                                width_pct=100, height_pct=20),
                            constraints=Constraints(
                                flex_direction=FlexDirection.ROW,
                                gap_units=2,
                                padding_units=0,
                            ),
                            style_tokens=StyleTokens(
                                bg_token="surface-primary"),
                            children=[
                                VectorNode(
                                    node_id="stat-nodes",
                                    type=NodeType.CONTAINER,
                                    dimensions=Dimensions(
                                        width_pct=33, height_pct=100),
                                    style_tokens=StyleTokens(
                                        bg_token="surface-card",
                                        text_token="text-cyan",
                                    ),
                                    content="Nodes: 0",
                                ),
                                VectorNode(
                                    node_id="stat-violations",
                                    type=NodeType.CONTAINER,
                                    dimensions=Dimensions(
                                        width_pct=33, height_pct=100),
                                    style_tokens=StyleTokens(
                                        bg_token="surface-card",
                                        text_token="text-success",
                                    ),
                                    content="Violations: 0",
                                ),
                                VectorNode(
                                    node_id="stat-depth",
                                    type=NodeType.CONTAINER,
                                    dimensions=Dimensions(
                                        width_pct=33, height_pct=100),
                                    style_tokens=StyleTokens(
                                        bg_token="surface-card",
                                        text_token="text-purple",
                                    ),
                                    content="Max Depth: 0",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
    )
