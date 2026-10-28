import { Chip, Stack, Table, TableBody, TableCell, TableHead, TableRow } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { PageTitle, QueryState } from "../components/State";
import { useRunId } from "../hooks/useDataset";
import { getJson, inr } from "../services/api";

interface Candidate {
  response_id: string;
  product: string | null;
  score: number;
  annual_revenue_inr: number | null;
  theme: string;
  reason: string;
  timeframe: string;
  suggested_action: string;
  recommended_owner: string;
}

export function CallbacksPage() {
  const runId = useRunId();
  const query = useQuery({
    queryKey: ["callbacks", runId],
    queryFn: () => getJson<{ candidates: Candidate[] }>(`/api/callbacks/${runId}`),
    enabled: Boolean(runId),
  });
  return (
    <>
      <PageTitle title="Callback shortlist" subtitle="A person places any call. This screen only recommends who to contact and why." />
      <QueryState loading={query.isLoading} error={query.error} empty={!runId} emptyMessage="Run the specialist analysis from Executive Overview to build the shortlist.">
        {query.data ? (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>When</TableCell>
                <TableCell>Response</TableCell>
                <TableCell>Score</TableCell>
                <TableCell>Revenue</TableCell>
                <TableCell>Theme</TableCell>
                <TableCell>Why</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {query.data.candidates.map((row) => (
                <TableRow key={row.response_id}>
                  <TableCell><Chip size="small" label={row.timeframe} /></TableCell>
                  <TableCell>{row.response_id}<br />{row.product}</TableCell>
                  <TableCell>{row.score}</TableCell>
                  <TableCell>{inr(row.annual_revenue_inr)}</TableCell>
                  <TableCell>{row.theme}<br />{row.recommended_owner}</TableCell>
                  <TableCell>
                    <Stack spacing={0.5}>
                      <span>{row.reason}</span>
                      <span>{row.suggested_action}</span>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : null}
      </QueryState>
    </>
  );
}
