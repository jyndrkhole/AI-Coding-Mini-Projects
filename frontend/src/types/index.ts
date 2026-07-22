export interface Workspace {
  id: number;
  name: string;
  description?: string | null;
  color: string;
  is_default: boolean;
  created_at: string;
  document_count: number;
  email_count: number;
}

export interface EmailSuggestions {
  client_concerns: string[];
  missing_technical_points: string[];
  ambiguous_statements: string[];
  risk_analysis: string[];
  confidence_score: number;
  alternative_wording: string[];
}

export interface ThreadAnalysis {
  summary: string;
  key_decisions: string[];
  pending_questions: string[];
  blockers: string[];
  commitments: string[];
  risks: string[];
  next_actions: string[];
  stakeholders: string[];
}

export interface EmailGenerateResponse {
  id: number;
  generated_text: string;
  subject?: string | null;
  suggestions?: EmailSuggestions | null;
  thread_analysis?: ThreadAnalysis | null;
  context_used?: string | null;
  provider: string;
  model: string;
}

export interface EmailRecord {
  id: number;
  workspace_id?: number | null;
  mode: string;
  subject?: string | null;
  input_text: string;
  generated_text: string;
  final_text?: string | null;
  style?: string | null;
  rewrite_mode?: string | null;
  suggestions?: EmailSuggestions | null;
  thread_analysis?: ThreadAnalysis | null;
  created_at: string;
}

export interface Document {
  id: number;
  workspace_id: number;
  original_name: string;
  file_type: string;
  category: string;
  file_size: number;
  chunk_count: number;
  status: string;
  created_at: string;
}

export interface PromptTemplate {
  id: number;
  name: string;
  category: string;
  description?: string | null;
  template: string;
  variables?: string[] | null;
  is_builtin: boolean;
  usage_count: number;
  created_at: string;
}

export interface Settings {
  llm_provider: string;
  llm_model: string;
  llm_temperature: number;
  llm_max_tokens: number;
  groq_api_key_set: boolean;
  ollama_base_url: string;
  ollama_model: string;
  embedding_provider: string;
  embedding_model: string;
  chunk_size: number;
  chunk_overlap: number;
  retrieval_top_k: number;
  provider_healthy: boolean;
  available_rewrite_modes: Record<string, string>;
  available_reply_styles: string[];
}

export interface SearchResult {
  id: string;
  content: string;
  score: number;
  metadata: Record<string, unknown>;
}

export interface ChatMessage {
  id: number;
  role: string;
  content: string;
  created_at: string;
}

export interface LogEntry {
  id: number;
  workspace_id?: number | null;
  action: string;
  input_text: string;
  context_used?: string | null;
  prompt: string;
  llm_response: string;
  final_edited?: string | null;
  provider: string;
  model: string;
  temperature: number;
  tokens_used?: number | null;
  latency_ms?: number | null;
  created_at: string;
}

export interface DashboardStats {
  workspace_count: number;
  document_count: number;
  email_count: number;
  style_example_count: number;
  prompt_count: number;
  log_count: number;
  recent_emails: EmailRecord[];
  recent_documents: Document[];
}

export interface StyleExample {
  id: number;
  content: string;
  category: string;
  notes?: string | null;
  greeting?: string | null;
  sign_off?: string | null;
  created_at: string;
}

export const CONTEXT_SOURCES = [
  { id: "architecture", label: "Architecture Documents" },
  { id: "meeting_notes", label: "Meeting Notes" },
  { id: "previous_emails", label: "Previous Emails" },
  { id: "project_documents", label: "Project Documents" },
  { id: "chatgpt_knowledge", label: "ChatGPT Knowledge Base" },
  { id: "personal_notes", label: "Personal Notes" },
] as const;
