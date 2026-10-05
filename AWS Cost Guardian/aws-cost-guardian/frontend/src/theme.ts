import { createTheme } from "@mui/material/styles";

export function createAppTheme(mode: "light" | "dark") {
  const dark = mode === "dark";
  return createTheme({
    palette: {
      mode,
      primary: { main: dark ? "#8fb8d6" : "#12324d" },
      secondary: { main: dark ? "#3dbe7a" : "#0f7b4c" },
      background: {
        default: dark ? "#0e1620" : "#eef2f6",
        paper: dark ? "#172433" : "#ffffff",
      },
      text: {
        primary: dark ? "#e8eef4" : "#172033",
        secondary: dark ? "#9aabba" : "#5c6b7a",
      },
      divider: dark ? "#2a3b4d" : "#e2e8f0",
    },
    typography: {
      fontFamily: '"Segoe UI", "Helvetica Neue", Arial, sans-serif',
      h4: { fontWeight: 700, letterSpacing: "-0.02em" },
      h6: { fontWeight: 700 },
    },
    shape: { borderRadius: 12 },
    components: {
      MuiCard: {
        styleOverrides: {
          root: {
            border: "1px solid",
            borderColor: dark ? "#2a3b4d" : "#e2e8f0",
            backgroundImage: "none",
            boxShadow: "none",
          },
        },
      },
    },
  });
}
