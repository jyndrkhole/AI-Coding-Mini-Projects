import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  MenuItem,
  Skeleton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { categoryChartHeight, CategoryTick, useChartColors, zeroValueAxis } from "../components/chartLayout";
import { apiGet, apiPost } from "../services/api";
import type { CostExplorer, ScanResult } from "../types";
import { formatCompactMoney, formatPercent } from "../utils/format";

type Filters = { start: string; end: string; service: string; region: string };

const emptyFilters: Filters = { start: "", end: "", service: "", region: "" };

function formatAmount(value: number, currency: string): string {
  return new Intl.NumberFormat(currency === "INR" ? "en-IN" : "en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: Number.isInteger(value) ? 0 : 2,
  }).format(value);
}

function formatSignedAmount(value: number, currency: string): string {
  const formatted = formatAmount(Math.abs(value), currency);
  if (value > 0) return `+${formatted}`;
  if (value < 0) return `-${formatted}`;
  return formatted;
}

export function CostExplorerPage() {
  const chart = useChartColors();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<Filters>(emptyFilters);
  const [applied, setApplied] = useState<Filters>(emptyFilters);
  const explorer = useQuery({
    queryKey: ["costs", "explorer", applied],
    queryFn: () => apiGet<CostExplorer>(`/api/costs/explorer${queryString(applied)}`),
  });
  const scan = useMutation({
    mutationFn: () => apiPost<ScanResult>("/api/aws/scan"),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["costs"] });
      await queryClient.invalidateQueries({ queryKey: ["account"] });
    },
  });

  const data = explorer.data;
  const filters = draft.start ? draft : data ? { start: data.start, end: data.end, service: "", region: "" } : emptyFilters;

  return (
    <Stack spacing={3}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" spacing={2}>
        <Box>
          <Typography variant="h4">Cost Explorer</Typography>
          <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 720, mt: 0.5 }}>
            {data
              ? `${data.source_label} unblended cost for ${data.current_period_label} compared with ${data.previous_period_label}.`
              : "Unblended cost by day, month, service, region, and usage type."}
          </Typography>
        </Box>
        <Button variant="contained" onClick={() => scan.mutate()} disabled={scan.isPending}>
          {scan.isPending ? "Refreshing" : "Refresh costs"}
        </Button>
      </Stack>

      {explorer.isError ? <Alert severity="error">{explorer.error.message}</Alert> : null}
      {scan.isError ? <Alert severity="error">{scan.error.message}</Alert> : null}
      {scan.data ? <ScanAlert result={scan.data} /> : null}

      <Card>
        <CardContent>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems={{ md: "center" }}>
            <TextField
              label="Start"
              type="date"
              size="small"
              value={filters.start}
              onChange={(event) => setDraft({ ...filters, start: event.target.value })}
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              label="End"
              type="date"
              size="small"
              value={filters.end}
              onChange={(event) => setDraft({ ...filters, end: event.target.value })}
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              label="Service"
              select
              size="small"
              value={filters.service}
              onChange={(event) => setDraft({ ...filters, service: event.target.value })}
              sx={{ minWidth: 180 }}
            >
              <MenuItem value="">All services</MenuItem>
              {(data?.available_services ?? []).map((service) => (
                <MenuItem key={service} value={service}>
                  {service}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Region"
              select
              size="small"
              value={filters.region}
              onChange={(event) => setDraft({ ...filters, region: event.target.value })}
              sx={{ minWidth: 180 }}
            >
              <MenuItem value="">All regions</MenuItem>
              {(data?.available_regions ?? []).map((region) => (
                <MenuItem key={region} value={region}>
                  {region}
                </MenuItem>
              ))}
            </TextField>
            <Button
              variant="outlined"
              onClick={() => {
                setDraft(filters);
                setApplied(filters);
              }}
            >
              Apply
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {explorer.isLoading ? <Skeleton variant="rounded" height={280} /> : null}

      {data ? (
        <>
          {data.daily_note ? <Alert severity="info">{data.daily_note}</Alert> : null}
          <Alert severity="info">{data.monthly_note}</Alert>
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", xl: "1.2fr 1fr" } }}>
            <ChartCard title="Daily cost">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={data.daily} margin={{ right: 8, bottom: 8 }}>
                  <CartesianGrid stroke={chart.grid} vertical={false} />
                  <XAxis dataKey="date" minTickGap={32} tickFormatter={(value: string) => value.slice(8)} tick={{ fontSize: 12 }} />
                  <YAxis
                    tickFormatter={(value: number) => formatCompactMoney(value, data.currency)}
                    width={72}
                    tick={{ fontSize: 12 }}
                    {...zeroValueAxis(data.daily.map((point) => point.amount))}
                  />
                  <Tooltip formatter={(value) => formatAmount(Number(value ?? 0), data.currency)} />
                  <Bar dataKey="amount" fill={chart.primary} isAnimationActive={false} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Monthly cost">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={data.monthly} margin={{ bottom: 24, right: 8 }}>
                  <CartesianGrid stroke={chart.grid} vertical={false} />
                  <XAxis dataKey="label" interval={0} tick={{ fontSize: 12 }} height={36} />
                  <YAxis
                    tickFormatter={(value: number) => formatCompactMoney(value, data.currency)}
                    width={72}
                    tick={{ fontSize: 12 }}
                    {...zeroValueAxis(data.monthly.map((point) => point.amount))}
                  />
                  <Tooltip formatter={(value) => formatAmount(Number(value ?? 0), data.currency)} />
                  <Bar dataKey="amount" fill={chart.secondary} isAnimationActive={false} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </Box>
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" } }}>
            <ChartCard title="Service distribution">
              <ResponsiveContainer width="100%" height={categoryChartHeight(data.services.length)}>
                <BarChart data={data.services} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
                  <CartesianGrid stroke={chart.grid} horizontal={false} />
                  <XAxis
                    type="number"
                    tickFormatter={(value: number) => formatCompactMoney(value, data.currency)}
                    tick={{ fontSize: 12 }}
                    {...zeroValueAxis(data.services.map((row) => row.current))}
                  />
                  <YAxis
                    type="category"
                    dataKey="service"
                    width={188}
                    interval={0}
                    tick={<CategoryTick />}
                  />
                  <Tooltip
                    formatter={(value) => formatAmount(Number(value ?? 0), data.currency)}
                    labelFormatter={(label) => String(label)}
                  />
                  <Bar dataKey="current" fill={chart.primary} isAnimationActive={false} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Regional distribution">
              <ResponsiveContainer width="100%" height={280}>
                <BarChart
                  data={data.regions.filter((row) => row.current !== 0 || row.previous !== 0)}
                  margin={{ bottom: 28, right: 8 }}
                >
                  <CartesianGrid stroke={chart.grid} vertical={false} />
                  <XAxis dataKey="region" interval={0} angle={-28} textAnchor="end" height={52} tick={{ fontSize: 11 }} />
                  <YAxis
                    tickFormatter={(value: number) => formatCompactMoney(value, data.currency)}
                    width={72}
                    tick={{ fontSize: 12 }}
                    {...zeroValueAxis(data.regions.map((row) => row.current))}
                  />
                  <Tooltip formatter={(value) => formatAmount(Number(value ?? 0), data.currency)} />
                  <Bar dataKey="current" fill={chart.secondary} isAnimationActive={false} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </Box>

          <Typography variant="h6">Service breakdown</Typography>
          <ComparisonTable
            rows={data.services.map((row) => ({
              name: row.service,
              current: row.current,
              previous: row.previous,
              change: row.change,
              changePercent: row.change_percent,
            }))}
            nameHeader="Service"
            currentLabel={data.current_period_label}
            previousLabel={data.previous_period_label}
            currency={data.currency}
          />

          <Typography variant="h6">Usage types</Typography>
          {data.pricing_note ? (
            <Typography variant="body2" color="text.secondary">
              {data.pricing_note}
            </Typography>
          ) : null}
          <Card>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Service</TableCell>
                  <TableCell>Usage type</TableCell>
                  <TableCell align="right">{data.current_period_label}</TableCell>
                  <TableCell align="right">{data.previous_period_label}</TableCell>
                  <TableCell align="right">Change</TableCell>
                  <TableCell>Price</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.usage_types.map((row) => (
                  <TableRow key={`${row.service}-${row.usage_type}`}>
                    <TableCell>{row.service}</TableCell>
                    <TableCell>{row.usage_type}</TableCell>
                    <TableCell align="right">{formatAmount(row.current, data.currency)}</TableCell>
                    <TableCell align="right">{formatAmount(row.previous, data.currency)}</TableCell>
                    <TableCell align="right">
                      {formatSignedAmount(row.change, data.currency)} ({formatPercent(row.change_percent)})
                    </TableCell>
                    <TableCell>{row.pricing_available ? "Calculated" : "Not calculated"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </>
      ) : null}
    </Stack>
  );
}

function queryString(filters: Filters): string {
  const params = new URLSearchParams();
  if (filters.start) params.set("start", filters.start);
  if (filters.end) params.set("end", filters.end);
  if (filters.service) params.set("service", filters.service);
  if (filters.region) params.set("region", filters.region);
  const value = params.toString();
  return value ? `?${value}` : "";
}

function ScanAlert({ result }: { result: ScanResult }) {
  const cost = result.steps.find((step) => step.service === "cost_explorer");
  const severity = result.status === "completed" ? "success" : "warning";
  return <Alert severity={severity}>{cost?.detail || cost?.error || "Cost refresh finished."}</Alert>;
}

function ChartCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card>
      <CardContent>
        <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>
          {title}
        </Typography>
        {children}
      </CardContent>
    </Card>
  );
}

function ComparisonTable({
  rows,
  nameHeader,
  currentLabel,
  previousLabel,
  currency,
}: {
  rows: { name: string; current: number; previous: number; change: number; changePercent: number | null }[];
  nameHeader: string;
  currentLabel: string;
  previousLabel: string;
  currency: string;
}) {
  return (
    <Card>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>{nameHeader}</TableCell>
            <TableCell align="right">{currentLabel}</TableCell>
            <TableCell align="right">{previousLabel}</TableCell>
            <TableCell align="right">Change</TableCell>
            <TableCell align="right">Percentage</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={row.name}>
              <TableCell>{row.name}</TableCell>
              <TableCell align="right">{formatAmount(row.current, currency)}</TableCell>
              <TableCell align="right">{formatAmount(row.previous, currency)}</TableCell>
              <TableCell align="right">{formatSignedAmount(row.change, currency)}</TableCell>
              <TableCell align="right">{formatPercent(row.changePercent)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}
