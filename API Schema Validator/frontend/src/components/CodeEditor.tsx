import Editor, { OnMount } from '@monaco-editor/react';
import { Box, useTheme } from '@mui/material';
import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
} from 'react';
import type { editor as MonacoEditor } from 'monaco-editor';

export interface CodeEditorHandle {
  /** Scroll to line, select it, and flash a focus decoration. */
  revealLine: (line: number) => void;
}

interface CodeEditorProps {
  value: string;
  onChange?: (value: string) => void;
  language?: string;
  readOnly?: boolean;
  height?: string | number;
  errorLines?: number[];
  /** Extra lines to spotlight (e.g. currently selected error). */
  focusLines?: number[];
}

function clampLine(ed: MonacoEditor.IStandaloneCodeEditor, line: number): number {
  const maxLine = ed.getModel()?.getLineCount() ?? 1;
  return Math.min(Math.max(1, line), maxLine);
}

const CodeEditor = forwardRef<CodeEditorHandle, CodeEditorProps>(
  function CodeEditor(
    {
      value,
      onChange,
      language = 'json',
      readOnly = false,
      height = '100%',
      errorLines = [],
      focusLines = [],
    },
    ref,
  ) {
    const theme = useTheme();
    const isDark = theme.palette.mode === 'dark';
    const monacoTheme = isDark ? 'vs-dark' : 'light';
    const editorRef = useRef<MonacoEditor.IStandaloneCodeEditor | null>(null);
    const decorationIds = useRef<string[]>([]);
    const focusDecorationIds = useRef<string[]>([]);

    const options = useMemo(
      () => ({
        minimap: { enabled: false },
        fontSize: 13,
        fontFamily: '"IBM Plex Mono", ui-monospace, monospace',
        lineNumbers: 'on' as const,
        scrollBeyondLastLine: false,
        wordWrap: 'on' as const,
        automaticLayout: true,
        readOnly,
        glyphMargin: true,
        padding: { top: 8, bottom: 8 },
        renderLineHighlight: 'line' as const,
      }),
      [readOnly],
    );

    const applyFocus = (line: number) => {
      const ed = editorRef.current;
      if (!ed || line < 1) return;
      const safe = clampLine(ed, line);
      const maxCol = ed.getModel()?.getLineMaxColumn(safe) ?? 1;
      const range = {
        startLineNumber: safe,
        startColumn: 1,
        endLineNumber: safe,
        endColumn: maxCol,
      };

      ed.revealLineInCenter(safe);
      ed.setPosition({ lineNumber: safe, column: 1 });
      ed.setSelection(range);

      focusDecorationIds.current = ed.deltaDecorations(focusDecorationIds.current, [
        {
          range,
          options: {
            isWholeLine: true,
            className: 'schema-focus-line',
            linesDecorationsClassName: 'schema-focus-gutter',
          },
        },
      ]);

      window.setTimeout(() => {
        if (!editorRef.current) return;
        focusDecorationIds.current = editorRef.current.deltaDecorations(
          focusDecorationIds.current,
          [],
        );
      }, 2500);
    };

    useImperativeHandle(
      ref,
      () => ({
        revealLine: (line: number) => applyFocus(line),
      }),
      // applyFocus uses editorRef; recreate rarely
      // eslint-disable-next-line react-hooks/exhaustive-deps
      [],
    );

    // Auto-jump whenever focusLines changes — more reliable than imperative-only calls
    useEffect(() => {
      const line = focusLines.find((n) => Number.isFinite(n) && n > 0);
      if (line) {
        // Wait a tick for layout after state update
        const t = window.setTimeout(() => applyFocus(line), 30);
        return () => window.clearTimeout(t);
      }
      return undefined;
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [focusLines.join(','), value]);

    useEffect(() => {
      const ed = editorRef.current;
      if (!ed) return;

      const uniqueLines = [
        ...new Set(
          [...errorLines, ...focusLines].filter((n) => Number.isFinite(n) && n > 0),
        ),
      ];
      const model = ed.getModel();
      const decorations = uniqueLines.map((line) => {
        const maxColumn = model?.getLineMaxColumn(line) ?? 1;
        const isFocus = focusLines.includes(line);
        return {
          range: {
            startLineNumber: line,
            startColumn: 1,
            endLineNumber: line,
            endColumn: maxColumn,
          },
          options: {
            isWholeLine: true,
            className: isFocus ? 'schema-focus-line' : 'schema-error-line',
            linesDecorationsClassName: isFocus
              ? 'schema-focus-gutter'
              : 'schema-error-line-gutter',
            glyphMarginClassName: 'schema-error-glyph',
            inlineClassName: 'schema-error-inline',
            overviewRuler: {
              color: isDark ? '#ff8a80' : '#c62828',
              position: 1, // OverviewRulerLane.Center-ish; numeric avoids monaco import
            },
          },
        };
      });
      decorationIds.current = ed.deltaDecorations(decorationIds.current, decorations);
    }, [errorLines, focusLines, value, isDark]);

    const handleMount: OnMount = (editor) => {
      editorRef.current = editor;
      const line = focusLines.find((n) => Number.isFinite(n) && n > 0);
      if (line) applyFocus(line);
    };

    return (
      <Box
        sx={{
          height,
          border: 1,
          borderColor: 'divider',
          borderRadius: 1,
          overflow: 'hidden',
          '& .schema-error-line': {
            backgroundColor: isDark
              ? 'rgba(255, 138, 128, 0.10) !important'
              : 'rgba(198, 40, 40, 0.07) !important',
          },
          '& .schema-focus-line': {
            backgroundColor: isDark
              ? 'rgba(255, 213, 79, 0.16) !important'
              : 'rgba(255, 193, 7, 0.18) !important',
            outline: isDark
              ? '1px solid rgba(255, 213, 79, 0.45)'
              : '1px solid rgba(245, 124, 0, 0.35)',
          },
          '& .schema-error-line-gutter': {
            background: isDark ? '#ff8a80' : '#c62828',
            width: '3px !important',
            marginLeft: '3px',
          },
          '& .schema-focus-gutter': {
            background: isDark ? '#ffd54f' : '#ef6c00',
            width: '4px !important',
            marginLeft: '3px',
          },
          '& .schema-error-glyph': {
            background: isDark ? '#ff8a80' : '#c62828',
            width: '4px !important',
            marginLeft: '3px',
            borderRadius: '1px',
          },
          '& .schema-error-inline': {
            textDecoration: 'underline wavy',
            textDecorationColor: isDark ? '#ff8a80' : '#c62828',
            textUnderlineOffset: '2px',
          },
        }}
      >
        <Editor
          height="100%"
          language={language}
          theme={monacoTheme}
          value={value}
          options={options}
          onChange={(v) => onChange?.(v ?? '')}
          onMount={handleMount}
        />
      </Box>
    );
  },
);

export default CodeEditor;
