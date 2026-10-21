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
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { categoryChartHeight, CategoryTick, useChartColors, useChartTooltip, zeroValueAxis } from "../components/chartLayout";
import { PageHeaderAction, usePageHeader } from "../layouts/pageHeader";
import { apiGet, apiPost } from "../services/api";
import type { CostExplorer, LinkedAccountCost, ScanResult } from "../types";
import { formatCompactMoney, formatPercent } from "../utils/format";

type Filters = { start: string; end: string; service: string; region: string; linked_account: string };

const emptyFilters: Filters = { start: "", end: "", service: "", region: "", linked_account: "" };

function withVisibleDates(filters: Filters, data?: CostExplorer): Filters {
  if (filters.start || !data) return filters;
  return { ...filters, start: data.start, end: data.end };
}

function accountOptionLabel(row: LinkedAccountCost): string {
  if (row.is_this_login) return `This account · ${row.account_name || row.account_id}`;
  return row.account_name ? `${row.account_name} · ${row.account_id}` : row.account_id;
}

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
  const tooltip = useChartTooltip();
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const explorer = useQuery({
    queryKey: ["costs", "explorer", filters],
    queryFn: () => apiGet<CostExplorer>(`/api/costs/explorer${queryString(filters)}`),
    placeholderData: keepPreviousData,
  });
  const scan = useMutation({
    mutationFn: () => apiPost<ScanResult>("/api/aws/scan?include_inventory=false"),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["costs"] });
      await queryClient.invalidateQueries({ queryKey: ["account"] });
    },
  });

  const data = explorer.data;
  const visible = withVisibleDates(filters, data);
  const serviceRows =
    data && visible.service && !visible.linked_account
      ? data.services.filter((row) => row.service === visible.service)
      : data?.services ?? [];
  const regionRows = data && visible.region ? data.regions.filter((row) => row.region === visible.region) : data?.regions ?? [];
  const usageRows =
    data && visible.service && !visible.linked_account
      ? data.usage_types.filter((row) => row.service === visible.service)
      : data?.usage_types ?? [];
  function patch(update: Partial<Filters>) {
    setFilters((current) => ({ ...withVisibleDates(current, data), ...update }));
  }
  usePageHeader(
    "Cost Explorer",
    data
      ? `${data.source_label} unblended cost for ${data.current_period_label} compared with ${data.previous_period_label}.`
      : "Unblended cost by day, month, service, region, and usage type.",
  );

  return (
    <Stack spacing={3}>
      <PageHeaderAction>
        <Button size="small" variant="contained" onClick={() => scan.mutate()} disabled={scan.isPending}>
          {scan.isPending ? "Refreshing" : "Refresh costs"}
        </Button>
      </PageHeaderAction>

      {explorer.isError ? <Alert severity="error">{explorer.error.message}</Alert> : null}
      {scan.isError ? <Alert severity="error">{scan.error.message}</Alert> : null}
      {scan.data ? <ScanAlert result={scan.data} /> : null}

      <Card>
        <CardContent>
          <Stack direction="row" flexWrap="wrap" useFlexGap spacing={2} alignItems="center">
            <TextField
              label="Start"
              type="date"
              size="small"
              value={visible.start}
              onChange={(event) => patch({ start: event.target.value })}
              InputLabelProps={{ shrink: true }}
              sx={{ minWidth: 160 }}
            />
            <TextField
              label="End"
              type="date"
              size="small"
              value={visible.end}
              onChange={(event) => patch({ end: event.target.value })}
              InputLabelProps={{ shrink: true }}
              sx={{ minWidth: 160 }}
            />
            <TextField
              label="Service"
              select
              size="small"
              value={visible.service}
              onChange={(event) => patch({ service: event.target.value })}
              sx={{ minWidth: 220, flex: "1 1 220px" }}
              InputLabelProps={{ shrink: true }}
              SelectProps={{ displayEmpty: true }}
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
              value={visible.region}
              onChange={(event) => patch({ region: event.target.value })}
              sx={{ minWidth: 180, flex: "1 1 180px" }}
              InputLabelProps={{ shrink: true }}
              SelectProps={{ displayEmpty: true }}
            >
              <MenuItem value="">All regions</MenuItem>
              {(data?.available_regions ?? []).map((region) => (
                <MenuItem key={region} value={region}>
                  {region}
                </MenuItem>
              ))}
            </TextField>
            {(data?.linked_accounts ?? []).length > 1 ? (
              <TextField
                label="Account"
                select
                size="small"
                value={visible.linked_account}
                onChange={(event) => patch({ linked_account: event.target.value })}
                sx={{ minWidth: 240, flex: "1 1 240px" }}
                InputLabelProps={{ shrink: true }}
                SelectProps={{ displayEmpty: true }}
              >
                <MenuItem value="">All accounts</MenuItem>
                {(data?.linked_accounts ?? []).map((row) => (
                  <MenuItem key={row.account_id} value={row.account_id}>
                    {accountOptionLabel(row)}
                  </MenuItem>
                ))}
              </TextField>
            ) : null}
            <Button variant="outlined" onClick={() => setFilters(visible)}>
              Apply
            </Button>
            <Button variant="contained" onClick={() => scan.mutate()} disabled={scan.isPending}>
              {scan.isPending ? "Refreshing" : "Refresh costs"}
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {explorer.isLoading ? <Skeleton variant="rounded" height={280} /> : null}

      {data ? (
        <>
          {visible.service || visible.linked_account || visible.region ? (
            <Alert severity="success">
              Showing {visible.service || "all services"}
              {visible.linked_account ? ` for account ${visible.linked_account}` : " across accounts"}
              {visible.region ? ` in ${visible.region}` : ""}.
            </Alert>
          ) : null}
          {data.account_note ? <Alert severity="info">{data.account_note}</Alert> : null}
          {data.linked_accounts.length > 1 ? (
            <>
              <Typography variant="h6">
                Chargeback by account{visible.service ? ` · ${visible.service}` : ""}
              </Typography>
              <ComparisonTable
                rows={data.linked_accounts
                  .filter((row) => {
                    if (visible.linked_account && row.account_id !== visible.linked_account) return false;
                    if (visible.service && row.current === 0 && row.previous === 0) return false;
                    return true;
                  })
                  .map((row) => ({
                    name: `${row.account_id}${row.account_name ? ` · ${row.account_name}` : ""}${row.is_this_login ? " (this account)" : " (linked)"}`,
                    current: row.current,
                    previous: row.previous,
                    change: row.change,
                    changePercent: row.change_percent,
                  }))}
                nameHeader="Account"
                currentLabel={data.current_period_label}
                previousLabel={data.previous_period_label}
                currency={data.currency}
              />
            </>
          ) : null}
          {data.daily_note ? <Alert severity="info">{data.daily_note}</Alert> : null}
          <Alert severity="info">{data.monthly_note}</Alert>
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", xl: "1.2fr 1fr" } }}>
            <ChartCard title={visible.service ? `Daily cost · ${visible.service}` : "Daily cost"}>
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
                  <Tooltip {...tooltip} formatter={(value) => formatAmount(Number(value ?? 0), data.currency)} />
                  <Bar dataKey="amount" fill={chart.primary} isAnimationActive={false} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title={visible.service ? `Monthly cost · ${visible.service}` : "Monthly cost"}>
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
                  <Tooltip {...tooltip} formatter={(value) => formatAmount(Number(value ?? 0), data.currency)} />
                  <Bar dataKey="amount" fill={chart.secondary} isAnimationActive={false} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </Box>
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" } }}>
            <ChartCard title="Service distribution">
              <ResponsiveContainer width="100%" height={categoryChartHeight(serviceRows.length)}>
                <BarChart data={serviceRows} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
                  <CartesianGrid stroke={chart.grid} horizontal={false} />
                  <XAxis
                    type="number"
                    tickFormatter={(value: number) => formatCompactMoney(value, data.currency)}
                    tick={{ fontSize: 12 }}
                    {...zeroValueAxis(serviceRows.map((row) => row.current))}
                  />
                  <YAxis
                    type="category"
                    dataKey="service"
                    width={188}
                    interval={0}
                    tick={<CategoryTick />}
                  />
                  <Tooltip
                    {...tooltip}
                    formatter={(value) => formatAmount(Number(value ?? 0), data.currency)}
                    labelFormatter={(label) => String(label)}
                  />
                  <Bar dataKey="current" fill={chart.primary} isAnimationActive={false} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Regional distribution">
              {visible.service ? (
                <Typography variant="body2" color="text.secondary">
                  Region is not split by service. Clear the service filter to see regional distribution.
                </Typography>
              ) : (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart
                    data={regionRows.filter((row) => row.current !== 0 || row.previous !== 0)}
                    margin={{ bottom: 28, right: 8 }}
                  >
                    <CartesianGrid stroke={chart.grid} vertical={false} />
                    <XAxis dataKey="region" interval={0} angle={-28} textAnchor="end" height={52} tick={{ fontSize: 11 }} />
                    <YAxis
                      tickFormatter={(value: number) => formatCompactMoney(value, data.currency)}
                      width={72}
                      tick={{ fontSize: 12 }}
                      {...zeroValueAxis(regionRows.map((row) => row.current))}
                    />
                    <Tooltip {...tooltip} formatter={(value) => formatAmount(Number(value ?? 0), data.currency)} />
                    <Bar dataKey="current" fill={chart.secondary} isAnimationActive={false} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </ChartCard>
          </Box>

          <Typography variant="h6">Service breakdown</Typography>
          <ComparisonTable
            rows={serviceRows.map((row) => ({
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

          {usageRows.length > 0 ? (
            <>
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
                    {usageRows.map((row) => (
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
  if (filters.linked_account) params.set("linked_account", filters.linked_account);
  const value = params.toString();
  return value ? `?${value}` : "";
}

function ScanAlert({ result }: { result: ScanResult }) {
  const cost = result.steps.find((step) => step.service === "cost_explorer");
  const forecast = result.steps.find((step) => step.service === "cost_forecast");
  const failed = cost?.status === "error";
  const severity = failed ? "error" : cost?.status === "ok" ? "success" : "warning";
  const parts = [cost?.detail || cost?.error || "Cost refresh finished."];
  if (forecast?.status === "ok" && forecast.detail) parts.push(forecast.detail);
  if (forecast?.status === "error" && forecast.error) parts.push(forecast.error);
  return <Alert severity={severity}>{parts.join(" ")}</Alert>;
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
