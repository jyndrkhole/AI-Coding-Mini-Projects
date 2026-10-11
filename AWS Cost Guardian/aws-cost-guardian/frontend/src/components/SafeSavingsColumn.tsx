import { Box, Button, Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import { useState } from "react";
import { Link } from "react-router-dom";
import type { Recommendation } from "../types";
import { formatMoney } from "../utils/format";

const PREVIEW = 6;

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

export function SafeSavingsColumn({ items, currency }: { items: Recommendation[]; currency: string }) {
  const conversations = conversationsFor(items);
  const quoted = conversations.filter((conversation) => conversation.quoted);
  const summary =
    quoted.length === 0
      ? `${conversations.length} conversations, ${items.length} findings. No saving in this column is estimated.`
      : `${quoted.length} of ${conversations.length} conversations have a quoted saving. Leave the rest as “Not estimated.”`;

  return (
    <Stack spacing={1.5}>
      <Typography variant="body2" color="text.secondary">
        {summary}
      </Typography>
      {conversations.map((conversation) => (
        <ConversationCard key={`${conversation.title}-${conversation.quoted}`} conversation={conversation} currency={currency} />
      ))}
    </Stack>
  );
}

function ConversationCard({ conversation, currency }: { conversation: Conversation; currency: string }) {
  const [expanded, setExpanded] = useState(false);
  const { items } = conversation;
  const first = items[0];
  const shared = sameFacts(items);
  const visible = expanded ? items : items.slice(0, PREVIEW);
  const hidden = items.length - visible.length;
  const quotedTotal = items.reduce((sum, item) => sum + item.estimated_monthly_savings, 0);

  return (
    <Card>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" spacing={1} alignItems="flex-start">
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            {conversation.title}
          </Typography>
          <Chip size="small" label={conversation.service} variant="outlined" />
        </Stack>
        <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 1 }}>
          <Chip size="small" variant="outlined" label={items.length === 1 ? "1 finding" : `${items.length} findings`} />
          <Chip
            size="small"
            variant={conversation.quoted ? "filled" : "outlined"}
            color={conversation.quoted ? "success" : "default"}
            label={conversation.quoted ? `${formatMoney(quotedTotal, currency)}/month` : "Not estimated"}
          />
        </Stack>
        {first.client_brief ? (
          <Box sx={{ mt: 1.5 }}>
            <Typography variant="caption" color="text.secondary">
              Tell the client
            </Typography>
            <Typography variant="body2">{first.client_brief}</Typography>
          </Box>
        ) : null}
        {first.client_ask ? (
          <Box sx={{ mt: 1.5 }}>
            <Typography variant="caption" color="text.secondary">
              Ask the client
            </Typography>
            <Typography variant="body2">{first.client_ask}</Typography>
          </Box>
        ) : null}
        <Box sx={{ mt: 1.5 }}>
          <Typography variant="caption" color="text.secondary">
            What you found
          </Typography>
          {shared ? (
            <Box component="ol" sx={{ m: 0, pl: 2.25 }}>
              {(first.next_steps ?? []).map((step) => (
                <Typography key={step} component="li" variant="body2" sx={{ mt: 0.5 }}>
                  {step}
                </Typography>
              ))}
            </Box>
          ) : null}
          <Stack spacing={0.75} sx={{ mt: shared ? 1 : 0.5 }}>
            {visible.map((item) => (
              <Typography key={item.id} variant="body2">
                <Link to={`/recommendations/${item.id}`}>{item.resource_id ?? item.title}</Link>
                {!shared && item.next_steps && item.next_steps.length > 0 ? (
                  <Box component="span" sx={{ color: "text.secondary" }}>{` — ${item.next_steps.join(" · ")}`}</Box>
                ) : null}
              </Typography>
            ))}
          </Stack>
          {hidden > 0 ? (
            <Button size="small" sx={{ mt: 0.5, px: 0 }} onClick={() => setExpanded(true)}>
              Show the other {hidden}
            </Button>
          ) : null}
          {expanded && items.length > PREVIEW ? (
            <Button size="small" sx={{ mt: 0.5, px: 0 }} onClick={() => setExpanded(false)}>
              Show fewer
            </Button>
          ) : null}
        </Box>
      </CardContent>
    </Card>
  );
}
