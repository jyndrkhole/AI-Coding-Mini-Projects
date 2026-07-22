const API_BASE = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  dashboard: () => request<import("../types").DashboardStats>("/dashboard"),

  workspaces: {
    list: () => request<import("../types").Workspace[]>("/workspaces"),
    create: (data: { name: string; description?: string; color?: string }) =>
      request<import("../types").Workspace>("/workspaces", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: number, data: Partial<{ name: string; description: string; color: string }>) =>
      request<import("../types").Workspace>(`/workspaces/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (id: number) =>
      request<{ ok: boolean }>(`/workspaces/${id}`, { method: "DELETE" }),
  },

  emails: {
    compose: (data: Record<string, unknown>) =>
      request<import("../types").EmailGenerateResponse>("/emails/compose", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    reply: (data: Record<string, unknown>) =>
      request<import("../types").EmailGenerateResponse>("/emails/reply", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    rewrite: (data: { text: string; mode: string; workspace_id?: number }) =>
      request<import("../types").EmailGenerateResponse>("/emails/rewrite", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    analyzeThread: (data: { thread: string; workspace_id?: number }) =>
      request<import("../types").ThreadAnalysis>("/emails/analyze-thread", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    saveFinal: (id: number, final_text: string, use_as_style_example = true) =>
      request<import("../types").EmailRecord>(`/emails/${id}/save-final`, {
        method: "POST",
        body: JSON.stringify({ final_text, use_as_style_example }),
      }),
    list: (workspace_id?: number) =>
      request<import("../types").EmailRecord[]>(
        `/emails${workspace_id ? `?workspace_id=${workspace_id}` : ""}`
      ),
  },

  knowledge: {
    list: (workspace_id?: number) =>
      request<import("../types").Document[]>(
        `/knowledge/documents${workspace_id ? `?workspace_id=${workspace_id}` : ""}`
      ),
    upload: async (workspaceId: number, file: File, category: string) => {
      const form = new FormData();
      form.append("workspace_id", String(workspaceId));
      form.append("category", category);
      form.append("file", file);
      const res = await fetch(`${API_BASE}/knowledge/upload`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || "Upload failed");
      }
      return res.json() as Promise<import("../types").Document>;
    },
    ingestText: (data: {
      workspace_id: number;
      title: string;
      content: string;
      category?: string;
    }) =>
      request<import("../types").Document>("/knowledge/text", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    importChatGPT: (data: {
      workspace_id: number;
      title?: string;
      content: string;
    }) =>
      request<import("../types").Document>("/knowledge/import-chatgpt", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    delete: (id: number) =>
      request<{ ok: boolean }>(`/knowledge/documents/${id}`, { method: "DELETE" }),
    search: (data: {
      query: string;
      workspace_id: number;
      top_k?: number;
      context_sources?: string[];
    }) =>
      request<{ query: string; results: import("../types").SearchResult[] }>(
        "/knowledge/search",
        { method: "POST", body: JSON.stringify(data) }
      ),
  },

  prompts: {
    list: () => request<import("../types").PromptTemplate[]>("/prompts"),
    create: (data: {
      name: string;
      category?: string;
      description?: string;
      template: string;
      variables?: string[];
    }) =>
      request<import("../types").PromptTemplate>("/prompts", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: number, data: Record<string, unknown>) =>
      request<import("../types").PromptTemplate>(`/prompts/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (id: number) =>
      request<{ ok: boolean }>(`/prompts/${id}`, { method: "DELETE" }),
  },

  settings: {
    get: () => request<import("../types").Settings>("/settings"),
    update: (data: Record<string, unknown>) =>
      request<import("../types").Settings>("/settings", {
        method: "PUT",
        body: JSON.stringify(data),
      }),
  },

  style: {
    list: () => request<import("../types").StyleExample[]>("/style/examples"),
    add: (data: {
      content: string;
      category?: string;
      notes?: string;
      greeting?: string;
      sign_off?: string;
    }) =>
      request<import("../types").StyleExample>("/style/examples", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    delete: (id: number) =>
      request<{ ok: boolean }>(`/style/examples/${id}`, { method: "DELETE" }),
  },

  chat: {
    send: (data: {
      message: string;
      workspace_id?: number;
      use_knowledge_base?: boolean;
    }) =>
      request<{
        reply: import("../types").ChatMessage;
        context_used?: string | null;
      }>("/chat", { method: "POST", body: JSON.stringify(data) }),
    history: (workspace_id?: number) =>
      request<import("../types").ChatMessage[]>(
        `/chat/history${workspace_id ? `?workspace_id=${workspace_id}` : ""}`
      ),
  },

  logs: {
    list: (workspace_id?: number) =>
      request<import("../types").LogEntry[]>(
        `/logs${workspace_id ? `?workspace_id=${workspace_id}` : ""}`
      ),
    get: (id: number) => request<import("../types").LogEntry>(`/logs/${id}`),
  },
};
