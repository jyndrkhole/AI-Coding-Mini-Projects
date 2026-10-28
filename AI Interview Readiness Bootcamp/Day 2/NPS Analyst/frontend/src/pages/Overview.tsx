import { Alert, Box, Button, Chip, Stack } from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { HorizontalBars } from "../charts/Bars";
import { NpsTrend } from "../charts/NpsTrend";
import { Kpi } from "../components/Kpi";
import { PageTitle, QueryState } from "../components/State";
import { useDatasetId, useDatasets } from "../hooks/useDataset";
import { getJson, inr, npsText, postJson } from "../services/api";

interface Overview {
  nps: number | null;
  promoters: number;
  passives: number;
  detractors: number;
  total_responses: number;
  alert: { level: string; reasons: string[] };
  period: { period_nps_change: number | null };
  estimated_expected_revenue_at_risk_inr: number | null;
  monthly: { month: string; nps: number | null }[];
  by_product: { segment: string; nps: number | null }[];
  top_themes: { theme: string; detractors: number }[];
  association: { statement: string };
}

export function OverviewPage() {
  const datasets = useDatasets();
  const datasetId = useDatasetId();
  const client = useQueryClient();
  const overview = useQuery({
    queryKey: ["overview", datasetId],
    queryFn: () => getJson<Overview>(`/api/overview/${datasetId}`),
    enabled: Boolean(datasetId),
  });
  const run = useMutation({
    mutationFn: () => postJson(`/api/analysis/${datasetId}/run?force=true`),
    onSuccess: () => client.invalidateQueries(),
  });
  const level = overview.data?.alert.level;
  return (
    <>
      <PageTitle title="Executive overview" subtitle="What changed, which experiences moved with it, and what revenue is exposed." />
      <QueryState loading={datasets.isLoading || overview.isLoading} error={datasets.error || overview.error} empty={!datasetId}>
        {overview.data ? (
          <Stack spacing={3}>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ alignItems: { sm: "center" } }}>
              <Chip label={level} color={level === "RED" ? "error" : level === "AMBER" ? "warning" : "success"} />
              <Button variant="contained" onClick={() => run.mutate()} disabled={run.isPending}>
                {run.isPending ? "Running analysis…" : "Run specialist analysis"}
              </Button>
            </Stack>
            {overview.data.alert.reasons.map((reason) => (
              <Alert key={reason} severity={level === "RED" ? "error" : "warning"}>
                {reason}
              </Alert>
            ))}
            <Alert severity="info">{overview.data.association.statement}</Alert>
            <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", md: "1fr 1fr 1fr 1fr" } }}>
              <Kpi label="Full-period NPS" value={npsText(overview.data.nps)} hint={`${overview.data.total_responses} responses`} />
              <Kpi label="Change from first month" value={npsText(overview.data.period.period_nps_change)} />
              <Kpi label="Promoters / passives / detractors" value={`${overview.data.promoters} / ${overview.data.passives} / ${overview.data.detractors}`} />
              <Kpi label="Expected revenue at risk" value={inr(overview.data.estimated_expected_revenue_at_risk_inr)} hint="Uses assumed churn rates, not measured losses" />
            </Box>
            <NpsTrend rows={overview.data.monthly} />
            <HorizontalBars rows={overview.data.by_product.map((row) => ({ name: row.segment, value: row.nps ?? 0 }))} color="#10233f" />
            <HorizontalBars rows={overview.data.top_themes.map((row) => ({ name: row.theme, value: row.detractors }))} color="#9f2d2d" />
          </Stack>
        ) : null}
      </QueryState>
    </>
  );
}
