"""
Stage 2: Retrieval Tool
Implements the formal retrieval tool call schema and execution logic.
Provides callable function definition conforming to OpenAI / Groq tool specification.
"""

from typing import Dict, Any, Optional
from src.retrieval.retriever import retrieve, RetrievalResult

RETRIEVE_TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "retrieve_library_passages",
        "description": "Retrieve grounded passages and metadata from the 3 curated arXiv papers (1706.03762v7, 2410.00037v1, 2507.07955v2).",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Technical search query extracted from the user question."
                },
                "paper_filter": {
                    "type": "string",
                    "description": "Optional arXiv identifier to restrict search to a specific paper (e.g. '1706.03762').",
                    "nullable": True
                },
                "setting": {
                    "type": "string",
                    "description": "Retrieval configuration setting: 'A' (300tok/k=3), 'B' (600tok/k=5), or 'C' (900tok/k=5+rerank).",
                    "enum": ["A", "B", "C"],
                    "default": "A"
                }
            },
            "required": ["query"]
        }
    }
}

class RetrievalToolCall:
    def __init__(self, tool_name: str = "retrieve_library_passages", arguments: Optional[Dict[str, Any]] = None):
        self.tool_name = tool_name
        self.arguments = arguments or {}

    def execute(self, setting_override: Optional[str] = None) -> RetrievalResult:
        """Execute the retrieval tool call with the provided arguments."""
        query = self.arguments.get("query", "")
        setting = setting_override or self.arguments.get("setting", "A")
        paper_filter = self.arguments.get("paper_filter")
        
        return retrieve(
            query=query,
            setting=setting,
            paper_filter=paper_filter
        )

