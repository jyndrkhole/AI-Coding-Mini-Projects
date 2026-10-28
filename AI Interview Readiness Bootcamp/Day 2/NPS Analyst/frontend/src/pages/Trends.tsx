import { Alert, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { NpsTrend } from "../charts/NpsTrend";
import { PageTitle, QueryState } from "../components/State";
import { useDatasetId } from "../hooks/useDataset";
import { getJson, npsText } from "../services/api";

interface Month {
  month: string;
  nps: number | null;
  nps_change: number | null;
  total_responses: number;
  promoters: number;
  passives: number;
  detractors: number;
  caution: string | null;
  confidence_low: number | null;
  confidence_high: number | null;
}

export function TrendsPage() {
  const datasetId = useDatasetId();
  const query = useQuery({
    queryKey: ["monthly", datasetId],
    queryFn: () => getJson<{ months: Month[]; reference_claims: { month: string; claimed_nps: number; actual_nps: number | null; status: string }[] }>(`/api/nps/${datasetId}/monthly`),
    enabled: Boolean(datasetId),
  });
  return (
    <>
      <PageTitle title="NPS trends" subtitle="Monthly scores, sample sizes, and bootstrap intervals. Missing months are not filled in." />
      <QueryState loading={query.isLoading} error={query.error} empty={!datasetId}>
        {query.data ? (
          <Stack spacing={3}>
            <NpsTrend rows={query.data.months} />
            {query.data.reference_claims.map((claim) => (
              <Alert key={claim.month} severity={claim.status === "match" ? "success" : "warning"}>
                {claim.month}: brief claimed {claim.claimed_nps}, calculated {npsText(claim.actual_nps)} ({claim.status}).
              </Alert>
            ))}
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Month</TableCell>
                  <TableCell>NPS</TableCell>
                  <TableCell>Change</TableCell>
                  <TableCell>95% interval</TableCell>
                  <TableCell>n</TableCell>
                  <TableCell>P / Pa / D</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {query.data.months.map((row) => (
                  <TableRow key={row.month}>
                    <TableCell>{row.month}</TableCell>
                    <TableCell>{npsText(row.nps)}</TableCell>
                    <TableCell>{npsText(row.nps_change)}</TableCell>
                    <TableCell>
                      {npsText(row.confidence_low)} to {npsText(row.confidence_high)}
                      {row.caution ? <Typography variant="caption" display="block">{row.caution}</Typography> : null}
                    </TableCell>
                    <TableCell>{row.total_responses}</TableCell>
                    <TableCell>{row.promoters} / {row.passives} / {row.detractors}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Stack>
        ) : null}
      </QueryState>
    </>
  );
}
