import UploadFileIcon from '@mui/icons-material/UploadFile';
import { Box, Button, Stack, TextField, Typography } from '@mui/material';
import { forwardRef, useMemo, useRef } from 'react';
import CodeEditor, { type CodeEditorHandle } from './CodeEditor';
import JsonTree from './JsonTree';

interface Props {
  responseText: string;
  onResponseTextChange: (v: string) => void;
  onFileSelected: (file: File) => void;
  errorLines: number[];
  focusLines?: number[];
  searchQuery: string;
  onSearchQueryChange: (v: string) => void;
}

const ResponsePanel = forwardRef<CodeEditorHandle, Props>(function ResponsePanel(
  {
    responseText,
    onResponseTextChange,
    onFileSelected,
    errorLines,
    focusLines,
    searchQuery,
    onSearchQueryChange,
  },
  ref,
) {
  const fileRef = useRef<HTMLInputElement>(null);

  const treeData = useMemo(() => {
    try {
      return JSON.parse(responseText);
    } catch {
      return null;
    }
  }, [responseText]);

  return (
    <Stack spacing={1.5} sx={{ height: '100%' }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Typography variant="h6">API Response</Typography>
        <Stack direction="row" spacing={1}>
          <input
            ref={fileRef}
            hidden
            type="file"
            accept=".json,application/json"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onFileSelected(f);
            }}
          />
          <Button
            size="small"
            variant="outlined"
            startIcon={<UploadFileIcon />}
            onClick={() => fileRef.current?.click()}
          >
            Upload JSON
          </Button>
        </Stack>
      </Stack>

      <TextField
        size="small"
        label="Search property names"
        placeholder="e.g. email, status, id"
        value={searchQuery}
        onChange={(e) => onSearchQueryChange(e.target.value)}
      />

      <Box sx={{ flex: 1, minHeight: 280 }} id="response-editor-panel">
        <CodeEditor
          ref={ref}
          value={responseText}
          onChange={onResponseTextChange}
          language="json"
          height="100%"
          errorLines={errorLines}
          focusLines={focusLines}
        />
      </Box>

      <Box
        sx={{
          maxHeight: 180,
          overflow: 'auto',
          border: 1,
          borderColor: 'divider',
          borderRadius: 1,
          p: 1,
        }}
      >
        <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
          JSON Tree
        </Typography>
        <JsonTree data={treeData} searchQuery={searchQuery} label="$" />
      </Box>
    </Stack>
  );
});

export default ResponsePanel;
