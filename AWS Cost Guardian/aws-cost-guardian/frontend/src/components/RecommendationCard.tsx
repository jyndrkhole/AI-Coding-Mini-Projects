import { Box, Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import { Link } from "react-router-dom";
import type { Recommendation } from "../types";
import { formatMoney, sourceLabel } from "../utils/format";

const riskColor = {
  LOW: "success",
  MEDIUM: "warning",
  HIGH: "error",
} as const;

export function RecommendationCard({ item, currency }: { item: Recommendation; currency: string }) {
  const color = riskColor[item.risk_level as keyof typeof riskColor] ?? "default";
  const quoted = item.estimated_monthly_savings > 0;
  const steps = item.next_steps ?? [];
  return (
    <Card>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" spacing={1} alignItems="flex-start">
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            <Link to={`/recommendations/${item.id}`}>{item.title}</Link>
          </Typography>
          <Chip size="small" label={item.service} variant="outlined" />
        </Stack>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          {item.resource_id ?? "Account"}
        </Typography>
        <Stack direction="row" spacing={3} sx={{ mt: 1.5 }}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              {item.category === "architecture" ? "Last full month" : "Investigate"}
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              {formatMoney(item.current_monthly_cost, currency)}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              {quoted ? "Ceiling" : "Quoted saving"}
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 700, color: quoted ? "secondary.main" : "text.secondary" }}>
              {quoted ? `${formatMoney(item.estimated_monthly_savings, currency)}/month` : "Not estimated"}
            </Typography>
          </Box>
        </Stack>
        {item.client_brief ? (
          <Box sx={{ mt: 1.5 }}>
            <Typography variant="caption" color="text.secondary">
              Tell the client
            </Typography>
            <Typography variant="body2">{item.client_brief}</Typography>
          </Box>
        ) : (
          <Typography variant="body2" sx={{ mt: 1.5 }}>
            {item.evidence_summary}
          </Typography>
        )}
        {item.client_ask ? (
          <Box sx={{ mt: 1.5 }}>
            <Typography variant="caption" color="text.secondary">
              Ask the client
            </Typography>
            <Typography variant="body2">{item.client_ask}</Typography>
          </Box>
        ) : null}
        {steps.length > 0 ? (
          <Box sx={{ mt: 1.5 }}>
            <Typography variant="caption" color="text.secondary">
              Your next steps
            </Typography>
            <Box component="ol" sx={{ m: 0, pl: 2.25 }}>
              {steps.map((step) => (
                <Typography key={step} component="li" variant="body2" sx={{ mt: 0.5 }}>
                  {step}
                </Typography>
              ))}
            </Box>
          </Box>
        ) : null}
        {item.assumptions[0] ? (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
            {item.assumptions[0]}
          </Typography>
        ) : null}
        <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 1.5 }}>
          <Chip size="small" color={color} label={`Risk ${item.risk_level}`} />
          <Chip size="small" variant="outlined" label={`Confidence ${item.confidence}`} />
          <Chip size="small" variant="outlined" label={sourceLabel(item.source)} />
        </Stack>
      </CardContent>
    </Card>
  );
}
