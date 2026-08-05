import UploadFileIcon from '@mui/icons-material/UploadFile';
import {
  Box,
  Button,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Radio,
  RadioGroup,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { forwardRef, useRef } from 'react';
import type { EndpointInfo, SchemaOption, SchemaSourceType } from '../types';
import CodeEditor, { type CodeEditorHandle } from './CodeEditor';

interface Props {
  sourceType: SchemaSourceType;
  onSourceTypeChange: (v: SchemaSourceType) => void;
  url: string;
  onUrlChange: (v: string) => void;
  schemaText: string;
  onSchemaTextChange: (v: string) => void;
  onLoad: () => void;
  onFileSelected: (file: File) => void;
  loading: boolean;
  format?: string | null;
  endpoints: EndpointInfo[];
  schemas: SchemaOption[];
  selectedPath: string;
  selectedMethod: string;
  selectedStatus: string;
  selectedSchemaName: string;
  onPathChange: (v: string) => void;
  onMethodChange: (v: string) => void;
  onStatusChange: (v: string) => void;
  onSchemaNameChange: (v: string) => void;
  editorLanguage: string;
  allowRemoteFetch?: boolean;
  schemaFocusLines?: number[];
}

const SchemaPanel = forwardRef<CodeEditorHandle, Props>(function SchemaPanel(
  props,
  ref,
) {
  const fileRef = useRef<HTMLInputElement>(null);
  const allowRemoteFetch = props.allowRemoteFetch ?? false;
  const methodsForPath = props.endpoints
    .filter((e) => e.path === props.selectedPath)
    .map((e) => e.method);
  const uniquePaths = [...new Set(props.endpoints.map((e) => e.path))];
  const currentEndpoint = props.endpoints.find(
    (e) => e.path === props.selectedPath && e.method === props.selectedMethod,
  );

  return (
    <Stack spacing={1.5} sx={{ height: '100%' }}>
      <Typography variant="h6">Schema Source</Typography>

      <FormControl>
        <RadioGroup
          row
          value={props.sourceType}
          onChange={(e) => props.onSourceTypeChange(e.target.value as SchemaSourceType)}
        >
          <FormControlLabel
            value="url"
            control={<Radio size="small" />}
            label="URL"
            disabled={!allowRemoteFetch}
          />
          <FormControlLabel value="file" control={<Radio size="small" />} label="Upload File" />
          <FormControlLabel value="text" control={<Radio size="small" />} label="Paste Text" />
        </RadioGroup>
      </FormControl>

      {!allowRemoteFetch && (
        <Typography variant="caption" color="text.secondary">
          URL fetch is disabled in local-only privacy mode. Paste YAML/JSON or upload a file.
        </Typography>
      )}

      {props.sourceType === 'url' && allowRemoteFetch && (
        <Stack direction="row" spacing={1}>
          <TextField
            size="small"
            fullWidth
            label="Schema URL"
            placeholder="https://example.com/openapi.yaml"
            value={props.url}
            onChange={(e) => props.onUrlChange(e.target.value)}
          />
          <Button variant="outlined" onClick={props.onLoad} disabled={props.loading}>
            Fetch
          </Button>
        </Stack>
      )}

      {props.sourceType === 'file' && (
        <Stack direction="row" spacing={1} alignItems="center">
          <input
            ref={fileRef}
            hidden
            type="file"
            accept=".json,.yaml,.yml,application/json,text/yaml"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) props.onFileSelected(f);
            }}
          />
          <Button
            variant="outlined"
            startIcon={<UploadFileIcon />}
            onClick={() => fileRef.current?.click()}
            disabled={props.loading}
          >
            Choose YAML / JSON
          </Button>
        </Stack>
      )}

      {props.sourceType === 'text' && (
        <Button variant="outlined" onClick={props.onLoad} disabled={props.loading} sx={{ alignSelf: 'flex-start' }}>
          Parse Schema
        </Button>
      )}

      {(props.endpoints.length > 0 || props.schemas.length > 0) && (
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
          {uniquePaths.length > 0 && (
            <FormControl size="small" fullWidth>
              <InputLabel>API Path</InputLabel>
              <Select
                label="API Path"
                value={props.selectedPath}
                onChange={(e) => props.onPathChange(e.target.value)}
              >
                {uniquePaths.map((p) => (
                  <MenuItem key={p} value={p}>
                    {p}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
          {methodsForPath.length > 0 && (
            <FormControl size="small" fullWidth>
              <InputLabel>Method</InputLabel>
              <Select
                label="Method"
                value={props.selectedMethod}
                onChange={(e) => props.onMethodChange(e.target.value)}
              >
                {methodsForPath.map((m) => (
                  <MenuItem key={m} value={m}>
                    {m}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
          {currentEndpoint && (
            <FormControl size="small" fullWidth>
              <InputLabel>Status</InputLabel>
              <Select
                label="Status"
                value={props.selectedStatus}
                onChange={(e) => props.onStatusChange(e.target.value)}
              >
                {currentEndpoint.response_codes.map((c) => (
                  <MenuItem key={c} value={c}>
                    {c}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
          {props.schemas.length > 0 && (
            <FormControl size="small" fullWidth>
              <InputLabel>Schema</InputLabel>
              <Select
                label="Schema"
                value={props.selectedSchemaName}
                onChange={(e) => props.onSchemaNameChange(e.target.value)}
              >
                <MenuItem value="">
                  <em>From path/method</em>
                </MenuItem>
                {props.schemas.map((s) => (
                  <MenuItem key={s.name} value={s.name}>
                    {s.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
        </Stack>
      )}

      {props.format && (
        <Typography variant="caption" color="text.secondary">
          Detected format: {props.format}
        </Typography>
      )}

      <Box sx={{ flex: 1, minHeight: 280 }} id="schema-editor-panel">
        <CodeEditor
          ref={ref}
          value={props.schemaText}
          onChange={props.onSchemaTextChange}
          language={props.editorLanguage}
          height="100%"
          focusLines={props.schemaFocusLines}
        />
      </Box>
    </Stack>
  );
});

export default SchemaPanel;
