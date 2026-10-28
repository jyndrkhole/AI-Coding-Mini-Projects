import { useQuery } from "@tanstack/react-query";
import { getJson } from "../services/api";

export interface DatasetRow {
  id: string;
  filename: string;
  row_count: number;
  valid_count: number;
  invalid_count: number;
  reporting_period_start: string | null;
  reporting_period_end: string | null;
  latest_analysis_run_id: string | null;
}

export function useDatasets() {
  return useQuery({
    queryKey: ["datasets"],
    queryFn: () => getJson<{ datasets: DatasetRow[] }>("/api/surveys/datasets"),
  });
}

export function useDatasetId(): string | undefined {
  return useDatasets().data?.datasets[0]?.id;
}

export function useRunId(): string | undefined {
  return useDatasets().data?.datasets[0]?.latest_analysis_run_id ?? undefined;
}
