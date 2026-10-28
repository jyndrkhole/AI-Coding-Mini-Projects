import { Chip, Stack, Table, TableBody, TableCell, TableHead, TableRow } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { PageTitle, QueryState } from "../components/State";
import { useRunId } from "../hooks/useDataset";
import { getJson } from "../services/api";

interface Step {
  phase: string;
  agent: string;
  status: string;
  duration_ms: number;
  tools: string[];
  error: string | null;
}

export function TracePage() {
  const runId = useRunId();
  const query = useQuery({
    queryKey: ["trace", runId],
    queryFn: () => getJson<{ trace: Step[] }>(`/api/agents/${runId}/trace`),
    enabled: Boolean(runId),
  });
  return (
    <>
      <PageTitle title="Analysis trace" subtitle="Phase 1 runs the score, voice, and revenue specialists together. Planning starts after they finish. The report is fact-checked." />
      <QueryState loading={query.isLoading} error={query.error} empty={!runId} emptyMessage="Run the specialist analysis from Executive Overview to see the trace.">
        {query.data ? (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Phase</TableCell>
                <TableCell>Agent</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Duration</TableCell>
                <TableCell>Tools</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {query.data.trace.map((step, index) => (
                <TableRow key={`${step.agent}-${index}`}>
                  <TableCell>{step.phase}</TableCell>
                  <TableCell>{step.agent}</TableCell>
                  <TableCell><Chip size="small" label={step.status} color={step.status === "failed" ? "error" : "default"} /></TableCell>
                  <TableCell>{step.duration_ms} ms</TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={0.5} useFlexGap sx={{ flexWrap: "wrap" }}>
                      {step.tools.map((tool) => <Chip key={tool} size="small" variant="outlined" label={tool} />)}
                      {step.error ? step.error : null}
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
