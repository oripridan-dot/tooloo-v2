import logging
import os
import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

from src.tooloo.core.mega_dag import ContinuousMegaDAG, DagNode, NodeType
from src.tooloo.core.buddy import BuddyOperator
from src.tooloo.tools.core_fs import DEFAULT_TOOLS

logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Tooloo.MCPChat")

# Module-level DAG reference set by run_mcp_chat_server
global_dag: ContinuousMegaDAG | None = None
# Buddy instance kept alive so answer_question uses the same model config
_buddy: BuddyOperator | None = None

app = Server("tooloo-sovereign-chat")


@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """Exposes the full Sovereign Hub capability surface to the MCP client."""
    return [
        types.Tool(
            name="read_ongoing_mandate",
            description=(
                "Returns the current Contextual Story, active Mandate, DAG iteration count, "
                "JIT cycle count, and a recent narrative snippet from the Sovereign Hub. "
                "Call this first to understand what the system is doing before submitting intents."
            ),
            inputSchema={"type": "object", "properties": {}, "strict": True},
        ),
        types.Tool(
            name="get_dag_status",
            description=(
                "Returns low-level DAG health metrics: queue depth, active iteration count, "
                "elapsed runtime, state keys, and registered operator/tool names. "
                "Use to diagnose whether the DAG is stalled, healthy, or overloaded."
            ),
            inputSchema={"type": "object", "properties": {}, "strict": True},
        ),
        types.Tool(
            name="submit_intent",
            description=(
                "Submits a human intent/goal into the Sovereign Mega DAG. "
                "Routed through SOTA_JIT enrichment before planning — "
                "grounds the intent in domain knowledge before autonomous execution begins. "
                "Returns immediately; execution happens asynchronously in the DAG."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "The mission goal to submit for autonomous execution"
                    }
                },
                "required": ["goal"],
                "strict": True,
            },
        ),
        types.Tool(
            name="inject_state",
            description=(
                "Injects or overwrites key-value pairs directly into the DAG's global state. "
                "Use to pass runtime configuration, override jit_cycles, set flags, etc. "
                "Keys are merged (not replaced) into context.state."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "updates": {
                        "type": "object",
                        "description": "Key-value pairs to merge into context.state"
                    }
                },
                "required": ["updates"],
                "strict": True,
            },
        ),
        types.Tool(
            name="query_buddy",
            description=(
                "Ask Buddy a direct question about the system's current state, narrative, "
                "or mandate. Buddy reasons over the live context using the configured BUDDY_MODEL "
                "(Claude: adaptive thinking + compaction; Gemini: streaming). "
                "Returns a grounded, honest answer based solely on live execution data."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to ask Buddy about the current system state"
                    }
                },
                "required": ["question"],
                "strict": True,
            },
        ),
        types.Tool(
            name="update_mandate",
            description=(
                "Overrides the DAG's active Mandate with a new directive. "
                "The Mandate governs Buddy's story synthesis and the overall system behavior. "
                "Use to redirect the system mid-run without restarting the DAG."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "mandate": {
                        "type": "string",
                        "description": "The new mandate directive text"
                    }
                },
                "required": ["mandate"],
                "strict": True,
            },
        ),
    ]


@app.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Dispatches all MCP tool calls to the Sovereign Hub."""
    global global_dag, _buddy

    # All tools except read_ongoing_mandate and get_dag_status require a live DAG
    _dag_required = name not in {}  # all tools need the DAG
    if not global_dag or not global_dag.context:
        return [types.TextContent(
            type="text",
            text="Error: The Sovereign Mega DAG is not ignited or context is missing."
        )]

    ctx = global_dag.context

    # ------------------------------------------------------------------ #
    # read_ongoing_mandate                                                 #
    # ------------------------------------------------------------------ #
    if name == "read_ongoing_mandate":
        import time
        elapsed = round(time.time() - ctx.start_time, 1)
        response = (
            f"**Mandate:**\n{ctx.mandate}\n\n"
            f"**Contextual Story:**\n{ctx.contextual_story}\n\n"
            f"**Iterations:** {ctx.iterations} | "
            f"**JIT Cycles:** {ctx.state.get('jit_cycles', 0)} | "
            f"**Elapsed:** {elapsed}s\n\n"
            f"**Recent Narrative (last 500 chars):**\n{ctx.narrative[-500:]}"
        )
        return [types.TextContent(type="text", text=response)]

    # ------------------------------------------------------------------ #
    # get_dag_status                                                       #
    # ------------------------------------------------------------------ #
    elif name == "get_dag_status":
        import time
        elapsed = round(time.time() - ctx.start_time, 1)
        queue_size = global_dag.queue.qsize()
        ops = list(global_dag.operators.keys())
        tools = list(global_dag.tool_handlers.keys())
        status = (
            f"**DAG Health:**\n"
            f"- Queue depth: {queue_size}\n"
            f"- Iterations: {ctx.iterations} / {global_dag.max_iterations}\n"
            f"- Elapsed: {elapsed}s\n"
            f"- Max depth: {global_dag.max_depth}\n"
            f"- Concurrency limit: {global_dag._concurrency._value}\n\n"
            f"**Registered Operators:** {[o.value for o in ops]}\n\n"
            f"**Registered Tools:** {tools}\n\n"
            f"**State Keys:** {list(ctx.state.keys())}"
        )
        return [types.TextContent(type="text", text=status)]

    # ------------------------------------------------------------------ #
    # submit_intent                                                        #
    # ------------------------------------------------------------------ #
    elif name == "submit_intent":
        if not arguments or "goal" not in arguments:
            return [types.TextContent(type="text", text="Error: 'goal' argument is required.")]

        goal = arguments["goal"]
        logger.info(f"🎤 [MCP CHAT] Intent Received: {goal}")

        if global_dag.queue.closed if hasattr(global_dag.queue, "closed") else False:
            return [types.TextContent(type="text", text="Error: DAG queue is closed. Restart the DAG.")]

        # Route through SOTA_JIT so the intent is domain-enriched before planning
        # (KI: tool_use_overview — JIT gates planning to prevent hallucinated tool calls)
        jit_node = DagNode(
            node_type=NodeType.SOTA_JIT,
            goal=f"HUMAN INTENT — enrich, validate, and plan: {goal}"
        )
        await global_dag.queue.put(jit_node)
        return [types.TextContent(
            type="text",
            text=f"✅ Intent queued via SOTA_JIT enrichment: '{goal}'"
        )]

    # ------------------------------------------------------------------ #
    # inject_state                                                         #
    # ------------------------------------------------------------------ #
    elif name == "inject_state":
        if not arguments or "updates" not in arguments:
            return [types.TextContent(type="text", text="Error: 'updates' object is required.")]

        updates = arguments["updates"]
        if not isinstance(updates, dict):
            return [types.TextContent(type="text", text="Error: 'updates' must be a JSON object.")]

        ctx.state.update(updates)
        logger.info(f"[CHAT] State injected: {list(updates.keys())}")
        return [types.TextContent(
            type="text",
            text=f"✅ State updated. Keys merged: {list(updates.keys())}"
        )]

    # ------------------------------------------------------------------ #
    # query_buddy                                                          #
    # ------------------------------------------------------------------ #
    elif name == "query_buddy":
        if not arguments or "question" not in arguments:
            return [types.TextContent(type="text", text="Error: 'question' argument is required.")]

        question = arguments["question"]
        if not _buddy:
            return [types.TextContent(type="text", text="Error: BuddyOperator not initialised.")]

        try:
            answer = await _buddy.answer_question(question, ctx)
        except Exception as e:
            logger.error(f"[CHAT] query_buddy failed: {e}")
            return [types.TextContent(type="text", text=f"Error: Buddy query failed — {e}")]

        return [types.TextContent(type="text", text=answer.strip() or "(Buddy returned empty response)")]

    # ------------------------------------------------------------------ #
    # update_mandate                                                       #
    # ------------------------------------------------------------------ #
    elif name == "update_mandate":
        if not arguments or "mandate" not in arguments:
            return [types.TextContent(type="text", text="Error: 'mandate' argument is required.")]

        new_mandate = arguments["mandate"].strip()
        if not new_mandate:
            return [types.TextContent(type="text", text="Error: mandate must be non-empty.")]

        old = ctx.mandate
        ctx.mandate = new_mandate
        logger.info(f"[CHAT] Mandate overridden via MCP.")
        return [types.TextContent(
            type="text",
            text=f"✅ Mandate updated.\n\nOLD: {old}\n\nNEW: {new_mandate}"
        )]

    else:
        raise ValueError(f"Unknown tool: {name}")


async def run_mcp_chat_server(dag_instance: ContinuousMegaDAG):
    """
    Entry point: wires the Sovereign Hub to the MCP chat interface.

    Responsibilities:
    1. Store DAG reference for handler access.
    2. Register BuddyOperator on the DAG (was previously imported but never wired).
    3. Register all DEFAULT_TOOLS so intents submitted via chat have real tools available.
    4. Start the MCP stdio server.
    """
    global global_dag, _buddy

    global_dag = dag_instance

    # Wire BuddyOperator — previously imported but never registered, causing BUDDY
    # nodes to silently no-op through the ToolooOperator stub.
    _buddy = BuddyOperator()
    global_dag.register_operator(NodeType.BUDDY, _buddy)
    logger.info("✅ BuddyOperator registered on Sovereign DAG.")

    # Register DEFAULT_TOOLS so the DAG's planning operators have real actions available.
    # Without this, submit_intent would plan against an empty tool registry.
    for tool_name, tool_cfg in DEFAULT_TOOLS.items():
        global_dag.register_tool(tool_name, tool_cfg["handler"], tool_cfg["schema"])
    logger.info(f"✅ {len(DEFAULT_TOOLS)} DEFAULT_TOOLS registered on Sovereign DAG.")

    logger.info("Initializing MCP Chat Interface Bridge...")
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="tooloo-sovereign-chat",
                server_version="0.2.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
