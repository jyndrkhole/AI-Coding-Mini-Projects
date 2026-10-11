import { Box, Button, Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import { useState } from "react";
import { Link } from "react-router-dom";
import type { Recommendation } from "../types";
import { formatMoney } from "../utils/format";

const PREVIEW = 6;

function riskChipColor(level: string): "success" | "warning" | "error" | "default" {
  if (level === "LOW") return "success";
  if (level === "MEDIUM") return "warning";
  if (level === "HIGH") return "error";
  return "default";
}

const actionOrder: Record<string, number> = {
  CLEANUP: 0,
  RELEASE: 1,
  SCHEDULE: 2,
  REVIEW: 3,
  GOVERNANCE: 4,
};

type Conversation = {
  title: string;
  service: string;
  actionType: string;
  quoted: boolean;
  items: Recommendation[];
};

function conversationsFor(items: Recommendation[]): Conversation[] {
  const groups = new Map<string, Recommendation[]>();
  for (const item of items) {
    const quoted = item.estimated_monthly_savings > 0;
    const key = `${item.title}\u0000${quoted ? "quoted" : "open"}`;
    const bucket = groups.get(key) ?? [];
    bucket.push(item);
    groups.set(key, bucket);
  }
  return [...groups.values()]
    .map((group) => ({
      title: group[0].title,
      service: group[0].service,
      actionType: group[0].action_type,
      quoted: group.every((item) => item.estimated_monthly_savings > 0),
      items: group,
    }))
    .sort((left, right) => {
      if (left.quoted !== right.quoted) return left.quoted ? -1 : 1;
      const byAction = (actionOrder[left.actionType] ?? 9) - (actionOrder[right.actionType] ?? 9);
      if (byAction !== 0) return byAction;
      return left.items.length - right.items.length;
    });
}

function sameFacts(items: Recommendation[]): boolean {
  const first = JSON.stringify(items[0].next_steps ?? []);
  return items.every((item) => JSON.stringify(item.next_steps ?? []) === first);
}

export function SafeSavingsColumn({
  items,
  currency,
  mode = "quote",
}: {
  items: Recommendation[];
  currency: string;
  mode?: "quote" | "investigate" | "ceiling";
}) {
  const conversations = conversationsFor(items);
  return (
    <Stack spacing={1.5}>
      {conversations.map((conversation) => (
        <ConversationCard
          key={`${conversation.title}-${conversation.quoted}`}
          conversation={conversation}
          currency={currency}
          mode={mode}
        />
      ))}
    </Stack>
  );
}

function ConversationCard({
  conversation,
  currency,
  mode,
}: {
  conversation: Conversation;
  currency: string;
  mode: "quote" | "investigate" | "ceiling";
}) {
  const [checksOpen, setChecksOpen] = useState(false);
  const [resourcesOpen, setResourcesOpen] = useState(false);
  const { items } = conversation;
  const first = items[0];
  const shared = sameFacts(items);
  const steps = shared ? (first.next_steps ?? []) : [];
  const visible = resourcesOpen ? items : items.slice(0, PREVIEW);
  const hidden = items.length - visible.length;
  const bill = items.reduce((sum, item) => sum + item.current_monthly_cost, 0);
  const quotedAmount = items.reduce((sum, item) => sum + item.estimated_monthly_savings, 0);
  const risks = [...new Set(items.map((item) => item.risk_level))];
  const hasAmount = mode === "ceiling" || conversation.quoted;
  const savingLabel = mode === "ceiling" ? "Ceiling" : "Saving";
  const savingValue = hasAmount ? `${formatMoney(quotedAmount, currency)}/month` : "Not estimated";

  return (
    <Card>
      <CardContent sx={{ py: 1.75, "&:last-child": { pb: 1.75 } }}>
        <Stack direction="row" justifyContent="space-between" spacing={1} alignItems="flex-start">
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            {conversation.title}
          </Typography>
          <Stack direction="row" spacing={0.75} useFlexGap flexWrap="wrap" justifyContent="flex-end">
            {risks.map((risk) => (
              <Chip key={risk} size="small" color={riskChipColor(risk)} label={`Risk ${risk}`} />
            ))}
            <Chip size="small" label={conversation.service} variant="outlined" />
          </Stack>
        </Stack>
        <Stack direction="row" spacing={2.5} sx={{ mt: 1.25 }}>
          {bill > 0 ? (
            <Box>
              <Typography variant="caption" color="text.secondary">
                {mode === "ceiling" ? "Last full month" : "On the bill"}
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 700 }}>
                {formatMoney(bill, currency)}
              </Typography>
            </Box>
          ) : null}
          <Box>
            <Typography variant="caption" color="text.secondary">
              {savingLabel}
            </Typography>
            <Typography
              variant="body2"
              sx={{ fontWeight: 700, color: hasAmount ? "text.primary" : "text.secondary" }}
            >
              {savingValue}
            </Typography>
          </Box>
          <Box sx={{ ml: "auto", textAlign: "right" }}>
            <Typography variant="caption" color="text.secondary">
              {items.length === 1 ? "1 finding" : `${items.length} findings`}
            </Typography>
          </Box>
        </Stack>
        {first.client_brief ? (
          <Typography variant="body2" sx={{ mt: 1.25 }}>
            {first.client_brief}
          </Typography>
        ) : null}
        {first.client_ask ? (
          <Typography variant="body2" sx={{ mt: 1, pl: 1.25, borderLeft: 2, borderColor: "divider" }}>
            {first.client_ask}
          </Typography>
        ) : null}
        {steps.length > 0 ? (
          <Box sx={{ mt: 0.75 }}>
            <Button size="small" sx={{ px: 0 }} onClick={() => setChecksOpen((open) => !open)}>
              {checksOpen ? "Hide the checks" : `Show ${steps.length} ${steps.length === 1 ? "check" : "checks"}`}
            </Button>
            {checksOpen ? (
              <Box component="ol" sx={{ m: 0, pl: 2.25 }}>
                {steps.map((step) => (
                  <Typography key={step} component="li" variant="body2" sx={{ mt: 0.5 }}>
                    {step}
                  </Typography>
                ))}
              </Box>
            ) : null}
          </Box>
        ) : null}
        <Stack spacing={0.5} sx={{ mt: 1 }}>
          {visible.map((item) => (
            <Typography key={item.id} variant="body2">
              <Link to={`/recommendations/${item.id}`}>{item.resource_id ?? item.title}</Link>
              {!shared && item.next_steps && item.next_steps.length > 0 ? (
                <Box component="span" sx={{ color: "text.secondary" }}>{` — ${item.next_steps[0]}`}</Box>
              ) : null}
            </Typography>
          ))}
          {hidden > 0 ? (
            <Button size="small" sx={{ px: 0, alignSelf: "flex-start" }} onClick={() => setResourcesOpen(true)}>
              Show the other {hidden}
            </Button>
          ) : null}
          {resourcesOpen && items.length > PREVIEW ? (
            <Button size="small" sx={{ px: 0, alignSelf: "flex-start" }} onClick={() => setResourcesOpen(false)}>
              Show fewer
            </Button>
          ) : null}
        </Stack>
      </CardContent>
    </Card>
  );
}
