import { Card, CardContent, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useValueTones } from "./chartLayout";

type KpiCardProps = {
  label: string;
  value: string;
  caption: string;
  tone?: "default" | "savings" | "increase";
};

export function KpiCard({ label, value, caption, tone = "default" }: KpiCardProps) {
  const theme = useTheme();
  const tones = useValueTones();
  const accent = tone === "default" ? theme.palette.primary.main : tones[tone];
  return (
    <Card
      sx={{
        height: "100%",
        borderTop: "3px solid",
        borderTopColor: accent,
        background: `linear-gradient(180deg, ${accent}24 0%, ${theme.palette.background.paper} 46%)`,
      }}
    >
      <CardContent sx={{ px: 1.75, py: 1.5, "&:last-child": { pb: 1.5 } }}>
        <Typography variant="caption" sx={{ display: "block", fontWeight: 700, letterSpacing: "0.06em", lineHeight: 1.3, textTransform: "uppercase", color: accent }}>
          {label}
        </Typography>
        <Typography variant="h6" sx={{ fontWeight: 700, color: tone === "default" ? tones.neutral : accent, mt: 0.5, lineHeight: 1.2 }}>
          {value}
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
          {caption}
        </Typography>
      </CardContent>
    </Card>
  );
}
