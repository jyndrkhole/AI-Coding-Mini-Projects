import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function HorizontalBars({ rows, color = "#1f7a4d" }: { rows: { name: string; value: number }[]; color?: string }) {
  return (
    <ResponsiveContainer width="100%" height={Math.max(220, rows.length * 42)}>
      <BarChart data={rows} layout="vertical" margin={{ left: 24 }}>
        <CartesianGrid stroke="#e6ebf2" />
        <XAxis type="number" />
        <YAxis type="category" dataKey="name" width={140} />
        <Tooltip />
        <Bar dataKey="value" fill={color} radius={4} />
      </BarChart>
    </ResponsiveContainer>
  );
}
