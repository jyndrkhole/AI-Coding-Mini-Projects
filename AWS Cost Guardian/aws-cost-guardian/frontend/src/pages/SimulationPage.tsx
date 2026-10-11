import { Alert, Button, Card, CardContent, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { useState } from "react";
import { apiPost } from "../services/api";
import type { SimulationResult } from "../types";
import { formatMoney } from "../utils/format";

export function SimulationPage() {
  const [hours, setHours] = useState("12");
  const [environment, setEnvironment] = useState("dev");
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setError(null);
    try {
      setResult(
        await apiPost<SimulationResult>("/api/simulation", {
          scenario_type: "business_hours",
          hours_per_weekday: Number(hours),
          environment,
        }),
      );
    } catch (caught) {
      setResult(null);
      setError(caught instanceof Error ? caught.message : "The simulation could not run.");
    }
  }

  return (
    <Stack spacing={2}>
      <Typography variant="h4">What-if simulation</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 720 }}>
        Estimate a business-hours schedule for development instances that already have a stored monthly cost. Instances
        without a stored cost are left out.
      </Typography>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
        <TextField select label="Environment" value={environment} onChange={(event) => setEnvironment(event.target.value)}>
          <MenuItem value="dev">dev</MenuItem>
          <MenuItem value="development">development</MenuItem>
        </TextField>
        <TextField label="Hours per weekday" value={hours} onChange={(event) => setHours(event.target.value)} />
      </Stack>
      <Button variant="contained" onClick={() => void run()} sx={{ alignSelf: "flex-start" }}>
        Estimate
      </Button>
      {error ? <Alert severity="error">{error}</Alert> : null}
      {result ? (
        <Card>
          <CardContent>
            <Typography variant="overline">{result.label}</Typography>
            <Typography variant="body2" sx={{ mt: 1 }}>
              Current {formatMoney(result.current_monthly_cost, result.currency)} · Projected{" "}
              {formatMoney(result.projected_monthly_cost, result.currency)}
            </Typography>
            <Typography variant="body2">
              Estimated potential savings {formatMoney(result.potential_monthly_savings, result.currency)} / month (
              {formatMoney(result.potential_annual_savings, result.currency)} / year)
            </Typography>
            <Typography variant="body2" sx={{ mt: 1 }}>
              Included: {result.included_resources.join(", ") || "none"}
            </Typography>
            {result.excluded_resources.length > 0 ? (
              <Typography variant="body2">Excluded, no stored cost: {result.excluded_resources.join(", ")}</Typography>
            ) : null}
            {result.assumptions.map((line) => (
              <Typography key={line} variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                {line}
              </Typography>
            ))}
          </CardContent>
        </Card>
      ) : null}
    </Stack>
  );
}
