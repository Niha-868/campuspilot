import os
import sys
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Set up logging for client calls
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TrackerAgent:
    def __init__(self):
        # Locate the tracker_mcp.py file in the workspace
        self.server_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "mcp_server",
            "tracker_mcp.py"
        )
        self.server_params = StdioServerParameters(
            command=sys.executable,
            args=[self.server_path],
            env=os.environ.copy()
        )

    def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Launches the MCP server as a separate process, calls the specified tool,
        and returns the string response.
        """
        logging.info(f"[MCP Client] Launching tracker MCP server process to invoke tool: '{tool_name}'...")
        
        async def _async_call():
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    logging.info(f"[MCP Client] Session initialized. Sending JSON-RPC call for tool '{tool_name}' with arguments: {list(arguments.keys())}")
                    result = await session.call_tool(tool_name, arguments=arguments)
                    
                    if result.content and len(result.content) > 0:
                        return result.content[0].text
                    return ""

        # Safe execution of async loop in synchronous environment
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # If for some reason we are in a running loop thread (e.g. nested contexts)
            # we run it via another loop or threadsafe, but normally Flask threads don't have running loops.
            return loop.run_until_complete(_async_call())
        else:
            return asyncio.run(_async_call())

    def get_profile(self, student_id: str) -> Dict[str, Any]:
        logging.info(f"[MCP Client] Requesting profile for student: {student_id}")
        res_str = self._call_tool("get_profile", {"student_id": student_id})
        try:
            return json.loads(res_str)
        except json.JSONDecodeError:
            logging.error(f"[MCP Client] Failed to decode profile JSON response: {res_str}")
            return {}

    def log_session_result(self, student_id: str, stage: str, score: float, feedback: str, topic: Optional[str] = None) -> Dict[str, Any]:
        logging.info(f"[MCP Client] Logging session result for stage: {stage}, score: {score}")
        res_str = self._call_tool("log_session_result", {
            "student_id": student_id,
            "stage": stage,
            "score": score,
            "feedback": feedback,
            "topic": topic
        })
        try:
            return json.loads(res_str)
        except json.JSONDecodeError:
            logging.error(f"[MCP Client] Failed to decode session response JSON: {res_str}")
            return {}

    def get_weak_areas(self, student_id: str) -> Dict[str, float]:
        logging.info(f"[MCP Client] Requesting weak areas for student: {student_id}")
        res_str = self._call_tool("get_weak_areas", {"student_id": student_id})
        try:
            return json.loads(res_str)
        except json.JSONDecodeError:
            logging.error(f"[MCP Client] Failed to decode weak areas JSON response: {res_str}")
            return {}

    def get_next_focus(self, student_id: str) -> str:
        logging.info(f"[MCP Client] Requesting next focus for student: {student_id}")
        return self._call_tool("get_next_focus", {"student_id": student_id})
