import { createTheme, PaletteMode } from '@mui/material';

const shared = {
  typography: {
    fontFamily: '"Outfit", "Segoe UI", sans-serif',
    h1: { fontWeight: 700, letterSpacing: '-0.02em' },
    h2: { fontWeight: 600, letterSpacing: '-0.01em' },
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
    button: { textTransform: 'none' as const, fontWeight: 600 },
  },
  shape: { borderRadius: 10 },
};

export function createAppTheme(mode: PaletteMode) {
  const isDark = mode === 'dark';
  return createTheme({
    ...shared,
    palette: {
      mode,
      primary: {
        main: isDark ? '#5ec8a2' : '#0f6b4c',
        contrastText: isDark ? '#06261c' : '#ffffff',
      },
      secondary: {
        main: isDark ? '#8ab4f8' : '#1a4a8a',
      },
      success: { main: isDark ? '#4caf7a' : '#0a7a35' },
      error: { main: isDark ? '#f28b82' : '#b00020' },
      background: {
        default: isDark ? '#0f1419' : '#eef2ef',
        paper: isDark ? '#1a222b' : '#ffffff',
      },
      divider: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(15,40,30,0.1)',
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            backgroundImage: isDark
              ? 'radial-gradient(1200px 500px at 10% -10%, rgba(94,200,162,0.12), transparent), radial-gradient(900px 400px at 100% 0%, rgba(138,180,248,0.1), transparent)'
              : 'radial-gradient(1200px 500px at 10% -10%, rgba(15,107,76,0.08), transparent), radial-gradient(900px 400px at 100% 0%, rgba(26,74,138,0.06), transparent)',
            backgroundAttachment: 'fixed',
          },
          code: {
            fontFamily: '"IBM Plex Mono", ui-monospace, monospace',
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: 'none',
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: 8,
          },
        },
      },
    },
  });
}
