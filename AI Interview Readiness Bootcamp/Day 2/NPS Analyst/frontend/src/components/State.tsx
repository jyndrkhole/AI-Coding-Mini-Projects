import { Alert, Box, CircularProgress, Typography } from "@mui/material";
import { ReactNode } from "react";

export function QueryState({
  loading,
  error,
  empty,
  emptyMessage = "No survey is loaded. Upload a CSV with the expected columns.",
  children,
}: {
  loading: boolean;
  error: Error | null;
  empty?: boolean;
  emptyMessage?: string;
  children: ReactNode;
}) {
  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }
  if (error) {
    return <Alert severity="error">{error.message}</Alert>;
  }
  if (empty) {
    return <Alert severity="info">{emptyMessage}</Alert>;
  }
  return <>{children}</>;
}

export function PageTitle({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="h4">{title}</Typography>
      <Typography color="text.secondary">{subtitle}</Typography>
    </Box>
  );
}
