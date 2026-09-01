export function ApiDocsPage() {
  return (
    <section className="card panel">
      <div className="panel-header">
        <div>
          <h3>API documentation</h3>
          <p className="help">Swagger UI for this internal test webhook receiver.</p>
        </div>
        <a className="btn secondary" href="/api-docs" target="_blank" rel="noreferrer">
          Open in new tab
        </a>
      </div>
      <iframe className="docs-frame" title="Swagger UI" src="/api-docs" />
    </section>
  );
}
