import { Card, CardContent, Typography } from "@mui/material";
import { useValueTones } from "./chartLayout";

type KpiCardProps = {
  label: string;
  value: string;
  caption: string;
  tone?: "default" | "savings" | "increase";
};

export function KpiCard({ label, value, caption, tone = "default" }: KpiCardProps) {
  const tones = useValueTones();
  const color = tone === "default" ? tones.neutral : tones[tone];
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent>
        <Typography variant="overline" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="h5" sx={{ fontWeight: 700, color, my: 0.5 }}>
          {value}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {caption}
        </Typography>
      </CardContent>
    </Card>
  );
}
