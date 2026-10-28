import { Alert, Button, Chip, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { PageTitle, QueryState } from "../components/State";
import { useRunId } from "../hooks/useDataset";
import { getJson, inr, npsText } from "../services/api";

interface ReportDocument {
  alert_level: string;
  fact_check: { passed: boolean; failures: unknown[]; warnings: unknown[] };
  report: {
    headline: string;
    alert_reasons: string[];
    nps_performance: { overall: { nps: number | null; total_responses: number }; months: { label: string; nps: number | null; total_responses: number }[] };
    why_it_moved: { status: string; association?: { statement: string }; detail?: string };
    financial_exposure: { status: string; statement?: string; revenue_exposed_inr?: number; estimated_expected_revenue_at_risk_inr?: number; detail?: string };
    actions: { priority: number; title: string; evidence: string; suggested_owner: string; timeframe: string; success_metric: string }[];
    callbacks: { response_id: string; timeframe: string; theme: string }[];
    caveats: { notes: string[] };
    quotes: { response_id: string; comment: string }[];
  };
}

export function ReportPage() {
  const runId = useRunId();
  const query = useQuery({
    queryKey: ["report", runId],
    queryFn: () => getJson<ReportDocument>(`/api/reports/${runId}`),
    enabled: Boolean(runId),
  });
  const report = query.data?.report;
  return (
    <>
      <PageTitle title="Leadership report" subtitle="Numbers in this brief were checked against the calculation before it was stored." />
      <QueryState loading={query.isLoading} error={query.error} empty={!runId} emptyMessage="Run the specialist analysis from Executive Overview to open the brief.">
        {query.data && report ? (
          <Stack spacing={2}>
            <Stack direction="row" spacing={1}>
              <Chip label={query.data.alert_level} color={query.data.alert_level === "RED" ? "error" : "warning"} />
              <Chip label={query.data.fact_check.passed ? "Fact check passed" : "Fact check failed"} color={query.data.fact_check.passed ? "success" : "error"} />
              <Button href={`/api/reports/${runId}/export?format=md`}>Markdown</Button>
              <Button href={`/api/reports/${runId}/export?format=html`}>HTML</Button>
            </Stack>
            <Typography variant="h5">{report.headline}</Typography>
            {report.alert_reasons.map((reason) => <Alert key={reason} severity="error">{reason}</Alert>)}
            <Typography>
              Full-period NPS {npsText(report.nps_performance.overall.nps)} on {report.nps_performance.overall.total_responses} responses.
            </Typography>
            {report.nps_performance.months.map((month) => (
              <Typography key={month.label}>{month.label}: {npsText(month.nps)} (n={month.total_responses})</Typography>
            ))}
            <Typography variant="h6">Why it moved</Typography>
            <Typography>{report.why_it_moved.status === "available" ? report.why_it_moved.association?.statement : report.why_it_moved.detail}</Typography>
            {report.quotes.map((quote) => (
              <Typography key={quote.response_id}>“{quote.comment}” — {quote.response_id}</Typography>
            ))}
            <Typography variant="h6">Financial exposure</Typography>
            {report.financial_exposure.status === "available" ? (
              <>
                <Typography>{report.financial_exposure.statement}</Typography>
                <Typography>Exposed {inr(report.financial_exposure.revenue_exposed_inr)} · expected at risk {inr(report.financial_exposure.estimated_expected_revenue_at_risk_inr)}</Typography>
              </>
            ) : (
              <Typography>{report.financial_exposure.detail}</Typography>
            )}
            <Typography variant="h6">Actions</Typography>
            {report.actions.map((action) => (
              <Alert key={action.priority} severity="info">
                {action.priority}. {action.title} · {action.timeframe} · {action.suggested_owner}. {action.evidence} Success: {action.success_metric}
              </Alert>
            ))}
            <Typography variant="h6">Callbacks</Typography>
            {report.callbacks.map((row) => <Typography key={row.response_id}>{row.timeframe} {row.response_id} {row.theme}</Typography>)}
            <Typography variant="h6">Caveats</Typography>
            {report.caveats.notes.map((note) => <Typography key={note}>{note}</Typography>)}
          </Stack>
        ) : null}
      </QueryState>
    </>
  );
}
