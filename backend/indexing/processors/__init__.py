from pathlib import Path
from typing import Protocol


class ContentProcessor(Protocol):
    def process(self, content: str) -> str:
        ...


class MarkdownProcessor:
    def process(self, content: str) -> str:
        # Keep markdown as-is, it's already good for chunking
        return content


class CodeProcessor:
    def __init__(self, language: str):
        self.language = language

    def process(self, content: str) -> str:
        # Add language context for better embedding
        return f"```{self.language}\n{content}\n```"


class PlainTextProcessor:
    def process(self, content: str) -> str:
        return content


def get_processor(file_path: str) -> ContentProcessor:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in {".md", ".markdown"}:
        return MarkdownProcessor()
    elif suffix == ".py":
        return CodeProcessor("python")
    elif suffix == ".js":
        return CodeProcessor("javascript")
    elif suffix == ".ts":
        return CodeProcessor("typescript")
    elif suffix == ".rs":
        return CodeProcessor("rust")
    elif suffix == ".go":
        return CodeProcessor("go")
    elif suffix == ".java":
        return CodeProcessor("java")
    elif suffix in {".c", ".h"}:
        return CodeProcessor("c")
    elif suffix in {".cpp", ".hpp", ".cc"}:
        return CodeProcessor("cpp")
    else:
        return PlainTextProcessor()
