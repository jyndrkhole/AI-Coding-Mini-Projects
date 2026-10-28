import { Chip, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { PageTitle, QueryState } from "../components/State";
import { useDatasetId } from "../hooks/useDataset";
import { getJson } from "../services/api";

interface Issue {
  response_id: string | null;
  issue_type: string;
  severity: string;
  evidence: { score?: number; comment?: string };
}

export function QualityPage() {
  const datasetId = useDatasetId();
  const query = useQuery({
    queryKey: ["quality", datasetId],
    queryFn: () => getJson<{ total_issues: number; by_type: Record<string, number>; note: string; issues: Issue[]; contradiction_count: number }>(`/api/data-quality/${datasetId}`),
    enabled: Boolean(datasetId),
  });
  const contradictions = (query.data?.issues || []).filter((issue) => issue.issue_type === "POSSIBLE_SCORE_INTERPRETATION_ERROR");
  return (
    <>
      <PageTitle title="Data quality" subtitle="Contradictory scores stay as recorded. They are flagged for a person to review." />
      <QueryState loading={query.isLoading} error={query.error} empty={!datasetId}>
        {query.data ? (
          <Stack spacing={2}>
            <Typography>{query.data.note} {query.data.total_issues} issues, including {query.data.contradiction_count} score/comment contradictions.</Typography>
            <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap" }}>
              {Object.entries(query.data.by_type).map(([name, count]) => <Chip key={name} label={`${name}: ${count}`} />)}
            </Stack>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Response</TableCell>
                  <TableCell>Score</TableCell>
                  <TableCell>Comment</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {contradictions.map((issue) => (
                  <TableRow key={`${issue.response_id}-${issue.evidence.comment}`}>
                    <TableCell>{issue.response_id}</TableCell>
                    <TableCell>{issue.evidence.score}</TableCell>
                    <TableCell>{issue.evidence.comment}</TableCell>
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
