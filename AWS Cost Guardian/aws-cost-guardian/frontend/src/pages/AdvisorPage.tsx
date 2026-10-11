import { Alert, Button, Card, CardContent, Stack, TextField, Typography } from "@mui/material";
import { useState } from "react";
import { apiPost } from "../services/api";
import type { AdvisorAnswer } from "../types";

export function AdvisorPage() {
  const [message, setMessage] = useState("Where should we look first for this account?");
  const [answer, setAnswer] = useState<AdvisorAnswer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function ask() {
    setPending(true);
    setError(null);
    try {
      setAnswer(await apiPost<AdvisorAnswer>("/api/ai/chat", { message }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The advisor could not answer.");
    } finally {
      setPending(false);
    }
  }

  return (
    <Stack spacing={2}>
      <Typography variant="h4">Advisor</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 720 }}>
        The advisor explains stored costs and recommendations. Dollar amounts come from the application. If the model is
        not configured, the answer is the stored evidence itself.
      </Typography>
      <TextField multiline minRows={3} label="Question" value={message} onChange={(event) => setMessage(event.target.value)} />
      <Button variant="contained" onClick={() => void ask()} disabled={pending} sx={{ alignSelf: "flex-start" }}>
        {pending ? "Asking" : "Ask"}
      </Button>
      {error ? <Alert severity="error">{error}</Alert> : null}
      {answer ? (
        <Card>
          <CardContent>
            <Typography variant="caption" color="text.secondary">
              {answer.narrative_source === "model" ? `Answer from ${answer.provider}` : "Answer from stored evidence"}
            </Typography>
            <Typography variant="body1" sx={{ mt: 1 }}>
              {answer.narrative}
            </Typography>
            <Typography variant="subtitle2" sx={{ mt: 2 }}>
              Facts
            </Typography>
            {answer.facts.map((fact) => (
              <Typography key={fact} variant="body2">
                {fact}
              </Typography>
            ))}
            {answer.missing_evidence.length > 0 ? (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                Missing: {answer.missing_evidence.join(" ")}
              </Typography>
            ) : null}
          </CardContent>
        </Card>
      ) : null}
    </Stack>
  );
}
