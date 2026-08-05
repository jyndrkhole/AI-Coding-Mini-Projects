import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Typography,
} from '@mui/material';
import { useMemo } from 'react';

interface JsonTreeProps {
  data: unknown;
  searchQuery?: string;
  label?: string;
}

function matchesSearch(key: string, value: unknown, query: string): boolean {
  if (!query) return true;
  const q = query.toLowerCase();
  if (key.toLowerCase().includes(q)) return true;
  if (typeof value === 'string' && value.toLowerCase().includes(q)) return true;
  if (typeof value === 'number' && String(value).includes(q)) return true;
  if (value && typeof value === 'object') {
    return Object.entries(value as object).some(([k, v]) => matchesSearch(k, v, query));
  }
  return false;
}

function NodeView({
  name,
  value,
  searchQuery,
  depth,
}: {
  name: string;
  value: unknown;
  searchQuery: string;
  depth: number;
}) {
  const isObject = value !== null && typeof value === 'object';
  const highlighted = Boolean(searchQuery) && name.toLowerCase().includes(searchQuery.toLowerCase());

  if (!isObject) {
    return (
      <Box sx={{ pl: depth * 1.5, py: 0.25, fontFamily: '"IBM Plex Mono", monospace', fontSize: 13 }}>
        <Typography
          component="span"
          sx={{
            color: highlighted ? 'primary.main' : 'text.secondary',
            fontWeight: highlighted ? 700 : 500,
            fontFamily: 'inherit',
            fontSize: 'inherit',
          }}
        >
          {name}
        </Typography>
        <Typography component="span" sx={{ fontFamily: 'inherit', fontSize: 'inherit' }}>
          {': '}
          {JSON.stringify(value)}
        </Typography>
      </Box>
    );
  }

  const entries = Object.entries(value as object).filter(([k, v]) =>
    matchesSearch(k, v, searchQuery),
  );

  return (
    <Accordion
      disableGutters
      elevation={0}
      defaultExpanded={depth < 2 || Boolean(searchQuery)}
      sx={{
        bgcolor: 'transparent',
        '&:before': { display: 'none' },
        pl: depth * 0.5,
      }}
    >
      <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ minHeight: 36, px: 1 }}>
        <Typography
          sx={{
            fontFamily: '"IBM Plex Mono", monospace',
            fontSize: 13,
            fontWeight: highlighted ? 700 : 500,
            color: highlighted ? 'primary.main' : 'text.primary',
          }}
        >
          {name}{' '}
          <Typography component="span" color="text.secondary" fontSize={12}>
            {Array.isArray(value) ? `[${(value as unknown[]).length}]` : `{${Object.keys(value as object).length}}`}
          </Typography>
        </Typography>
      </AccordionSummary>
      <AccordionDetails sx={{ pt: 0, pb: 0.5 }}>
        {entries.map(([k, v]) => (
          <NodeView key={k} name={k} value={v} searchQuery={searchQuery} depth={depth + 1} />
        ))}
        {entries.length === 0 && (
          <Typography variant="caption" color="text.secondary" sx={{ pl: 2 }}>
            No matching properties
          </Typography>
        )}
      </AccordionDetails>
    </Accordion>
  );
}

export default function JsonTree({ data, searchQuery = '', label = 'root' }: JsonTreeProps) {
  const parsed = useMemo(() => data, [data]);

  if (parsed === undefined || parsed === null) {
    return (
      <Typography variant="body2" color="text.secondary">
        No JSON to display
      </Typography>
    );
  }

  return <NodeView name={label} value={parsed} searchQuery={searchQuery} depth={0} />;
}
