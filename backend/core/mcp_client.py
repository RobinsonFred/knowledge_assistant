import asyncio
import json
from pathlib import Path
from typing import Any


class MCPClient:
    def __init__(self, server_path: str, allowed_paths: list[str] | None = None):
        self.server_path = server_path
        self.allowed_paths = allowed_paths or ["."]
        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0
        self._initialized = False

    async def start(self) -> None:
        args = [
            "python",
            str(self.server_path),
            *self.allowed_paths,
        ]

        self._process = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Initialize the connection
        await self._initialize()

    async def _initialize(self) -> dict[str, Any]:
        response = await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "knowledge-assistant",
                "version": "1.0.0",
            },
        })
        self._initialized = True
        return response

    async def _send_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if self._process is None or self._process.stdin is None or self._process.stdout is None:
            raise RuntimeError("MCP client not started")

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }

        request_line = json.dumps(request) + "\n"
        self._process.stdin.write(request_line.encode())
        await self._process.stdin.drain()

        response_line = await self._process.stdout.readline()
        response = json.loads(response_line.decode().strip())

        if "error" in response:
            raise RuntimeError(f"MCP error: {response['error']}")

        return response.get("result", {})

    async def list_tools(self) -> list[dict[str, Any]]:
        result = await self._send_request("tools/list", {})
        return result.get("tools", [])

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        result = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments,
        })

        content = result.get("content", [])
        if content and content[0].get("type") == "text":
            return json.loads(content[0]["text"])

        return result

    async def list_files(
        self,
        path: str,
        pattern: str = "*",
        recursive: bool = False,
    ) -> dict[str, Any]:
        return await self.call_tool("list_files", {
            "path": path,
            "pattern": pattern,
            "recursive": recursive,
        })

    async def read_file(self, path: str) -> dict[str, Any]:
        return await self.call_tool("read_file", {"path": path})

    async def get_file_metadata(self, path: str) -> dict[str, Any]:
        return await self.call_tool("get_file_metadata", {"path": path})

    async def stop(self) -> None:
        if self._process:
            self._process.terminate()
            await self._process.wait()
            self._process = None
            self._initialized = False


def get_filesystem_mcp_client(allowed_paths: list[str] | None = None) -> MCPClient:
    server_path = Path(__file__).parent.parent.parent / "mcp_servers" / "filesystem" / "server.py"
    return MCPClient(str(server_path), allowed_paths)
