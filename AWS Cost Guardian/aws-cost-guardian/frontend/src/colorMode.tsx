import { CssBaseline, ThemeProvider } from "@mui/material";
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { createAppTheme } from "./theme";

export type ColorModePreference = "light" | "dark" | "system";

const STORAGE_KEY = "aws-cost-guardian-color-mode";

type ColorModeContextValue = {
  preference: ColorModePreference;
  setPreference: (preference: ColorModePreference) => void;
};

const ColorModeContext = createContext<ColorModeContextValue | null>(null);

function storedPreference(): ColorModePreference {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark" || stored === "system") return stored;
  return "system";
}

function useSystemMode(): "light" | "dark" {
  const query = "(prefers-color-scheme: dark)";
  const [mode, setMode] = useState<"light" | "dark">(() =>
    window.matchMedia(query).matches ? "dark" : "light",
  );

  useEffect(() => {
    const media = window.matchMedia(query);
    const apply = () => setMode(media.matches ? "dark" : "light");
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, []);

  return mode;
}

export function ColorModeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreferenceState] = useState<ColorModePreference>(storedPreference);
  const systemMode = useSystemMode();
  const mode = preference === "system" ? systemMode : preference;
  const theme = useMemo(() => createAppTheme(mode), [mode]);
  const value = useMemo(
    () => ({
      preference,
      setPreference: (next: ColorModePreference) => {
        localStorage.setItem(STORAGE_KEY, next);
        setPreferenceState(next);
      },
    }),
    [preference],
  );

  return (
    <ColorModeContext.Provider value={value}>
      <ThemeProvider theme={theme}>
        <CssBaseline enableColorScheme />
        {children}
      </ThemeProvider>
    </ColorModeContext.Provider>
  );
}

export function useColorMode(): ColorModeContextValue {
  const value = useContext(ColorModeContext);
  if (!value) {
    throw new Error("Color mode is unavailable.");
  }
  return value;
}
