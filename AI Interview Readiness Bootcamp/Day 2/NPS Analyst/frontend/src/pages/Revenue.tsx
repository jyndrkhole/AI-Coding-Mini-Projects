import { Alert, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { PageTitle, QueryState } from "../components/State";
import { useDatasetId } from "../hooks/useDataset";
import { getJson, inr, npsText } from "../services/api";

interface Bucket {
  label: string;
  revenue_exposed_inr: number;
  estimated_expected_revenue_at_risk_inr: number;
  missing_revenue_count: number;
  coverage_percentage: number | null;
}
interface Revenue {
  revenue_exposed_inr: number;
  estimated_expected_revenue_at_risk_inr: number;
  missing_revenue_count: number;
  coverage_percentage: number | null;
  assumptions: { promoter_churn_probability: number; passive_churn_probability: number; detractor_churn_probability: number; note: string };
  note: string;
  by_group: Bucket[];
  by_theme: Bucket[];
  priorities: { highest_volume_theme: string | null; highest_expected_revenue_theme: string | null; same_theme: boolean; note: string; customer_impact: { theme: string; customer_impact_score: number; nps: number | null }[]; revenue_at_risk: { theme: string; expected_revenue_at_risk_inr: number | null }[] };
}

export function RevenuePage() {
  const datasetId = useDatasetId();
  const query = useQuery({
    queryKey: ["revenue", datasetId],
    queryFn: () => getJson<Revenue>(`/api/revenue-risk/${datasetId}`),
    enabled: Boolean(datasetId),
  });
  return (
    <>
      <PageTitle title="Revenue at risk" subtitle="Exposure and expected revenue at risk are separate. Neither is booked loss." />
      <QueryState loading={query.isLoading} error={query.error} empty={!datasetId}>
        {query.data ? (
          <Stack spacing={2}>
            <Alert severity="warning">{query.data.note}</Alert>
            <Typography>
              Exposed {inr(query.data.revenue_exposed_inr)} · expected at risk {inr(query.data.estimated_expected_revenue_at_risk_inr)} · coverage {query.data.coverage_percentage?.toFixed(1)}% · missing revenue rows {query.data.missing_revenue_count}
            </Typography>
            <Typography color="text.secondary">
              Assumptions: promoter {(query.data.assumptions.promoter_churn_probability * 100).toFixed(0)}%, passive {(query.data.assumptions.passive_churn_probability * 100).toFixed(0)}%, detractor {(query.data.assumptions.detractor_churn_probability * 100).toFixed(0)}%. {query.data.assumptions.note}
            </Typography>
            <Alert severity={query.data.priorities.same_theme ? "info" : "warning"}>
              Highest comment volume: {query.data.priorities.highest_volume_theme}. Highest expected revenue at risk: {query.data.priorities.highest_expected_revenue_theme}. {query.data.priorities.note}
            </Alert>
            <Typography variant="h6">By NPS group</Typography>
            <BucketTable rows={query.data.by_group} />
            <Typography variant="h6">Customer-impact ranking</Typography>
            {query.data.priorities.customer_impact.map((row) => (
              <Typography key={row.theme}>{row.theme} · impact {row.customer_impact_score.toFixed(2)} · NPS {npsText(row.nps)}</Typography>
            ))}
            <Typography variant="h6">Expected revenue ranking</Typography>
            {query.data.priorities.revenue_at_risk.map((row) => (
              <Typography key={row.theme}>{row.theme} · {inr(row.expected_revenue_at_risk_inr)}</Typography>
            ))}
          </Stack>
        ) : null}
      </QueryState>
    </>
  );
}

function BucketTable({ rows }: { rows: Bucket[] }) {
  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>Group</TableCell>
          <TableCell>Exposed</TableCell>
          <TableCell>Expected at risk</TableCell>
          <TableCell>Missing revenue</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.label}>
            <TableCell>{row.label}</TableCell>
            <TableCell>{inr(row.revenue_exposed_inr)}</TableCell>
            <TableCell>{inr(row.estimated_expected_revenue_at_risk_inr)}</TableCell>
            <TableCell>{row.missing_revenue_count}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
