import type { EmailSuggestions, ThreadAnalysis } from "../../types";

export function SuggestionsPanel({
  suggestions,
  analysis,
}: {
  suggestions?: EmailSuggestions | null;
  analysis?: ThreadAnalysis | null;
}) {
  if (!suggestions && !analysis) return null;

  return (
    <div className="panel">
      <h3 className="panel-title">AI Insights</h3>
      <div className="suggestions">
        {suggestions && (
          <>
            <div className="confidence">
              <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                Confidence
              </span>
              <div className="confidence-bar">
                <div
                  className="confidence-fill"
                  style={{ width: `${Math.min(100, suggestions.confidence_score)}%` }}
                />
              </div>
              <strong>{Math.round(suggestions.confidence_score)}</strong>
            </div>
            <SuggestionList title="Client concerns" items={suggestions.client_concerns} />
            <SuggestionList
              title="Missing technical points"
              items={suggestions.missing_technical_points}
            />
            <SuggestionList
              title="Ambiguous statements"
              items={suggestions.ambiguous_statements}
            />
            <SuggestionList title="Risk analysis" items={suggestions.risk_analysis} />
            <SuggestionList
              title="Alternative wording"
              items={suggestions.alternative_wording}
            />
          </>
        )}
        {analysis && (
          <>
            {analysis.summary && (
              <div className="suggestion-block">
                <h4>Thread summary</h4>
                <p style={{ margin: 0, fontSize: "0.88rem" }}>{analysis.summary}</p>
              </div>
            )}
            <SuggestionList title="Pending questions" items={analysis.pending_questions} />
            <SuggestionList title="Key decisions" items={analysis.key_decisions} />
            <SuggestionList title="Blockers" items={analysis.blockers} />
            <SuggestionList title="Commitments" items={analysis.commitments} />
            <SuggestionList title="Risks" items={analysis.risks} />
            <SuggestionList title="Next actions" items={analysis.next_actions} />
            <SuggestionList title="Stakeholders" items={analysis.stakeholders} />
          </>
        )}
      </div>
    </div>
  );
}

function SuggestionList({ title, items }: { title: string; items: string[] }) {
  if (!items?.length) return null;
  return (
    <div className="suggestion-block">
      <h4>{title}</h4>
      <ul>
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
