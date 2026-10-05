import { Card, CardContent, Typography } from "@mui/material";

type KpiCardProps = {
  label: string;
  value: string;
  caption: string;
  tone?: "default" | "savings" | "increase";
};

const tones = {
  default: "#172033",
  savings: "#0f7b4c",
  increase: "#9a3412",
};

export function KpiCard({ label, value, caption, tone = "default" }: KpiCardProps) {
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent>
        <Typography variant="overline" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="h5" sx={{ fontWeight: 700, color: tones[tone], my: 0.5 }}>
          {value}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {caption}
        </Typography>
      </CardContent>
    </Card>
  );
}
