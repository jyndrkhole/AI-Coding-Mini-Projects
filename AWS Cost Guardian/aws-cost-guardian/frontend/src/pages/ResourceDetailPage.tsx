import { Alert, Card, CardContent, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { apiGet } from "../services/api";
import type { InventoryResource } from "../types";

export function ResourceDetailPage() {
  const params = useParams();
  const resourceId = decodeURIComponent(params["*"] || "");
  const resource = useQuery({
    queryKey: ["resource", resourceId],
    queryFn: () => apiGet<InventoryResource>(`/api/resources/${encodeURIComponent(resourceId)}`),
    enabled: Boolean(resourceId),
  });

  if (!resourceId) {
    return <Alert severity="info">Choose a resource from the inventory.</Alert>;
  }

  return (
    <Stack spacing={2}>
      <Typography variant="body2">
        <Link to="/resources">Resources</Link>
      </Typography>
      {resource.isError ? <Alert severity="error">{resource.error.message}</Alert> : null}
      {resource.data ? (
        <Card>
          <CardContent>
            <Typography variant="h5">{resource.data.name || resource.data.resource_id}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              {resource.data.resource_id}
            </Typography>
            <Typography variant="body2" sx={{ mt: 2 }}>
              {resource.data.service} · {resource.data.state || "state not stored"} · {resource.data.environment || "environment not tagged"}
            </Typography>
            <Typography variant="subtitle2" sx={{ mt: 2 }}>
              Configuration
            </Typography>
            <Typography variant="body2" component="pre" sx={{ whiteSpace: "pre-wrap" }}>
              {JSON.stringify(resource.data.metadata, null, 2)}
            </Typography>
            <Typography variant="subtitle2" sx={{ mt: 2 }}>
              Metrics
            </Typography>
            {(resource.data.metrics ?? []).length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No CloudWatch summary is stored. Missing metrics are not treated as zero usage.
              </Typography>
            ) : (
              (resource.data.metrics ?? []).map((metric) => (
                <Typography key={metric.metric_name} variant="body2">
                  {metric.metric_name}: average {metric.average ?? "not stored"}, peak {metric.maximum ?? "not stored"}
                </Typography>
              ))
            )}
          </CardContent>
        </Card>
      ) : null}
    </Stack>
  );
}
