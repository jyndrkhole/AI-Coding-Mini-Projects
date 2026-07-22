"""RAG query chain using Groq or xAI Grok as the LLM."""

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from rag.config import (
    GROK_MODEL,
    GROQ_API_KEY,
    GROQ_MODEL,
    LLM_PROVIDER,
    SYSTEM_PROMPT,
    XAI_API_KEY,
)
from rag.vectorstore import get_retriever


def _format_docs(docs) -> str:
    parts = []
    for i, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page")
        header = f"[{i}] Source: {source}"
        if page is not None:
            header += f" (page {page + 1})"
        parts.append(f"{header}\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


def _resolve_provider() -> str:
    if LLM_PROVIDER in {"groq", "xai"}:
        return LLM_PROVIDER
    if GROQ_API_KEY:
        return "groq"
    if XAI_API_KEY:
        return "xai"
    return ""


def get_llm() -> BaseChatModel:
    provider = _resolve_provider()

    if provider == "groq":
        if not GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is not set. Get a free key at https://console.groq.com/"
            )
        from langchain_groq import ChatGroq

        return ChatGroq(model=GROQ_MODEL, groq_api_key=GROQ_API_KEY, temperature=0.2)

    if provider == "xai":
        if not XAI_API_KEY or XAI_API_KEY.startswith("gsk_"):
            raise ValueError(
                "XAI_API_KEY is not set or looks like a Groq key (gsk_...). "
                "Use GROQ_API_KEY for Groq, or get an xAI key at https://console.x.ai/"
            )
        from langchain_xai import ChatXAI

        return ChatXAI(model=GROK_MODEL, xai_api_key=XAI_API_KEY, temperature=0.2)

    raise ValueError(
        "No LLM API key found. Set GROQ_API_KEY (Groq, gsk_...) or "
        "XAI_API_KEY (xAI Grok, xai-...) in your .env file."
    )


def build_rag_chain():
    """Build a LangChain RAG chain: retrieve → prompt → LLM → answer."""
    retriever = get_retriever()
    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            (
                "human",
                "Context from study materials:\n\n{context}\n\n"
                "Interview question: {question}\n\n"
                "Provide a clear, interview-ready answer.",
            ),
        ]
    )

    chain = (
        {"context": retriever | _format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain


def ask(question: str) -> tuple[str, list[dict]]:
    """Ask a question and return (answer, source_chunks)."""
    retriever = get_retriever()
    docs = retriever.invoke(question)
    chain = build_rag_chain()
    answer = chain.invoke(question)

    sources = [
        {
            "source": doc.metadata.get("source", "unknown"),
            "page": doc.metadata.get("page"),
            "preview": doc.page_content[:300] + ("..." if len(doc.page_content) > 300 else ""),
        }
        for doc in docs
    ]
    return answer, sources
