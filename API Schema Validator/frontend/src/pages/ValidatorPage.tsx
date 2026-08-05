import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import DownloadIcon from '@mui/icons-material/Download';
import LightModeIcon from '@mui/icons-material/LightMode';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import {
  Alert,
  AppBar,
  Box,
  Button,
  CircularProgress,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Menu,
  MenuItem,
  Paper,
  Stack,
  Toolbar,
  Tooltip,
  Typography,
} from '@mui/material';
import Grid from '@mui/material/Grid2';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { CodeEditorHandle } from '../components/CodeEditor';
import ResponsePanel from '../components/ResponsePanel';
import SchemaPanel from '../components/SchemaPanel';
import ValidationResultView from '../components/ValidationResultView';
import {
  explainWithAi,
  exportReport,
  healthCheck,
  loadSchema,
  validateSchema,
} from '../services/api';
import type {
  EndpointInfo,
  ExportFormat,
  HealthResponse,
  LLMAction,
  SchemaOption,
  SchemaSourceType,
  ValidationErrorDetail,
  ValidationResponse,
} from '../types';
import { resolveResponseLine, resolveSchemaLine } from '../utils/locateInDocument';

interface Props {
  mode: 'light' | 'dark';
  onToggleTheme: () => void;
}

const SAMPLE_SCHEMA = `{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "User",
  "type": "object",
  "required": ["id", "email", "role"],
  "additionalProperties": false,
  "properties": {
    "id": { "type": "integer", "minimum": 1 },
    "email": { "type": "string", "format": "email" },
    "role": { "type": "string", "enum": ["admin", "member", "guest"] }
  }
}`;

const SAMPLE_RESPONSE = `{
  "id": "42",
  "email": "bad-email",
  "role": "superadmin",
  "extra": true
}`;

export default function ValidatorPage({ mode, onToggleTheme }: Props) {
  const [sourceType, setSourceType] = useState<SchemaSourceType>('text');
  const [url, setUrl] = useState('');
  const [schemaText, setSchemaText] = useState(SAMPLE_SCHEMA);
  const [responseText, setResponseText] = useState(SAMPLE_RESPONSE);
  const [format, setFormat] = useState<string | null>('json_schema');
  const [endpoints, setEndpoints] = useState<EndpointInfo[]>([]);
  const [schemas, setSchemas] = useState<SchemaOption[]>([]);
  const [selectedPath, setSelectedPath] = useState('');
  const [selectedMethod, setSelectedMethod] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('200');
  const [selectedSchemaName, setSelectedSchemaName] = useState('');
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [result, setResult] = useState<ValidationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [aiOpen, setAiOpen] = useState(false);
  const [aiContent, setAiContent] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [exportAnchor, setExportAnchor] = useState<null | HTMLElement>(null);
  const [aiAnchor, setAiAnchor] = useState<null | HTMLElement>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [selectedErrorIndex, setSelectedErrorIndex] = useState<number | null>(null);
  const [schemaFocusLines, setSchemaFocusLines] = useState<number[]>([]);
  const [responseFocusLines, setResponseFocusLines] = useState<number[]>([]);
  const schemaEditorRef = useRef<CodeEditorHandle>(null);
  const responseEditorRef = useRef<CodeEditorHandle>(null);

  useEffect(() => {
    healthCheck()
      .then(setHealth)
      .catch((e) => {
        setHealth(null);
        setError(e instanceof Error ? e.message : 'Backend health check failed');
      });
  }, []);

  const privacy = health?.privacy;
  const allowRemoteFetch = Boolean(privacy?.remote_schema_fetch);
  const allowAi = Boolean(privacy?.local_llm || privacy?.cloud_llm);

  useEffect(() => {
    if (!allowRemoteFetch && sourceType === 'url') {
      setSourceType('text');
    }
  }, [allowRemoteFetch, sourceType]);

  const editorLanguage = useMemo(() => {
    const trimmed = schemaText.trimStart();
    return trimmed.startsWith('{') ? 'json' : 'yaml';
  }, [schemaText]);

  const errorLines = useMemo(
    () =>
      (result?.errors ?? [])
        .map((e) => e.line_number)
        .filter((n): n is number => typeof n === 'number'),
    [result],
  );

  const applyLoadResult = useCallback((data: Awaited<ReturnType<typeof loadSchema>>) => {
    if (!data.success) {
      setError(data.error || data.message || 'Failed to load schema');
      return;
    }
    setError(null);
    setFormat(data.format);
    if (data.schema_text) setSchemaText(data.schema_text);
    setEndpoints(data.endpoints ?? []);
    setSchemas(data.schemas ?? []);
    if (data.endpoints?.length) {
      setSelectedPath(data.endpoints[0].path);
      setSelectedMethod(data.endpoints[0].method);
      setSelectedStatus(data.endpoints[0].response_codes[0] ?? '200');
    }
    if (data.format === 'json_schema' && data.schemas[0]) {
      setSelectedSchemaName(data.schemas[0].name);
    }
  }, []);

  const handleLoad = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await loadSchema({
        sourceType,
        content: schemaText,
        url,
      });
      applyLoadResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Schema load failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSchemaFile = async (file: File) => {
    setLoading(true);
    setError(null);
    try {
      const data = await loadSchema({ sourceType: 'file', file });
      applyLoadResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'File load failed');
    } finally {
      setLoading(false);
    }
  };

  const handleResponseFile = async (file: File) => {
    const text = await file.text();
    setResponseText(text);
  };

  const handleValidate = async () => {
    setValidating(true);
    setError(null);
    setSelectedErrorIndex(null);
    setSchemaFocusLines([]);
    setResponseFocusLines([]);
    try {
      const data = await validateSchema({
        schema_content: schemaText,
        response_content: responseText,
        path: selectedPath || null,
        method: selectedMethod || null,
        status_code: selectedStatus || '200',
        schema_name: selectedSchemaName || null,
      });
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Validation failed');
    } finally {
      setValidating(false);
    }
  };

  const handleErrorNavigate = useCallback(
    (err: ValidationErrorDetail, index: number) => {
      setSelectedErrorIndex(index);

      const schemaLine = resolveSchemaLine(
        schemaText,
        err.schema_path,
        {
          openApiPath: selectedPath || null,
          method: selectedMethod || null,
          statusCode: selectedStatus || null,
          schemaName: selectedSchemaName || null,
        },
        err.json_path,
      );
      const responseLine = resolveResponseLine(
        responseText,
        err.json_path,
        err.line_number,
      );

      setSchemaFocusLines(schemaLine ? [schemaLine] : []);
      setResponseFocusLines(responseLine ? [responseLine] : []);

      // Prefer schema jump first (YAML/JSON rule), then response instance.
      window.setTimeout(() => {
        if (schemaLine) {
          document.getElementById('schema-editor-panel')?.scrollIntoView({
            behavior: 'smooth',
            block: 'center',
          });
          schemaEditorRef.current?.revealLine(schemaLine);
        }
        if (responseLine) {
          // Slight delay so both panels get focus cues; schema stays primary.
          window.setTimeout(() => {
            responseEditorRef.current?.revealLine(responseLine);
          }, schemaLine ? 350 : 0);
        }
      }, 50);

      if (!schemaLine && !responseLine) {
        setError(
          `Could not locate ${err.category} in the editors (path: ${err.schema_path || err.json_path}).`,
        );
      }
    },
    [
      schemaText,
      responseText,
      selectedPath,
      selectedMethod,
      selectedStatus,
      selectedSchemaName,
    ],
  );

  const handleExport = async (fmt: ExportFormat) => {
    setExportAnchor(null);
    if (!result) return;
    try {
      const blob = await exportReport({
        format: fmt,
        validationResult: result,
        schemaContent: schemaText,
        responseContent: responseText,
      });
      const urlObj = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = urlObj;
      a.download = `validation-report.${fmt === 'pdf' ? 'pdf' : fmt}`;
      a.click();
      URL.revokeObjectURL(urlObj);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Export failed');
    }
  };

  const handleAi = async (action: LLMAction) => {
    setAiAnchor(null);
    if (!allowAi) {
      setError(
        'AI is disabled by privacy policy. Validation itself never sends data externally.',
      );
      return;
    }
    if (privacy && !privacy.cloud_llm && health?.llm_provider === 'groq') {
      setError('Cloud LLM is blocked. Configure Ollama locally or keep LLM_PROVIDER=ollama.');
      return;
    }
    const confirmed = window.confirm(
      privacy?.cloud_llm
        ? 'AI Assist may send schema/response excerpts to the configured LLM. Continue?'
        : 'AI Assist will send schema/response excerpts only to your local Ollama. Continue?',
    );
    if (!confirmed) return;

    setAiOpen(true);
    setAiLoading(true);
    setAiContent('');
    try {
      const data = await explainWithAi({
        action,
        schemaContent: schemaText,
        responseContent: responseText,
        errors: result?.errors ?? [],
      });
      setAiContent(data.success ? data.content : data.error || 'AI request failed');
    } catch (e) {
      setAiContent(e instanceof Error ? e.message : 'AI request failed');
    } finally {
      setAiLoading(false);
    }
  };

  const onPathChange = (path: string) => {
    setSelectedPath(path);
    const match = endpoints.find((e) => e.path === path);
    if (match) {
      setSelectedMethod(match.method);
      setSelectedStatus(match.response_codes[0] ?? '200');
    }
  };

  return (
    <Box sx={{ minHeight: '100vh', pb: 6 }}>
      <AppBar position="sticky" color="transparent" elevation={0} sx={{ backdropFilter: 'blur(10px)', borderBottom: 1, borderColor: 'divider' }}>
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 700 }}>
            API Schema Validation Portal
          </Typography>
          <Tooltip title={mode === 'dark' ? 'Light mode' : 'Dark mode'}>
            <IconButton onClick={onToggleTheme} color="inherit">
              {mode === 'dark' ? <LightModeIcon /> : <DarkModeIcon />}
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ mt: 3 }}>
        <Alert severity="info" sx={{ mb: 2 }}>
          Local-only mode: schemas and API responses stay on this machine. Validation never
          calls the internet. Use <strong>Paste Text</strong> or <strong>Upload File</strong>
          {privacy?.mode === 'strict' ? ' (remote URL fetch and cloud LLM are blocked).' : '.'}
        </Alert>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 6 }}>
            <Paper variant="outlined" sx={{ p: 2, height: { md: 640 }, display: 'flex', flexDirection: 'column' }}>
              <SchemaPanel
                ref={schemaEditorRef}
                sourceType={sourceType}
                onSourceTypeChange={setSourceType}
                url={url}
                onUrlChange={setUrl}
                schemaText={schemaText}
                onSchemaTextChange={setSchemaText}
                onLoad={handleLoad}
                onFileSelected={handleSchemaFile}
                loading={loading}
                format={format}
                endpoints={endpoints}
                schemas={schemas}
                selectedPath={selectedPath}
                selectedMethod={selectedMethod}
                selectedStatus={selectedStatus}
                selectedSchemaName={selectedSchemaName}
                onPathChange={onPathChange}
                onMethodChange={setSelectedMethod}
                onStatusChange={setSelectedStatus}
                onSchemaNameChange={setSelectedSchemaName}
                editorLanguage={editorLanguage}
                allowRemoteFetch={allowRemoteFetch}
                schemaFocusLines={schemaFocusLines}
              />
            </Paper>
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <Paper variant="outlined" sx={{ p: 2, height: { md: 640 }, display: 'flex', flexDirection: 'column' }}>
              <ResponsePanel
                ref={responseEditorRef}
                responseText={responseText}
                onResponseTextChange={setResponseText}
                onFileSelected={handleResponseFile}
                errorLines={errorLines}
                focusLines={responseFocusLines}
                searchQuery={searchQuery}
                onSearchQueryChange={setSearchQuery}
              />
            </Paper>
          </Grid>
        </Grid>

        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          spacing={1.5}
          justifyContent="center"
          alignItems="center"
          sx={{ my: 3 }}
        >
          <Button
            variant="contained"
            size="large"
            startIcon={validating ? <CircularProgress size={18} color="inherit" /> : <PlayArrowIcon />}
            onClick={handleValidate}
            disabled={validating}
            sx={{ minWidth: 220 }}
          >
            Validate Response
          </Button>
          <Button
            variant="outlined"
            startIcon={<DownloadIcon />}
            disabled={!result}
            onClick={(e) => setExportAnchor(e.currentTarget)}
          >
            Export
          </Button>
          <Menu anchorEl={exportAnchor} open={Boolean(exportAnchor)} onClose={() => setExportAnchor(null)}>
            <MenuItem onClick={() => handleExport('html')}>HTML</MenuItem>
            <MenuItem onClick={() => handleExport('json')}>JSON</MenuItem>
            <MenuItem onClick={() => handleExport('pdf')}>PDF</MenuItem>
          </Menu>
          <Button
            variant="outlined"
            startIcon={<AutoAwesomeIcon />}
            onClick={(e) => setAiAnchor(e.currentTarget)}
            disabled={!allowAi}
          >
            AI Assist
          </Button>
          <Menu anchorEl={aiAnchor} open={Boolean(aiAnchor)} onClose={() => setAiAnchor(null)}>
            <MenuItem onClick={() => handleAi('explain_errors')}>Explain Errors</MenuItem>
            <MenuItem onClick={() => handleAi('suggest_fix')}>Suggest Fix</MenuItem>
            <MenuItem onClick={() => handleAi('generate_correct_json')}>Generate Correct JSON</MenuItem>
            <MenuItem onClick={() => handleAi('explain_schema')}>Explain Schema</MenuItem>
          </Menu>
        </Stack>

        <ValidationResultView
          result={result}
          selectedErrorIndex={selectedErrorIndex}
          onErrorNavigate={handleErrorNavigate}
        />
      </Container>

      <Dialog open={aiOpen} onClose={() => setAiOpen(false)} fullWidth maxWidth="md">
        <DialogTitle>AI Assistance (optional)</DialogTitle>
        <DialogContent dividers>
          {aiLoading ? (
            <Stack alignItems="center" py={4}>
              <CircularProgress />
              <Typography sx={{ mt: 2 }} color="text.secondary">
                Contacting LLM provider…
              </Typography>
            </Stack>
          ) : (
            <Typography component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: '"IBM Plex Mono", monospace', fontSize: 13 }}>
              {aiContent}
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAiOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
