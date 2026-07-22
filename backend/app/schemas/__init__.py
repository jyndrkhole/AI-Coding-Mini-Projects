"""Pydantic request/response schemas."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Workspaces ──────────────────────────────────────────────

class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    color: str = "#3b82f6"


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None


class WorkspaceOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    color: str
    is_default: bool
    created_at: datetime
    document_count: int = 0
    email_count: int = 0

    model_config = {"from_attributes": True}


# ── Compose / Reply / Rewrite ───────────────────────────────

class ComposeRequest(BaseModel):
    rough_notes: str = Field(..., min_length=1)
    subject: Optional[str] = None
    workspace_id: Optional[int] = None
    context_sources: list[str] = Field(default_factory=list)
    use_style_memory: bool = True
    use_knowledge_base: bool = True
    extra_instructions: Optional[str] = None
    prompt_template_id: Optional[int] = None


class ReplyRequest(BaseModel):
    thread: str = Field(..., min_length=1)
    style: str = "Formal"
    workspace_id: Optional[int] = None
    context_sources: list[str] = Field(default_factory=list)
    use_style_memory: bool = True
    use_knowledge_base: bool = True
    extra_instructions: Optional[str] = None
    analyze_thread: bool = True


class RewriteRequest(BaseModel):
    text: str = Field(..., min_length=1)
    mode: str
    workspace_id: Optional[int] = None


class ThreadAnalyzeRequest(BaseModel):
    thread: str = Field(..., min_length=1)
    workspace_id: Optional[int] = None


class EmailSuggestions(BaseModel):
    client_concerns: list[str] = Field(default_factory=list)
    missing_technical_points: list[str] = Field(default_factory=list)
    ambiguous_statements: list[str] = Field(default_factory=list)
    risk_analysis: list[str] = Field(default_factory=list)
    confidence_score: float = 0
    alternative_wording: list[str] = Field(default_factory=list)


class ThreadAnalysis(BaseModel):
    summary: str = ""
    key_decisions: list[str] = Field(default_factory=list)
    pending_questions: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    commitments: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    stakeholders: list[str] = Field(default_factory=list)


class EmailGenerateResponse(BaseModel):
    id: int
    generated_text: str
    subject: Optional[str] = None
    suggestions: Optional[EmailSuggestions] = None
    thread_analysis: Optional[ThreadAnalysis] = None
    context_used: Optional[str] = None
    provider: str
    model: str


class EmailSaveFinalRequest(BaseModel):
    final_text: str
    use_as_style_example: bool = True


class EmailOut(BaseModel):
    id: int
    workspace_id: Optional[int] = None
    mode: str
    subject: Optional[str] = None
    input_text: str
    generated_text: str
    final_text: Optional[str] = None
    style: Optional[str] = None
    rewrite_mode: Optional[str] = None
    suggestions: Optional[dict] = None
    thread_analysis: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Knowledge Base ──────────────────────────────────────────

class DocumentOut(BaseModel):
    id: int
    workspace_id: int
    original_name: str
    file_type: str
    category: str
    file_size: int
    chunk_count: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TextIngestRequest(BaseModel):
    workspace_id: int
    title: str
    content: str
    category: str = "notes"


class ChatGPTImportRequest(BaseModel):
    workspace_id: int
    title: str = "ChatGPT Conversation"
    content: str


# ── Search ──────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    workspace_id: int
    top_k: int = 8
    context_sources: list[str] = Field(default_factory=list)


class SearchResult(BaseModel):
    id: str
    content: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    results: list[SearchResult]
    query: str


# ── Prompts ─────────────────────────────────────────────────

class PromptCreate(BaseModel):
    name: str
    category: str = "custom"
    description: Optional[str] = None
    template: str
    variables: list[str] = Field(default_factory=list)


class PromptUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    template: Optional[str] = None
    variables: Optional[list[str]] = None


class PromptOut(BaseModel):
    id: int
    name: str
    category: str
    description: Optional[str] = None
    template: str
    variables: Optional[list] = None
    is_builtin: bool
    usage_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Style Memory ────────────────────────────────────────────

class StyleExampleCreate(BaseModel):
    content: str
    category: str = "sent_email"
    notes: Optional[str] = None
    greeting: Optional[str] = None
    sign_off: Optional[str] = None


class StyleExampleOut(BaseModel):
    id: int
    content: str
    category: str
    notes: Optional[str] = None
    greeting: Optional[str] = None
    sign_off: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class VocabularyCreate(BaseModel):
    term: str
    preferred_form: str
    notes: Optional[str] = None


# ── Settings ────────────────────────────────────────────────

class SettingsUpdate(BaseModel):
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_temperature: Optional[float] = None
    llm_max_tokens: Optional[int] = None
    groq_api_key: Optional[str] = None
    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = None
    embedding_provider: Optional[str] = None
    embedding_model: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    retrieval_top_k: Optional[int] = None


class SettingsOut(BaseModel):
    llm_provider: str
    llm_model: str
    llm_temperature: float
    llm_max_tokens: int
    groq_api_key_set: bool
    ollama_base_url: str
    ollama_model: str
    embedding_provider: str
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    retrieval_top_k: int
    provider_healthy: bool = False
    available_rewrite_modes: dict[str, str] = Field(default_factory=dict)
    available_reply_styles: list[str] = Field(default_factory=list)


# ── Chat ────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    workspace_id: Optional[int] = None
    use_knowledge_base: bool = True


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    reply: ChatMessageOut
    context_used: Optional[str] = None


# ── Logs ────────────────────────────────────────────────────

class LogOut(BaseModel):
    id: int
    workspace_id: Optional[int] = None
    action: str
    input_text: str
    context_used: Optional[str] = None
    prompt: str
    llm_response: str
    final_edited: Optional[str] = None
    provider: str
    model: str
    temperature: float
    tokens_used: Optional[int] = None
    latency_ms: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Dashboard ───────────────────────────────────────────────

class DashboardStats(BaseModel):
    workspace_count: int
    document_count: int
    email_count: int
    style_example_count: int
    prompt_count: int
    log_count: int
    recent_emails: list[EmailOut] = Field(default_factory=list)
    recent_documents: list[DocumentOut] = Field(default_factory=list)
