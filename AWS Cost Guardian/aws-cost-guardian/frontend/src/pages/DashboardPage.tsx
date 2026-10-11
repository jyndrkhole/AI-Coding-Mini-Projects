import { Alert, Box, Button, Card, CardContent, Skeleton, Stack, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { categoryChartHeight, CategoryTick, useChartColors, useChartTooltip, useValueTones, zeroValueAxis } from "../components/chartLayout";
import { KpiCard } from "../components/KpiCard";
import { SafeSavingsColumn } from "../components/SafeSavingsColumn";
import { apiGet } from "../services/api";
import type { CostSummary, DailyCosts, OptimizationScore, Recommendation, RegionCosts, Savings, ServiceCosts } from "../types";
import { formatCompactMoney, formatMoney, formatPercent, formatSignedMoney } from "../utils/format";

const groups = [
  {
    id: "safe",
    title: "Safe savings",
    stance: "Quote",
    guidance: "One conversation per kind of waste. Quote a saving only when a card shows an amount.",
  },
  {
    id: "review",
    title: "Review required",
    stance: "Investigate",
    guidance: "Largest compute and storage lines. Collect utilization, then price one change. No saving is quoted here.",
  },
  {
    id: "architecture",
    title: "Architecture opportunities",
    stance: "Ceiling",
    guidance: "Standing hourly charges. The amount is a ceiling if the design changes after a replacement exists. Nothing was removed.",
  },
] as const;

export function DashboardPage() {
  const chart = useChartColors();
  const tooltip = useChartTooltip();
  const queryClient = useQueryClient();
  const summary = useQuery({ queryKey: ["costs", "summary"], queryFn: () => apiGet<CostSummary>("/api/costs/summary") });
  const daily = useQuery({ queryKey: ["costs", "daily"], queryFn: () => apiGet<DailyCosts>("/api/costs/daily") });
  const services = useQuery({ queryKey: ["costs", "services"], queryFn: () => apiGet<ServiceCosts>("/api/costs/services") });
  const regions = useQuery({ queryKey: ["costs", "regions"], queryFn: () => apiGet<RegionCosts>("/api/costs/regions") });
  const recommendations = useQuery({
    queryKey: ["recommendations"],
    queryFn: () => apiGet<{ currency: string; recommendations: Recommendation[] }>("/api/recommendations"),
  });
  const savings = useQuery({ queryKey: ["savings"], queryFn: () => apiGet<Savings>("/api/savings") });
  const score = useQuery({ queryKey: ["optimization-score"], queryFn: () => apiGet<OptimizationScore>("/api/optimization-score") });

  const queries = [summary, daily, services, regions, recommendations, savings, score];
  const error = queries.find((query) => query.isError)?.error;
  const isLoading = queries.some((query) => query.isLoading);

  async function reload() {
    await queryClient.invalidateQueries();
  }

  return (
    <Stack spacing={3}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" spacing={2}>
        <Box>
          <Typography variant="h4">Dashboard</Typography>
          <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 640, mt: 0.5 }}>
            Understand your AWS bill. Find the waste. Explain the trade-offs. Save with confidence.
          </Typography>
        </Box>
        <Button variant="outlined" onClick={() => void reload()}>
          Reload
        </Button>
      </Stack>

      {error ? <Alert severity="error">{error.message}</Alert> : null}

      {isLoading ? (
        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr 1fr" } }}>
          {Array.from({ length: 6 }, (_, index) => (
            <Skeleton key={index} variant="rounded" height={110} />
          ))}
        </Box>
      ) : null}

      {summary.data && savings.data && score.data ? (
        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "repeat(3, 1fr)" } }}>
          <KpiCard
            label="Current monthly cost"
            value={formatMoney(summary.data.current_monthly_cost, summary.data.currency)}
            caption={summary.data.current_period_label}
          />
          <KpiCard
            label="Previous monthly cost"
            value={formatMoney(summary.data.previous_monthly_cost, summary.data.currency)}
            caption={summary.data.previous_period_label}
          />
          <KpiCard
            label="MoM change"
            value={formatSignedMoney(summary.data.mom_change_amount, summary.data.currency)}
            caption={formatPercent(summary.data.mom_change_percent)}
            tone={summary.data.mom_change_amount > 0 ? "increase" : "savings"}
          />
          <KpiCard
            label="Potential monthly savings"
            value={formatMoney(savings.data.potential_monthly_savings, savings.data.currency)}
            caption={savings.data.label}
            tone="savings"
          />
          <KpiCard
            label="Potential annual savings"
            value={formatMoney(savings.data.potential_annual_savings, savings.data.currency)}
            caption={savings.data.label}
            tone="savings"
          />
          <KpiCard
            label="Optimization score"
            value={score.data.score === null ? "Not calculated" : `${score.data.score}`}
            caption={score.data.score === null ? score.data.label : `Out of ${score.data.maximum}`}
          />
        </Box>
      ) : null}

      {summary.data && summary.data.months.length > 0 ? (
        <ChartCard title="Last 6 months and current">
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {summary.data.history_note}
            {summary.data.prior_months_average === null
              ? ""
              : ` Average of the earlier full months: ${formatMoney(summary.data.prior_months_average, summary.data.currency)}.`}
            {" "}Hover a month to see which lines changed from the month before.
          </Typography>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={summary.data.months} margin={{ bottom: 24, right: 8 }}>
              <CartesianGrid stroke={chart.grid} vertical={false} />
              <XAxis dataKey="label" interval={0} angle={-28} textAnchor="end" height={56} tick={{ fontSize: 11 }} />
              <YAxis
                tickFormatter={(value: number) => formatCompactMoney(value, summary.data.currency)}
                width={72}
                tick={{ fontSize: 12 }}
                {...zeroValueAxis(summary.data.months.map((point) => point.amount))}
              />
              <Tooltip
                content={(tooltip) => (
                  <MonthChangeTooltip
                    active={tooltip.active}
                    payload={tooltip.payload as { payload?: CostSummary["months"][number] }[] | undefined}
                    currency={summary.data.currency}
                  />
                )}
                wrapperStyle={{ zIndex: 2, outline: "none" }}
              />
              <Bar dataKey="amount" fill={chart.primary} isAnimationActive={false} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      ) : null}

      {daily.data && services.data && regions.data ? (
        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", xl: "1.4fr 1fr" } }}>
          <ChartCard title={`Daily cost · ${daily.data.period_label}`}>
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={daily.data.points} margin={{ right: 8, bottom: 8 }}>
                <CartesianGrid stroke={chart.grid} vertical={false} />
                <XAxis dataKey="date" minTickGap={32} tickFormatter={(value: string) => value.slice(8)} tick={{ fontSize: 12 }} />
                <YAxis
                  tickFormatter={(value: number) => formatCompactMoney(value, daily.data.currency)}
                  width={72}
                  tick={{ fontSize: 12 }}
                  {...zeroValueAxis(daily.data.points.map((point) => point.amount))}
                />
                <Tooltip {...tooltip} formatter={(value) => formatMoney(Number(value ?? 0), daily.data.currency)} />
                <Area type="monotone" dataKey="amount" stroke={chart.primary} fill={chart.area} isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          </ChartCard>
          <Stack spacing={2}>
            <ChartCard title="Service cost">
              <ResponsiveContainer width="100%" height={categoryChartHeight(services.data.services.length)}>
                <BarChart data={services.data.services} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
                  <CartesianGrid stroke={chart.grid} horizontal={false} />
                  <XAxis
                    type="number"
                    tickFormatter={(value: number) => formatCompactMoney(value, services.data.currency)}
                    tick={{ fontSize: 12 }}
                    {...zeroValueAxis(services.data.services.map((row) => row.current))}
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
                    formatter={(value) => formatMoney(Number(value ?? 0), services.data.currency)}
                    labelFormatter={(label) => String(label)}
                  />
                  <Bar dataKey="current" fill={chart.primary} isAnimationActive={false} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Regional cost">
              <ResponsiveContainer width="100%" height={220}>
                <BarChart
                  data={regions.data.regions.filter((row) => row.current !== 0 || row.previous !== 0)}
                  margin={{ bottom: 28, right: 8 }}
                >
                  <CartesianGrid stroke={chart.grid} vertical={false} />
                  <XAxis dataKey="region" interval={0} angle={-28} textAnchor="end" height={52} tick={{ fontSize: 11 }} />
                  <YAxis
                    tickFormatter={(value: number) => formatCompactMoney(value, regions.data.currency)}
                    width={72}
                    tick={{ fontSize: 12 }}
                    {...zeroValueAxis(regions.data.regions.map((row) => row.current))}
                  />
                  <Tooltip {...tooltip} formatter={(value) => formatMoney(Number(value ?? 0), regions.data.currency)} />
                  <Bar dataKey="current" fill={chart.secondary} isAnimationActive={false} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </Stack>
        </Box>
      ) : null}

      {recommendations.data && recommendations.data.recommendations.length === 0 ? (
        <Alert severity="info">
          Safe savings, review, and architecture groups are empty because no recommendations have been collected
          for this account. This scan stores Cost Explorer amounts only.
        </Alert>
      ) : null}

      {recommendations.data && recommendations.data.recommendations.length > 0 ? (
        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", lg: "repeat(3, minmax(0, 1fr))" }, alignItems: "start" }}>
          {groups.map((group) => {
            const items = recommendations.data.recommendations.filter((item) => item.category === group.id);
            return (
              <Stack key={group.id} spacing={1.5}>
                <GroupHeader group={group} count={items.length} />
                {items.length === 0 ? (
                  <Typography variant="body2" color="text.secondary">
                    {group.id === "safe"
                      ? "Nothing is ready to quote. No low-risk cleanup was stored, and idle capacity was not measured."
                      : "None in this group."}
                  </Typography>
                ) : (
                  <SafeSavingsColumn
                    items={items}
                    currency={recommendations.data.currency}
                    mode={group.id === "architecture" ? "ceiling" : group.id === "review" ? "investigate" : "quote"}
                  />
                )}
              </Stack>
            );
          })}
        </Box>
      ) : null}
    </Stack>
  );
}

function GroupHeader({ group, count }: { group: (typeof groups)[number]; count: number }) {
  const theme = useTheme();
  const tones = useValueTones();
  const accent =
    group.id === "safe" ? tones.savings : group.id === "review" ? tones.increase : theme.palette.primary.main;
  const countLabel = count === 0 ? "None stored" : group.id === "safe" ? `${count} findings` : `${count} items`;
  return (
    <Card sx={{ borderTop: "3px solid", borderTopColor: accent, minHeight: { lg: 148 } }}>
      <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
        <Stack direction="row" justifyContent="space-between" alignItems="baseline" spacing={1}>
          <Typography variant="overline" sx={{ color: accent, letterSpacing: "0.12em", lineHeight: 1.4 }}>
            {group.stance}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {countLabel}
          </Typography>
        </Stack>
        <Typography variant="subtitle1" sx={{ fontWeight: 700, mt: 0.25 }}>
          {group.title}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          {group.guidance}
        </Typography>
      </CardContent>
    </Card>
  );
}

function MonthChangeTooltip({
  active,
  payload,
  currency,
}: {
  active?: boolean;
  payload?: { payload?: CostSummary["months"][number] }[];
  currency: string;
}) {
  const tones = useValueTones();
  const month = active ? payload?.[0]?.payload : undefined;
  if (!month) return null;
  return (
    <Box sx={{ bgcolor: "background.paper", border: 1, borderColor: "divider", borderRadius: 1, px: 1.25, py: 1, maxWidth: 340, boxShadow: 1 }}>
      <Typography variant="body2" sx={{ fontWeight: 700 }}>
        {month.label}
        {month.partial ? " · month to date" : ""}
      </Typography>
      <Typography variant="body2">{formatMoney(month.amount, currency)}</Typography>
      {month.compared_to && month.change !== null ? (
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
          {formatSignedMoney(month.change, currency)}
          {month.change_percent === null ? "" : ` (${formatPercent(month.change_percent)})`} vs {month.compared_to}
        </Typography>
      ) : (
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
          First stored month
        </Typography>
      )}
      {(month.components ?? []).map((item) => (
        <Stack key={`${item.service}-${item.usage_type}`} direction="row" justifyContent="space-between" spacing={1.5} sx={{ mt: 0.75 }}>
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="caption" sx={{ display: "block", fontWeight: 600 }}>
              {item.service}
            </Typography>
            {item.usage_type ? (
              <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                {item.usage_type}
              </Typography>
            ) : null}
          </Box>
          <Typography variant="caption" sx={{ fontWeight: 700, color: item.change > 0 ? tones.increase : tones.savings, whiteSpace: "nowrap" }}>
            {formatSignedMoney(item.change, currency)}
          </Typography>
        </Stack>
      ))}
      {month.other_component_count > 0 ? (
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.75 }}>
          {month.other_component_count} other lines also changed
        </Typography>
      ) : null}
    </Box>
  );
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
