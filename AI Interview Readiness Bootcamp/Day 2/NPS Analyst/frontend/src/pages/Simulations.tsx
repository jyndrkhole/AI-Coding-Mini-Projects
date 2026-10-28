import { Alert, Button, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { useMutation, useQuery } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { PageTitle, QueryState } from "../components/State";
import { useDatasetId } from "../hooks/useDataset";
import { getJson, npsText, postJson } from "../services/api";

interface Result {
  current_nps: number | null;
  simulated_nps: number | null;
  delta: number | null;
  affected_response_count: number;
  assumptions: string[];
  caveats: string[];
}

export function SimulationsPage() {
  const datasetId = useDatasetId();
  const themes = useQuery({
    queryKey: ["themes", datasetId],
    queryFn: () => getJson<{ themes: { theme: string }[] }>(`/api/themes/${datasetId}`),
    enabled: Boolean(datasetId),
  });
  const [theme, setTheme] = useState("OTP_AND_LOGIN");
  const [scenario, setScenario] = useState("A");
  const [proportion, setProportion] = useState(1);
  const simulation = useMutation({
    mutationFn: () => postJson<Result>("/api/simulations/fix-impact", { dataset_id: datasetId, theme, scenario, proportion, score_delta: 2 }),
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    simulation.mutate();
  }
  return (
    <>
      <PageTitle title="Fix-impact simulation" subtitle="A hypothetical score change. It does not forecast what customers will do, and it does not edit the survey." />
      <QueryState loading={themes.isLoading} error={themes.error} empty={!datasetId}>
        <Stack component="form" spacing={2} onSubmit={submit} sx={{ maxWidth: 520 }}>
          <TextField select label="Theme" value={theme} onChange={(event) => setTheme(event.target.value)}>
            {(themes.data?.themes || []).filter((row) => row.theme !== "UNCLEAR").map((row) => (
              <MenuItem key={row.theme} value={row.theme}>{row.theme}</MenuItem>
            ))}
          </TextField>
          <TextField select label="Scenario" value={scenario} onChange={(event) => setScenario(event.target.value)}>
            <MenuItem value="A">A · selected detractors become passives</MenuItem>
            <MenuItem value="B">B · selected detractors become promoters</MenuItem>
            <MenuItem value="C">C · a proportion improves by 2 points</MenuItem>
          </TextField>
          {scenario === "C" ? (
            <TextField label="Proportion" type="number" inputProps={{ min: 0, max: 1, step: 0.1 }} value={proportion} onChange={(event) => setProportion(Number(event.target.value))} />
          ) : null}
          <Button type="submit" variant="contained" disabled={simulation.isPending}>Run simulation</Button>
          {simulation.error ? <Alert severity="error">{simulation.error.message}</Alert> : null}
          {simulation.data ? (
            <Stack spacing={1}>
              <Typography>Current NPS {npsText(simulation.data.current_nps)}</Typography>
              <Typography>Simulated NPS {npsText(simulation.data.simulated_nps)}</Typography>
              <Typography>Delta {npsText(simulation.data.delta)}</Typography>
              <Typography>Affected responses {simulation.data.affected_response_count}</Typography>
              {simulation.data.assumptions.map((line) => <Alert key={line} severity="info">{line}</Alert>)}
              {simulation.data.caveats.map((line) => <Alert key={line} severity="warning">{line}</Alert>)}
            </Stack>
          ) : null}
        </Stack>
      </QueryState>
    </>
  );
}
