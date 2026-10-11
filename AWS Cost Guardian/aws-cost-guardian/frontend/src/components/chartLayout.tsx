import { useTheme } from "@mui/material/styles";

export function useChartColors() {
  const theme = useTheme();
  return {
    grid: theme.palette.divider,
    primary: theme.palette.primary.main,
    secondary: theme.palette.secondary.main,
    area: theme.palette.mode === "dark" ? "rgba(143, 184, 214, 0.22)" : "#d5e4f2",
  };
}

export function useChartTooltip() {
  const theme = useTheme();
  const text = theme.palette.text.primary;
  return {
    contentStyle: {
      backgroundColor: theme.palette.background.paper,
      border: `1px solid ${theme.palette.divider}`,
      borderRadius: 8,
      color: text,
    },
    labelStyle: { color: text, fontWeight: 600 },
    itemStyle: { color: text },
  };
}

export function useValueTones() {
  const theme = useTheme();
  return {
    neutral: theme.palette.text.primary,
    savings: theme.palette.secondary.main,
    increase: theme.palette.mode === "dark" ? "#f4b183" : "#9a3412",
  };
}

export function categoryChartHeight(count: number): number {
  return Math.max(220, count * 40);
}

export function shortenAxisLabel(value: string, max = 26): string {
  if (value.length <= max) return value;
  return `${value.slice(0, max - 1)}…`;
}

export function zeroValueAxis(values: number[]): { domain?: [number, number]; ticks?: number[] } {
  const max = values.reduce((highest, value) => Math.max(highest, value), 0);
  if (max === 0) return { domain: [0, 1], ticks: [0] };
  return {};
}

type CategoryTickProps = {
  x?: number;
  y?: number;
  payload?: { value?: string };
};

export function CategoryTick({ x = 0, y = 0, payload }: CategoryTickProps) {
  const theme = useTheme();
  return (
    <text x={x} y={y} dy={4} textAnchor="end" fill={theme.palette.text.secondary} fontSize={11}>
      {shortenAxisLabel(String(payload?.value ?? ""))}
    </text>
  );
}
