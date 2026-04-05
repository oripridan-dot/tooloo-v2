# TooLoo V4: Sovereign Hub

Autonomous intelligence engine built on a **Continuous Mega DAG** orchestrator with multi-provider LLM routing (Gemini, Claude via Vertex, DeepSeek, Llama 4).

## Architecture

```
src/tooloo/
  core/
    mega_dag.py    # ContinuousMegaDAG — async event-loop orchestrator
    llm.py         # ModelRouter — multi-provider LLM dispatch
    buddy.py       # BuddyOperator — contextual story weaver
    chat.py        # MCP Chat Server — human intent injection
  tools/
    core_fs.py     # Sandboxed filesystem tools (zero-trust /tmp/tooloo_sandbox)
  orchestrator.py  # Entry point: ignite the DAG from CLI

tooloo_v4_hub/portal/
  sovereign_api.py  # FastAPI server: WebSocket + REST hub
  index.html        # Main portal UI
  app.js            # Portal frontend logic
  style.css         # Portal styles
  SOVEREIGN_DASHBOARD.html  # Architecture reference + live health fetch
```

## Running

```bash
# Default RULE0 audit mission
uv run python3 src/tooloo/orchestrator.py

# Custom mission goal
uv run python3 src/tooloo/orchestrator.py --goal "your mission here"

# MCP Chat mode (stdio transport)
uv run python3 src/tooloo/orchestrator.py --mcp

# Portal (WebSocket + REST + UI)
uv run python3 tooloo_v4_hub/portal/sovereign_api.py
# Then open http://localhost:8080
```

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | required | Gemini REST API key |
| `GOOGLE_CLOUD_PROJECT` | `too-loo-zi8g7e` | GCP project for Vertex |
| `GOOGLE_CLOUD_LOCATION` | `me-west1` | Vertex region |
| `BUDDY_MODEL` | `gemini-flash-latest` | Model used by BuddyOperator |

## Constitution

See [GEMINI.md](GEMINI.md) — **2 rules**:
- **Rule 0**: Brutal Honesty (10 verbatim Claude Code enforcement clauses)
- **Rule 1**: Additive Development (8 principles)
