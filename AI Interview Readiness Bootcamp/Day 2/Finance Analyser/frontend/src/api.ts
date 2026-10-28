import type { AnalyzeBody, HistoryItem, Report, Status } from "./types";

export async function getStatus(): Promise<Status> {
  const response = await fetch("/api/status");
  if (!response.ok) throw new Error("Status request failed.");
  return response.json();
}

export async function getHistory(): Promise<HistoryItem[]> {
  const response = await fetch("/api/reports");
  if (!response.ok) throw new Error("Could not load history.");
  return response.json();
}

export async function getReport(id: string): Promise<Report> {
  const response = await fetch(`/api/reports/${id}`);
  if (!response.ok) throw new Error("That report is no longer available.");
  return response.json();
}

export async function analyze(
  body: AnalyzeBody,
  onEvent: (event: { type: string; phase?: string; name?: string; detail?: string }) => void,
): Promise<Report> {
  const response = await fetch("/api/analyze/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok || !response.body) {
    const text = await response.text();
    throw new Error(text || "Analysis failed.");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let report: Report | null = null;
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const line = chunk.split("\n").find((item) => item.startsWith("data: "));
      if (!line) continue;
      const event = JSON.parse(line.slice(6)) as {
        type: string;
        phase?: string;
        name?: string;
        detail?: string;
        report?: Report;
      };
      if (event.type === "error") throw new Error(event.detail || "Analysis failed.");
      if (event.type === "report" && event.report) report = event.report;
      else onEvent(event);
    }
  }
  if (!report) throw new Error("The analysis ended without a report.");
  return report;
}
