import { Alert, Button, Card, CardContent, Stack, Typography } from "@mui/material";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiGet, apiPatch, apiPost } from "../services/api";
import type { AdvisorAnswer, Recommendation } from "../types";
import { formatMoney } from "../utils/format";

const statuses = ["OPEN", "REVIEWED", "DISMISSED", "IMPLEMENTED"] as const;

export function RecommendationDetailPage() {
  const { recommendationId = "" } = useParams();
  const queryClient = useQueryClient();
  const [explanation, setExplanation] = useState<AdvisorAnswer | null>(null);
  const recommendation = useQuery({
    queryKey: ["recommendation", recommendationId],
    queryFn: () => apiGet<Recommendation & { currency?: string }>(`/api/recommendations/${recommendationId}`),
    enabled: Boolean(recommendationId),
  });

  async function setStatus(status: string) {
    await apiPatch(`/api/recommendations/${recommendationId}`, { status });
    await queryClient.invalidateQueries({ queryKey: ["recommendation", recommendationId] });
  }

  async function explain() {
    setExplanation(await apiPost<AdvisorAnswer>("/api/ai/explain", { recommendation_id: Number(recommendationId) }));
  }

  const item = recommendation.data;
  return (
    <Stack spacing={2}>
      <Typography variant="body2">
        <Link to="/">Dashboard</Link>
      </Typography>
      {recommendation.isError ? <Alert severity="error">{recommendation.error.message}</Alert> : null}
      {item ? (
        <Card>
          <CardContent>
            <Typography variant="h5">{item.title}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              {item.service} · {item.resource_id || "Account"} · {item.status}
            </Typography>
            <Typography variant="body1" sx={{ mt: 2 }}>
              {item.client_brief || item.description}
            </Typography>
            <Typography variant="body2" sx={{ mt: 2 }}>
              Current {formatMoney(item.current_monthly_cost, item.currency || "USD")} · Estimated potential savings{" "}
              {formatMoney(item.estimated_monthly_savings, item.currency || "USD")} / month
            </Typography>
            <Typography variant="body2" sx={{ mt: 2 }}>
              {item.evidence_summary}
            </Typography>
            {item.assumptions.map((line) => (
              <Typography key={line} variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                {line}
              </Typography>
            ))}
            {(item.next_steps ?? []).map((step) => (
              <Typography key={step} variant="body2" sx={{ mt: 0.5 }}>
                {step}
              </Typography>
            ))}
            <Stack direction="row" spacing={1} sx={{ mt: 2 }} useFlexGap flexWrap="wrap">
              {statuses.map((status) => (
                <Button key={status} size="small" variant={item.status === status ? "contained" : "outlined"} onClick={() => void setStatus(status)}>
                  {status}
                </Button>
              ))}
              <Button size="small" onClick={() => void explain()}>
                Explain
              </Button>
            </Stack>
            {explanation ? (
              <Typography variant="body2" sx={{ mt: 2 }}>
                {explanation.narrative}
              </Typography>
            ) : null}
          </CardContent>
        </Card>
      ) : null}
    </Stack>
  );
}
