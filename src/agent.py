from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        retrieved_chunks = self.store.search(question, top_k=top_k)

        if retrieved_chunks:
            context_blocks = []
            for index, chunk in enumerate(retrieved_chunks, start=1):
                source = chunk["metadata"].get("doc_id", chunk["id"])
                context_blocks.append(f"[{index}] source={source}\n{chunk['content']}")
            context = "\n\n".join(context_blocks)
        else:
            context = "No supporting context was retrieved."

        prompt = (
            "You are a grounded knowledge base assistant.\n"
            "Answer the question using only the provided context.\n"
            "If the context is insufficient, say that the answer is not available in the knowledge base.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )
        return self.llm_fn(prompt)
