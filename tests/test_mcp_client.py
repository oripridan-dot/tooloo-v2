import sys
import os
import asyncio
import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logging.basicConfig(level=logging.INFO, format='mcp_client: %(message)s')

async def run_client():
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["src/tooloo/orchestrator.py", "--mcp"],
        env=os.environ.copy()
    )

    logging.info("Starting MCP Chat connection via STDIO...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            logging.info("Connected to Sovereign MCP Server successfully!")
            
            # List available tools
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            logging.info(f"Available Chat Tools: {tool_names}")
            
            # Allow the Mega DAG a moment to start weaving its story
            await asyncio.sleep(5)
            
            # Call a tool directly: read_ongoing_mandate
            logging.info("Fetching Ongoing Mandate and Contextual Story...")
            result = await session.call_tool("read_ongoing_mandate", {})
            logging.info(f"\n[MANDATE RESULT]:\n{result.content[0].text}\n")
            
            # Send an intent through the MCP Chat
            logging.info("Injecting human intent...")
            intent_res = await session.call_tool("submit_intent", {"goal": "Optimize system vitality via testing"})
            logging.info(f"\n[INTENT SUBMIT RESULT]:\n{intent_res.content[0].text}\n")

if __name__ == "__main__":
    asyncio.run(run_client())
