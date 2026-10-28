import { Alert, Card, CardContent, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { HorizontalBars } from "../charts/Bars";
import { PageTitle, QueryState } from "../components/State";
import { useDatasetId } from "../hooks/useDataset";
import { getJson, npsText } from "../services/api";

interface Example {
  response_id: string;
  comment: string;
  score: number;
}
interface Theme {
  theme: string;
  comments: number;
  nps: number | null;
  detractors: number;
  promoters: number;
  detraction_change?: number | null;
  detractor_change: number | null;
  negative_examples: Example[];
  positive_examples: Example[];
}

export function VoicePage() {
  const datasetId = useDatasetId();
  const query = useQuery({
    queryKey: ["themes", datasetId],
    queryFn: () => getJson<{ themes: Theme[]; association: { statement: string } }>(`/api/themes/${datasetId}`),
    enabled: Boolean(datasetId),
  });
  return (
    <>
      <PageTitle title="Voice of customer" subtitle="Themes come from a keyword baseline. Quotes are copied from the survey." />
      <QueryState loading={query.isLoading} error={query.error} empty={!datasetId}>
        {query.data ? (
          <Stack spacing={2}>
            <Alert severity="info">{query.data.association.statement}</Alert>
            <HorizontalBars rows={query.data.themes.filter((theme) => theme.theme !== "UNCLEAR").map((theme) => ({ name: theme.theme, value: theme.comments }))} />
            {query.data.themes.filter((theme) => theme.theme !== "UNCLEAR").map((theme) => (
              <Card key={theme.theme} variant="outlined">
                <CardContent>
                  <Typography variant="h6">{theme.theme}</Typography>
                  <Typography color="text.secondary">
                    {theme.comments} comments · NPS {npsText(theme.nps)} · detractors {theme.detractors} · promoters {theme.promoters} · detractor change {theme.detractor_change ?? "—"}
                  </Typography>
                  {[...theme.negative_examples, ...theme.positive_examples].map((example) => (
                    <Typography key={example.response_id} sx={{ mt: 1 }}>
                      “{example.comment}” — {example.response_id}, score {example.score}
                    </Typography>
                  ))}
                </CardContent>
              </Card>
            ))}
          </Stack>
        ) : null}
      </QueryState>
    </>
  );
}
