import { CssBaseline, ThemeProvider } from '@mui/material';
import { useMemo, useState } from 'react';
import ValidatorPage from './pages/ValidatorPage';
import { createAppTheme } from './theme';

export default function App() {
  const [mode, setMode] = useState<'light' | 'dark'>(() => {
    const saved = localStorage.getItem('theme-mode');
    return saved === 'dark' ? 'dark' : 'light';
  });

  const theme = useMemo(() => createAppTheme(mode), [mode]);

  const toggleTheme = () => {
    setMode((prev) => {
      const next = prev === 'light' ? 'dark' : 'light';
      localStorage.setItem('theme-mode', next);
      return next;
    });
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <ValidatorPage mode={mode} onToggleTheme={toggleTheme} />
    </ThemeProvider>
  );
}
