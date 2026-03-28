# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining design_bank.py
# WHERE: engine/knowledge_banks
# WHEN: 2026-03-28T15:54:38.947570
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

"""
engine/knowledge_banks/design_bank.py — SOTA Design Knowledge Bank.

Covers Gestalt principles through 2026 SOTA design systems, typography,
color science, layout, motion, accessibility, and visual hierarchy.

Foundation: human perceptual psychology → current CSS/component ecosystems.
"""
from __future__ import annotations

from pathlib import Path

from engine.knowledge_banks.base import KnowledgeBank, KnowledgeEntry

_DEFAULT_PATH = (
    Path(__file__).resolve().parents[3] / "psyche_bank" / "design.cog.json"
)


class DesignBank(KnowledgeBank):
    """Curated design knowledge: Gestalt → SOTA 2026 design systems."""

    def __init__(self, path: Path | None = None, bank_root: Path | None = None) -> None:
        if bank_root is not None:
            path = bank_root / "design.cog.json"
        super().__init__(path or _DEFAULT_PATH)

    @property
    def bank_id(self) -> str:
        return "design"

    @property
    def bank_name(self) -> str:
        return "Design Bank — Gestalt to SOTA 2026"

    @property
    def domains(self) -> list[str]:
        return [
            "gestalt",
            "typography",
            "color",
            "layout",
            "motion",
            "design_systems",
            "accessibility",
            "visual_hierarchy",
            "interaction_patterns",
            "ux_research",
        ]

    def _seed(self) -> None:
        entries = [
            # ── Gestalt ────────────────────────────────────────────────────────
            KnowledgeEntry(
                id="design_gestalt_proximity",
                title="Gestalt: Proximity",
                body="Elements placed close together are perceived as a group. Use consistent spacing tokens (8px base grid) to signal grouping without explicit borders.",
                domain="gestalt",
                tags=["gestalt", "spacing", "grouping", "perception"],
                relevance_weight=0.95,
                sota_level="foundational",
            ),
            KnowledgeEntry(
                id="design_gestalt_similarity",
                title="Gestalt: Similarity",
                body="Items sharing color, shape, or size are perceived as related. Apply a consistent component variant system (e.g., shadcn/ui) to reinforce similarity cues.",
                domain="gestalt",
                tags=["gestalt", "similarity",
                      "visual-grouping", "components"],
                relevance_weight=0.94,
                sota_level="foundational",
            ),
            KnowledgeEntry(
                id="design_gestalt_figure_ground",
                title="Gestalt: Figure-Ground",
                body="Users separate foreground subjects from backgrounds. Elevation tokens (shadow scale) and backdrop-filter blur create clear depth planes.",
                domain="gestalt",
                tags=["gestalt", "depth", "elevation", "layering"],
                relevance_weight=0.93,
                sota_level="foundational",
            ),
            KnowledgeEntry(
                id="design_gestalt_closure",
                title="Gestalt: Closure",
                body="The mind completes incomplete shapes. Skeleton screens exploit closure to reduce perceived load time; partial outlines signal interactive affordance.",
                domain="gestalt",
                tags=["gestalt", "closure", "skeleton-screens", "affordance"],
                relevance_weight=0.90,
                sota_level="foundational",
            ),
            KnowledgeEntry(
                id="design_gestalt_continuity",
                title="Gestalt: Continuity",
                body="Eyes follow smooth paths over abrupt changes. Align elements along invisible grid lines; use consistent directionality in scrolling and drawer animations.",
                domain="gestalt",
                tags=["gestalt", "alignment", "grid", "eye-flow"],
                relevance_weight=0.89,
                sota_level="foundational",
            ),
            KnowledgeEntry(
                id="design_gestalt_praegnanz",
                title="Gestalt: Prägnanz (Law of Good Form)",
                body="The mind prefers the simplest interpretation. Remove decorative complexity; every visual element must carry meaning. Ruthless visual editing reduces cognitive load.",
                domain="gestalt",
                tags=["gestalt", "simplicity", "cognitive-load", "minimalism"],
                relevance_weight=0.92,
                sota_level="foundational",
            ),
            # ── Typography ─────────────────────────────────────────────────────
            KnowledgeEntry(
                id="design_typography_fluid_scale",
                title="Fluid Type Scale with clamp()",
                body="Use CSS `clamp(min, preferred, max)` for fluid typography. The utopia.fyi scale generates mathematically harmonious steps (Minor Third to Perfect Fifth). Ship as CSS custom properties.",
                domain="typography",
                tags=["typography", "fluid-type",
                      "CSS", "responsive", "scale"],
                relevance_weight=0.93,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="design_typography_variable_fonts",
                title="Variable Fonts (wght, ital, opsz, wdth axes)",
                body="Variable fonts ship multiple styles in one file, reducing page weight by 70%+. Use `font-variation-settings` for optical sizing at display vs body sizes. Inter, Geist, and Recursive are robust 2026 choices.",
                domain="typography",
                tags=["typography", "variable-fonts",
                      "performance", "optical-sizing"],
                relevance_weight=0.91,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="design_typography_measure",
                title="Optimal Line Measure (45–75 characters)",
                body="Optimal reading line length is 45–75 characters (~65ch). Use `max-inline-size: 65ch` on prose containers. Desktop content wider than 80ch requires multicolumn or increased leading.",
                domain="typography",
                tags=["typography", "readability", "line-length", "prose"],
                relevance_weight=0.90,
                sota_level="foundational",
            ),
            KnowledgeEntry(
                id="design_typography_leading",
                title="Line Height: Role-Aware Leading",
                body="Headings: 1.1–1.2 line-height. Body text: 1.5–1.65. Dense UI labels: 1.0–1.2. Use unitless multipliers in CSS to inherit font size correctly across nested elements.",
                domain="typography",
                tags=["typography", "line-height", "leading", "hierarchy"],
                relevance_weight=0.88,
                sota_level="foundational",
            ),
            # ── Color ──────────────────────────────────────────────────────────
            KnowledgeEntry(
                id="design_color_oklch",
                title="OKLCH: Perceptually Uniform Color Space",
                body="OKLCH (Lightness, Chroma, Hue) produces perceptually uniform color ramps without the hue shifts of HSL. Use `oklch()` in CSS — baseline 2024. Build palette scales with consistent L steps (e.g. 5, 15, 25…95).",
                domain="color",
                tags=["color", "oklch", "CSS", "palette", "perceptual"],
                relevance_weight=0.94,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="design_color_p3_gamut",
                title="Display P3 Wide Gamut Colors",
                body="Use `color(display-p3 r g b)` inside `@media (color-gamut: p3)` for vivid accent colors on modern screens. Provide sRGB fallbacks. P3 gives ~50% more visible red-green range.",
                domain="color",
                tags=["color", "p3", "wide-gamut",
                      "CSS", "progressive-enhancement"],
                relevance_weight=0.88,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="design_color_contrast_apca",
                title="APCA Contrast (WCAG 3.0 candidate)",
                body="APCA (Advanced Perceptual Contrast Algorithm) measures readability better than WCAG 2.x for modern displays. Lc 60+ for body text, Lc 45+ for large UI text. Use Colour Contrast Analyser or polypane.",
                domain="color",
                tags=["color", "contrast", "accessibility", "APCA", "WCAG"],
                relevance_weight=0.91,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="design_color_semantic_tokens",
                title="Semantic Color Tokens: Role-Based Naming",
                body="Name tokens by role, not value: `--color-surface-primary`, `--color-text-interactive-default`. Use Style Dictionary v4 to transform tokens from Figma Variables to CSS/Tailwind/Android/iOS outputs.",
                domain="color",
                tags=["color", "design-tokens",
                      "style-dictionary", "semantic"],
                relevance_weight=0.92,
                sota_level="sota_2026",
            ),
            # ── Layout ─────────────────────────────────────────────────────────
            KnowledgeEntry(
                id="design_layout_container_queries",
                title="CSS Container Queries (size + style)",
                body="Container queries let components respond to their parent's size, not viewport. Use `container-type: inline-size` on wrappers and `@container (min-inline-size: 640px)` in components. Baseline 2024 — replace all JS resize observers.",
                domain="layout",
                tags=["layout", "container-queries",
                      "CSS", "responsive", "components"],
                relevance_weight=0.95,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="design_layout_subgrid",
                title="CSS Subgrid: Aligned Nested Layouts",
                body="`grid-template-columns: subgrid` propagates parent grid tracks into nested elements. Eliminates complex offset calculations for card grids and form layouts. Baseline 2023 — production safe.",
                domain="layout",
                tags=["layout", "CSS-grid", "subgrid", "alignment"],
                relevance_weight=0.91,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="design_layout_8pt_grid",
                title="8-Point Spacing Grid",
                body="All spacing (margin, padding, gap) uses multiples of 8px (4px for micro-adjustments). Produces visual rhythm, maps to standard icon sizes (16, 24, 32, 48), and aligns with design-token systems.",
                domain="layout",
                tags=["layout", "spacing", "grid", "tokens", "rhythm"],
                relevance_weight=0.92,
                sota_level="foundational",
            ),
            # ── Motion ─────────────────────────────────────────────────────────
            KnowledgeEntry(
                id="design_motion_flip",
                title="FLIP Animation Technique",
                body="FLIP (First, Last, Invert, Play) produces 60fps layout transitions. Capture start state, apply end state, invert the transform, then animate to identity. GSAP 3.12 `Flip.from()` handles this automatically.",
                domain="motion",
                tags=["motion", "FLIP", "GSAP", "animation", "performance"],
                relevance_weight=0.90,
                sota_level="current",
            ),
            KnowledgeEntry(
                id="design_motion_reduced_motion",
                title="prefers-reduced-motion: Respect User Preferences",
                body="Wrap all non-essential animations in `@media (prefers-reduced-motion: no-preference)`. GSAP provides `gsap.matchMedia()` for JS-side motion queries. Essential animations (progress, loading) use opacity transitions only.",
                domain="motion",
                tags=["motion", "accessibility", "reduced-motion", "GSAP"],
                relevance_weight=0.94,
                sota_level="current",
            ),
            KnowledgeEntry(
                id="design_motion_spring_physics",
                title="Spring Physics for Natural Motion",
                body="Spring-based easing (stiffness + damping) feels natural because it mimics real-world physics. GSAP CustomEase, Framer Motion, and CSS `linear()` easing enable spring curves. Avoid pure linear or cubic-bezier for interactive feedback.",
                domain="motion",
                tags=["motion", "spring", "easing", "physics", "GSAP"],
                relevance_weight=0.87,
                sota_level="sota_2026",
            ),
            # ── Design Systems ─────────────────────────────────────────────────
            KnowledgeEntry(
                id="design_systems_radix_ui",
                title="Radix UI: Headless Accessible Components",
                body="Radix UI provides ARIA-compliant, unstyled primitives with full keyboard navigation, focus management, and screen-reader support. Pair with Tailwind CSS v4 for styling. Industry-standard in 2026 React applications.",
                domain="design_systems",
                tags=["design-systems", "Radix",
                      "headless", "accessibility", "React"],
                relevance_weight=0.93,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="design_systems_style_dictionary_v4",
                title="Style Dictionary v4: Cross-Platform Token Pipeline",
                body="Style Dictionary v4 (ESM-native, Node 20+) transforms design tokens from a single source to CSS custom properties, Tailwind config, Swift, Kotlin, and JSON. Integrate with Figma Variables API for a designer-developer sync pipeline.",
                domain="design_systems",
                tags=["design-tokens", "style-dictionary",
                      "cross-platform", "Figma"],
                relevance_weight=0.91,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="design_systems_shadcn",
                title="shadcn/ui: Copy-Owned Component Architecture",
                body="shadcn/ui components are copied into the codebase (not installed), giving full ownership and customisation without upstream breakage risk. Built on Radix + Tailwind. The dominant composable component strategy as of 2026.",
                domain="design_systems",
                tags=["design-systems", "shadcn",
                      "Radix", "Tailwind", "ownership"],
                relevance_weight=0.92,
                sota_level="sota_2026",
            ),
            # ── Accessibility ──────────────────────────────────────────────────
            KnowledgeEntry(
                id="design_a11y_wcag_22",
                title="WCAG 2.2 Level AA — 2026 Minimum Bar",
                body="WCAG 2.2 adds: focus appearance (2px+ outline), target size minimum (24×24px), consistent help, and removes obsolete parsing criteria. Level AA is the legal minimum in EU (EN 301 549), US (Section 508), and UK (PSBAR). Use aXe + Lighthouse CI for automated checking.",
                domain="accessibility",
                tags=["accessibility", "WCAG", "a11y", "compliance", "focus"],
                relevance_weight=0.96,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="design_a11y_cognitive",
                title="Cognitive Accessibility: COGA Guidance",
                body="COGA (Cognitive Accessibility) supplemental guidance: use plain language (Flesch-Kincaid grade 8 max), consistent navigation, visible status messages, and error prevention. Critical for AI chat interfaces where ambiguity causes confusion.",
                domain="accessibility",
                tags=["accessibility", "COGA",
                      "cognitive", "plain-language", "UX"],
                relevance_weight=0.92,
                sota_level="sota_2026",
            ),
            # ── Visual Hierarchy ───────────────────────────────────────────────
            KnowledgeEntry(
                id="design_hierarchy_f_pattern",
                title="F-Pattern Reading for Scanned Content",
                body="Users scan content in an F-shape: two horizontal top passes then a vertical scan. Place critical info in first two lines and left-aligned start of subsequent lines. Use for dashboards, feeds, and lists.",
                domain="visual_hierarchy",
                tags=["hierarchy", "F-pattern",
                      "scanning", "layout", "content"],
                relevance_weight=0.89,
                sota_level="foundational",
            ),
            KnowledgeEntry(
                id="design_hierarchy_whitespace",
                title="Whitespace as an Active Design Element",
                body="Generous whitespace (negative space) reduces cognitive load, signals premium quality, and improves comprehension by 20%+. Don't fill available space — let components breathe. Apple and Linear are reference implementations.",
                domain="visual_hierarchy",
                tags=["hierarchy", "whitespace",
                      "negative-space", "cognitive-load"],
                relevance_weight=0.91,
                sota_level="foundational",
            ),
            # ── Interaction Patterns ───────────────────────────────────────────
            KnowledgeEntry(
                id="design_interaction_progressive_disclosure",
                title="Progressive Disclosure: Reveal on Demand",
                body="Show only the most important 20% of options initially. Reveal advanced options on secondary interaction. Reduces initial cognitive load, improves task completion. Apply to AI chat: show quick actions first, advanced params behind 'More'.",
                domain="interaction_patterns",
                tags=["interaction", "progressive-disclosure",
                      "cognitive-load", "UX"],
                relevance_weight=0.92,
                sota_level="foundational",
            ),
            KnowledgeEntry(
                id="design_interaction_optimistic_ui",
                title="Optimistic UI: Instant Feedback Before Confirmation",
                body="Apply changes to the UI immediately and reconcile after server confirmation. Revert with toast notification on failure. Eliminates loading states for common actions. Use for chat message sending, like/save toggles, form submissions.",
                domain="interaction_patterns",
                tags=["interaction", "optimistic-UI",
                      "feedback", "latency", "UX"],
                relevance_weight=0.88,
                sota_level="current",
            ),
            # ── UX Research ────────────────────────────────────────────────────
            KnowledgeEntry(
                id="design_ux_jobs_to_be_done",
                title="Jobs To Be Done (JTBD) Framework",
                body="Users 'hire' products to make progress in specific situations. JTBD uncovers the functional, social, and emotional dimensions of that job. More predictive of behaviour than persona-based design. Use for Buddy's conversation design.",
                domain="ux_research",
                tags=["UX", "JTBD", "user-research",
                      "motivation", "design-thinking"],
                relevance_weight=0.90,
                sota_level="current",
            ),
            KnowledgeEntry(
                id="design_ux_hick_law",
                title="Hick's Law: Decision Time Grows with Options",
                body="Decision time = K × log2(N+1). Every additional option increases cognitive processing time. Limit nav items to 5–7, action buttons to 1 primary + 1 secondary per context. Critical for AI interface design where option overload is common.",
                domain="ux_research",
                tags=["UX", "Hick-law", "decision-making",
                      "cognitive-load", "nav"],
                relevance_weight=0.93,
                sota_level="foundational",
            ),
        ]
        for e in entries:
            self._store.entries.append(e)
