import asyncio
import os
from datetime import datetime
from pathlib import Path

from mcp_servers.common.base import MCPServer


class FilesystemMCPServer(MCPServer):
    def __init__(self, allowed_paths: list[str] | None = None):
        super().__init__(name="filesystem", version="1.0.0")
        self.allowed_paths = [Path(p).resolve() for p in (allowed_paths or ["."])]

    def _is_path_allowed(self, path: Path) -> bool:
        resolved = path.resolve()
        return any(
            resolved == allowed or allowed in resolved.parents
            for allowed in self.allowed_paths
        )

    async def setup_tools(self) -> None:
        self.register_tool(
            name="list_files",
            description="List files in a directory matching optional glob pattern",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to filter files (e.g., '*.md')",
                        "default": "*",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Whether to search recursively",
                        "default": False,
                    },
                },
                "required": ["path"],
            },
            handler=self.list_files,
        )

        self.register_tool(
            name="read_file",
            description="Read the contents of a file",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read",
                    },
                },
                "required": ["path"],
            },
            handler=self.read_file,
        )

        self.register_tool(
            name="get_file_metadata",
            description="Get metadata about a file (size, timestamps)",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file",
                    },
                },
                "required": ["path"],
            },
            handler=self.get_file_metadata,
        )

    async def list_files(
        self,
        path: str,
        pattern: str = "*",
        recursive: bool = False,
    ) -> dict:
        dir_path = Path(path)

        if not self._is_path_allowed(dir_path):
            raise PermissionError(f"Access denied: {path}")

        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")

        if not dir_path.is_dir():
            raise ValueError(f"Not a directory: {path}")

        glob_method = dir_path.rglob if recursive else dir_path.glob
        files = list(glob_method(pattern))

        return {
            "path": str(dir_path),
            "pattern": pattern,
            "recursive": recursive,
            "files": [
                {
                    "path": str(f),
                    "name": f.name,
                    "is_file": f.is_file(),
                    "is_dir": f.is_dir(),
                }
                for f in files
                if self._is_path_allowed(f)
            ],
        }

    async def read_file(self, path: str) -> dict:
        file_path = Path(path)

        if not self._is_path_allowed(file_path):
            raise PermissionError(f"Access denied: {path}")

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if not file_path.is_file():
            raise ValueError(f"Not a file: {path}")

        content = file_path.read_text(encoding="utf-8", errors="replace")

        return {
            "path": str(file_path),
            "content": content,
            "size": len(content),
        }

    async def get_file_metadata(self, path: str) -> dict:
        file_path = Path(path)

        if not self._is_path_allowed(file_path):
            raise PermissionError(f"Access denied: {path}")

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        stat = file_path.stat()

        return {
            "path": str(file_path),
            "name": file_path.name,
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "is_file": file_path.is_file(),
            "is_dir": file_path.is_dir(),
        }


async def main() -> None:
    import sys

    allowed_paths = sys.argv[1:] if len(sys.argv) > 1 else ["."]
    server = FilesystemMCPServer(allowed_paths=allowed_paths)
    await server.setup_tools()
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
