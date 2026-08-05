import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import {
  Box,
  Chip,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from '@mui/material';
import type { ValidationErrorDetail, ValidationResponse } from '../types';

interface Props {
  result: ValidationResponse | null;
  selectedErrorIndex?: number | null;
  onErrorNavigate?: (error: ValidationErrorDetail, index: number) => void;
}

export default function ValidationResultView({
  result,
  selectedErrorIndex = null,
  onErrorNavigate,
}: Props) {
  if (!result) {
    return (
      <Paper variant="outlined" sx={{ p: 3 }}>
        <Typography color="text.secondary">
          Run validation to see a summary and detailed errors here.
        </Typography>
      </Paper>
    );
  }

  const pass = result.valid;

  return (
    <Stack spacing={2}>
      <Paper
        variant="outlined"
        sx={{
          p: 2.5,
          borderColor: pass ? 'success.main' : 'error.main',
          bgcolor: pass ? 'success.main' : 'error.main',
          color: pass ? 'success.contrastText' : 'error.contrastText',
          backgroundImage: pass
            ? 'linear-gradient(135deg, rgba(10,122,53,0.95), rgba(15,107,76,0.9))'
            : 'linear-gradient(135deg, rgba(176,0,32,0.95), rgba(140,20,40,0.9))',
        }}
      >
        <Stack direction="row" spacing={1.5} alignItems="center">
          {pass ? <CheckCircleOutlineIcon fontSize="large" /> : <ErrorOutlineIcon fontSize="large" />}
          <Box>
            <Typography variant="h5">{pass ? 'PASS' : 'FAIL'}</Typography>
            <Typography variant="body2" sx={{ opacity: 0.9 }}>
              {result.message}
            </Typography>
          </Box>
        </Stack>
      </Paper>

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip label={`Total: ${result.summary.total_errors}`} />
        <Chip label={`Missing: ${result.summary.missing_fields}`} variant="outlined" />
        <Chip label={`Types: ${result.summary.invalid_types}`} variant="outlined" />
        <Chip label={`Enums: ${result.summary.enum_violations}`} variant="outlined" />
        <Chip label={`Extra props: ${result.summary.additional_properties}`} variant="outlined" />
        <Chip label={`Formats: ${result.summary.invalid_formats}`} variant="outlined" />
      </Stack>

      {result.errors.length > 0 && (
        <Paper variant="outlined" sx={{ overflow: 'auto' }}>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', px: 2, pt: 1.5 }}>
            Click a category (or row) to jump to the matching place in the schema YAML/JSON and API response.
          </Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Category</TableCell>
                <TableCell>Message</TableCell>
                <TableCell>JSON Path</TableCell>
                <TableCell>Schema Path</TableCell>
                <TableCell>Line</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {result.errors.map((e, idx) => {
                const selected = selectedErrorIndex === idx;
                return (
                  <TableRow
                    key={`${e.json_path}-${idx}`}
                    hover
                    selected={selected}
                    onClick={() => onErrorNavigate?.(e, idx)}
                    sx={{
                      cursor: onErrorNavigate ? 'pointer' : 'default',
                      '&.Mui-selected': {
                        bgcolor: (t) =>
                          t.palette.mode === 'dark'
                            ? 'rgba(255, 213, 79, 0.08)'
                            : 'rgba(255, 193, 7, 0.12)',
                      },
                    }}
                  >
                    <TableCell>
                      <Tooltip title="Jump to schema & response location">
                        <Chip
                          size="small"
                          label={e.category}
                          color="error"
                          variant={selected ? 'filled' : 'outlined'}
                          onClick={(ev) => {
                            ev.stopPropagation();
                            onErrorNavigate?.(e, idx);
                          }}
                          sx={{ cursor: 'pointer' }}
                        />
                      </Tooltip>
                    </TableCell>
                    <TableCell sx={{ maxWidth: 360 }}>{e.message}</TableCell>
                    <TableCell>
                      <code>{e.json_path}</code>
                    </TableCell>
                    <TableCell>
                      <code>{e.schema_path}</code>
                    </TableCell>
                    <TableCell>{e.line_number ?? '—'}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Paper>
      )}
    </Stack>
  );
}
