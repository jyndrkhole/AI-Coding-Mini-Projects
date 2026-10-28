# API

All routes are under `/api`. Set `NPS_API_TOKEN` to require `Authorization: Bearer <token>`. Health stays open.

- `GET /health`
- `GET /surveys/datasets`
- `POST /surveys/upload` multipart file, CSV, maximum 2 MB
- `GET /surveys/{dataset_id}/metadata`
- `GET /overview/{dataset_id}`
- `GET /nps/{dataset_id}/monthly`
- `GET /nps/{dataset_id}/segments`
- `GET /nps/{dataset_id}/confidence`
- `GET /themes/{dataset_id}`
- `GET /themes/{dataset_id}/monthly`
- `GET /data-quality/{dataset_id}`
- `GET /revenue-risk/{dataset_id}`
- `GET /callbacks/{analysis_run_id}`
- `POST /analysis/{dataset_id}/run?force=false`
- `GET /analysis/{analysis_run_id}/status`
- `GET /analysis/{analysis_run_id}/results`
- `POST /simulations/fix-impact` JSON body: dataset_id, theme, scenario A|B|C, optional proportion, score_delta, response_ids
- `GET /reports/{analysis_run_id}`
- `GET /reports/{analysis_run_id}/export?format=md|html`
- `GET /agents/{analysis_run_id}/trace`

Unknown dataset ids return 404. A malformed CSV returns 400. Unexpected failures return a short message and do not include a stack trace.
