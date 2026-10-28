import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function NpsTrend({ rows }: { rows: { label?: string; month: string; nps: number | null }[] }) {
  const data = rows.map((row) => ({ name: row.label || row.month, nps: row.nps }));
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data}>
        <CartesianGrid stroke="#e6ebf2" />
        <XAxis dataKey="name" />
        <YAxis domain={[-100, 100]} />
        <Tooltip />
        <Line type="monotone" dataKey="nps" stroke="#10233f" strokeWidth={2.5} dot={{ r: 4 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
