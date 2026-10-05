import { Box, Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import type { Recommendation } from "../types";
import { formatMoney, sourceLabel } from "../utils/format";

const riskColor = {
  LOW: "success",
  MEDIUM: "warning",
  HIGH: "error",
} as const;

export function RecommendationCard({ item, currency }: { item: Recommendation; currency: string }) {
  const color = riskColor[item.risk_level as keyof typeof riskColor] ?? "default";
  return (
    <Card>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" spacing={1} alignItems="flex-start">
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            {item.title}
          </Typography>
          <Chip size="small" label={item.service} variant="outlined" />
        </Stack>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Resource {item.resource_id ?? "Account"}
        </Typography>
        <Stack direction="row" spacing={3} sx={{ mt: 1.5 }}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Current
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              {formatMoney(item.current_monthly_cost, currency)}/month
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Potential
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 700, color: "secondary.main" }}>
              {formatMoney(item.estimated_monthly_savings, currency)}/month
            </Typography>
          </Box>
        </Stack>
        <Typography variant="body2" sx={{ mt: 1.5 }}>
          {item.evidence_summary}
        </Typography>
        {item.assumptions[0] ? (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Assumption: {item.assumptions[0]}
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
