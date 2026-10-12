import { Alert, Button, Card, CardContent, Stack, Typography } from "@mui/material";
import { useState } from "react";
import { PageHeaderAction, usePageHeader } from "../layouts/pageHeader";
import { apiGet, apiPost } from "../services/api";
import type { MonthlyReport } from "../types";

export function ReportPage() {
  const [report, setReport] = useState<MonthlyReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setError(null);
    try {
      setReport(await apiGet<MonthlyReport>("/api/reports/monthly"));
    } catch (caught) {
      setReport(null);
      setError(caught instanceof Error ? caught.message : "No report is stored.");
    }
  }

  async function generate() {
    setError(null);
    try {
      setReport(await apiPost<MonthlyReport>("/api/reports/monthly"));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The report could not be generated.");
    }
  }

  usePageHeader("Monthly report", "The report repeats stored costs and recommendations. PDF export is not generated yet.");

  return (
    <Stack spacing={2}>
      <PageHeaderAction>
        <Button size="small" variant="outlined" onClick={() => void load()}>
          Open latest
        </Button>
        <Button size="small" variant="contained" onClick={() => void generate()}>
          Generate
        </Button>
      </PageHeaderAction>
      {error ? <Alert severity="info">{error}</Alert> : null}
      {report ? (
        <Card>
          <CardContent>
            <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>
              {report.report_month}
            </Typography>
            <div dangerouslySetInnerHTML={{ __html: report.html }} />
          </CardContent>
        </Card>
      ) : null}
    </Stack>
  );
}
