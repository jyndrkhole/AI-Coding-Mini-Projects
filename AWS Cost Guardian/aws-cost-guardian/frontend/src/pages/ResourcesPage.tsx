import { Alert, Button, Card, CardContent, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useState } from "react";
import { PageHeaderAction, usePageHeader } from "../layouts/pageHeader";
import { apiGet, apiPost } from "../services/api";
import type { InventoryResource } from "../types";

type ScanStep = { service: string; status: string; error: string | null; detail: string | null };

export function ResourcesPage() {
  const [service, setService] = useState("");
  const [scanning, setScanning] = useState(false);
  const [scanNote, setScanNote] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const resources = useQuery({
    queryKey: ["resources"],
    queryFn: () => apiGet<{ resources: InventoryResource[] }>("/api/resources"),
  });
  const rows = (resources.data?.resources ?? []).filter((row) => !service || row.service === service);
  const services = Array.from(new Set((resources.data?.resources ?? []).map((row) => row.service))).sort();

  async function scan() {
    setScanning(true);
    setScanNote(null);
    try {
      const result = await apiPost<{ status: string; steps: ScanStep[] }>("/api/aws/scan");
      const denied = result.steps.filter((step) => step.status === "error" && step.error);
      setScanNote(
        denied.length
          ? denied.map((step) => step.error).join(" ")
          : `Scan ${result.status}. Stored resources will appear below.`,
      );
      await queryClient.invalidateQueries({ queryKey: ["resources"] });
    } catch (caught) {
      setScanNote(caught instanceof Error ? caught.message : "The scan could not finish.");
    } finally {
      setScanning(false);
    }
  }

  usePageHeader("Resources", "Instances, volumes, databases, and buckets collected by the last read-only scan.");

  return (
    <Stack spacing={2}>
      <PageHeaderAction>
        <Button size="small" variant="contained" onClick={() => void scan()} disabled={scanning}>
          {scanning ? "Scanning" : "Scan account"}
        </Button>
      </PageHeaderAction>
      <TextField select label="Service" value={service} onChange={(event) => setService(event.target.value)} sx={{ maxWidth: 280 }}>
        <MenuItem value="">All services</MenuItem>
        {services.map((item) => (
          <MenuItem key={item} value={item}>
            {item}
          </MenuItem>
        ))}
      </TextField>
      {resources.isError ? <Alert severity="error">{resources.error.message}</Alert> : null}
      {rows.map((row) => (
        <Card key={row.resource_id}>
          <CardContent>
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
              <Link to={`/resources/${encodeURIComponent(row.resource_id)}`}>{row.name || row.resource_id}</Link>
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {row.service} · {row.resource_type} · {row.region || "region not stored"} · {row.state || "state not stored"}
              {row.instance_type ? ` · ${row.instance_type}` : ""}
              {row.environment ? ` · ${row.environment}` : ""}
            </Typography>
          </CardContent>
        </Card>
      ))}
      {scanNote ? <Alert severity="warning">{scanNote}</Alert> : null}
      {resources.data && rows.length === 0 ? (
        <Alert severity="info">
          No resources are stored yet. Cost Explorer access is working. This IAM user still needs read-only list
          permissions for EC2, EBS, RDS, S3, Lambda, load balancers, CloudWatch, Compute Optimizer, and Cost
          Optimization Hub. Attach those to the user, then use Scan account. Nothing in AWS is changed by the scan.
        </Alert>
      ) : null}
    </Stack>
  );
}

