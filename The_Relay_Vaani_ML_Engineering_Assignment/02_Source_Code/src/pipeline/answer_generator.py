"""
Stage 4: Answer Generator
Constructs grounded prompts requiring strict adherence to retrieved passages,
explicit uncertainty, and precise inline citations [arXiv:IDvV, p.X, §Y].
Invokes the model provider (Groq or Stand-in).
"""

from typing import List, Dict, Any, Optional
from src.providers.base import ModelProvider, ProviderResponse

SYSTEM_PROMPT = """You are a rigorous ML Research Assistant for The Relay.
You answer questions EXCLUSIVELY using the provided retrieved passages from these three papers:
1. Attention Is All You Need (arXiv:1706.03762v7)
2. Moshi: a speech-text foundation model for real-time dialogue (arXiv:2410.00037v1)
3. Dynamic Chunking for End-to-End Hierarchical Sequence Modeling (arXiv:2507.07955v2)

STRICT CITATION RULES:
1. Every factual assertion, parameter, metric, or architectural detail MUST include an inline citation citing where in the paper it came from.
2. Citations MUST strictly use this exact format: [arXiv:<arxiv_id><version>, p.<page_number>, §<section>]
   Example: [arXiv:1706.03762v7, p.4, §3.2] or [arXiv:2410.00037v1, p.8, §3.1]
3. NEVER invent or hallucinate a page number that does not appear in the metadata of the provided passages.
4. If the retrieved passages do NOT contain sufficient evidence to answer the question, state clearly and honestly:
   "The provided papers do not contain sufficient evidence to answer this question."
5. Do NOT extrapolate or use outside knowledge. Keep answers technically concise and direct.
"""

def format_context_passages(passages: List[Dict[str, Any]]) -> str:
    """Format retrieved chunks into clean, cited context blocks for the prompt."""
    formatted_blocks = []
    for idx, chunk in enumerate(passages, 1):
        arxiv_tag = f"{chunk['arxiv_id']}{chunk['version']}"
        block = (
            f"--- PASSAGE {idx} ---\n"
            f"Paper: {chunk['paper_title']} (arXiv:{arxiv_tag})\n"
            f"Page: {chunk['page_number']} | Section: {chunk['section']}\n"
            f"Content:\n{chunk['text']}\n"
        )
        formatted_blocks.append(block)
    return "\n".join(formatted_blocks)

def build_prompt_messages(
    query: str,
    passages: List[Dict[str, Any]],
    refinement_instruction: Optional[str] = None
) -> List[Dict[str, str]]:
    """Build the chat completion messages list."""
    context_text = format_context_passages(passages)
    
    user_content = (
        f"USER QUESTION: {query}\n\n"
        f"RETRIEVED LIBRARY PASSAGES:\n{context_text}\n\n"
        f"INSTRUCTIONS:\nAnswer the question using ONLY the facts from the passages above. "
        f"Cite every fact with [arXiv:<id><ver>, p.<page>, §<section>]."
    )

    if refinement_instruction:
        user_content += f"\n\nCORRECTION INSTRUCTION:\n{refinement_instruction}"

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]

async def generate_answer(
    provider: ModelProvider,
    query: str,
    passages: List[Dict[str, Any]],
    stream: bool = False,
    refinement_instruction: Optional[str] = None,
    timeout: float = 25.0
) -> ProviderResponse:
    """
    Generate cited answer using the configured ModelProvider.
    """
    messages = build_prompt_messages(
        query=query,
        passages=passages,
        refinement_instruction=refinement_instruction
    )

    response = await provider.generate(
        messages=messages,
        stream=stream,
        temperature=0.0,
        max_tokens=1024,
        timeout=timeout
    )
    return response

