import { Box, Button, Chip, Stack, ToggleButton, ToggleButtonGroup, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useColorMode, type ColorModePreference } from "../colorMode";
import { apiGet } from "../services/api";
import type { Account } from "../types";
import { formatTimestamp } from "../utils/format";
import { PageHeaderProvider, usePageHeaderContent, usePageHeaderHost } from "./pageHeader";

export function AppShell() {
  return (
    <PageHeaderProvider>
      <Shell />
    </PageHeaderProvider>
  );
}

function Shell() {
  const theme = useTheme();
  const { preference, setPreference } = useColorMode();
  const queryClient = useQueryClient();
  const onDashboard = useLocation().pathname === "/";
  const pageHeader = usePageHeaderContent();
  const setActionHost = usePageHeaderHost();
  const account = useQuery({
    queryKey: ["account"],
    queryFn: () => apiGet<Account>("/api/aws/account"),
  });

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
      <Box
        component="nav"
        sx={{
          display: { xs: "none", md: "flex" },
          flexDirection: "column",
          width: 248,
          flexShrink: 0,
          position: "sticky",
          top: 0,
          height: "100vh",
          overflow: "auto",
          bgcolor: "#10283d",
          color: "#f8fafc",
          px: 2.5,
          py: 3,
        }}
      >
        <Typography variant="overline" sx={{ color: "#8fb8d6", letterSpacing: "0.14em" }}>
          FinOps
        </Typography>
        <Typography variant="h6" sx={{ lineHeight: 1.25, mb: 3 }}>
          AWS Cost Guardian
        </Typography>
        <Stack spacing={0.5}>
          <NavItem to="/" label="Dashboard" />
          <NavItem to="/costs" label="Cost Explorer" />
          <NavItem to="/resources" label="Resources" />
          <NavItem to="/advisor" label="Advisor" />
          <NavItem to="/simulate" label="Simulate" />
          <NavItem to="/report" label="Report" />
        </Stack>
        <Box sx={{ mt: "auto", pt: 3 }}>
          <AccountDetails account={account.data} error={account.isError ? account.error.message : undefined} loading={!account.data && !account.isError} />
        </Box>
      </Box>
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Box
          component="header"
          sx={{
            px: { xs: 2, md: 4 },
            py: 1,
            borderBottom: 1,
            borderColor: "divider",
            bgcolor: "background.paper",
          }}
        >
          <Stack spacing={1}>
            <Box sx={{ display: { md: "none" } }}>
              <Typography variant="h6" sx={{ mb: 0.5 }}>
                AWS Cost Guardian
              </Typography>
              <Stack direction="row" spacing={2} useFlexGap flexWrap="wrap">
                <NavLink to="/" style={{ color: theme.palette.primary.main }}>
                  Dashboard
                </NavLink>
                <NavLink to="/costs" style={{ color: theme.palette.primary.main }}>
                  Cost Explorer
                </NavLink>
                <NavLink to="/resources" style={{ color: theme.palette.primary.main }}>
                  Resources
                </NavLink>
                <NavLink to="/advisor" style={{ color: theme.palette.primary.main }}>
                  Advisor
                </NavLink>
              </Stack>
            </Box>
            <Box sx={{ display: "flex", flexDirection: { xs: "column", md: "row" }, alignItems: { md: "center" }, gap: 1 }}>
              <Box sx={{ minWidth: 0, flex: 1 }}>
                {pageHeader ? (
                  <>
                    <Typography variant="h5" sx={{ lineHeight: 1.15, fontWeight: 600 }}>
                      {pageHeader.title}
                    </Typography>
                    {pageHeader.subtitle ? (
                      <Typography variant="body2" color="text.secondary">
                        {pageHeader.subtitle}
                      </Typography>
                    ) : null}
                  </>
                ) : null}
              </Box>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "flex-end",
                  gap: 1,
                  flexShrink: 0,
                  width: { xs: "100%", md: "auto" },
                  ml: { md: "auto" },
                }}
              >
                <Box sx={{ display: { md: "none" }, minWidth: 0, mr: "auto" }}>
                  <AccountDetails
                    account={account.data}
                    error={account.isError ? account.error.message : undefined}
                    loading={!account.data && !account.isError}
                    compact
                  />
                </Box>
                <Box ref={setActionHost} sx={{ display: "flex", alignItems: "center" }} />
                {onDashboard ? (
                  <Button size="small" variant="outlined" onClick={() => void queryClient.invalidateQueries()}>
                    Reload
                  </Button>
                ) : null}
                <ColorModeToggle preference={preference} onChange={setPreference} />
                {account.data?.mock_aws ? <Chip label="DEMO MODE" color="warning" size="small" sx={{ display: { md: "none" } }} /> : null}
              </Box>
            </Box>
          </Stack>
        </Box>
        <Box component="main" sx={{ px: { xs: 2, md: 4 }, pt: 1.5, pb: 3 }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}

function AccountDetails({
  account,
  error,
  loading,
  compact = false,
}: {
  account?: Account;
  error?: string;
  loading?: boolean;
  compact?: boolean;
}) {
  if (!account) {
    return (
      <Typography variant="body2" color={compact ? "text.secondary" : "#c5d4e0"}>
        {error ?? (loading ? "Loading account" : "")}
      </Typography>
    );
  }
  if (compact) {
    return (
      <Box>
        <Typography variant="body2">
          Account {account.aws_account_id}
          {account.account_alias ? ` · ${account.account_alias}` : ""} · {account.region}
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
          Last scan {formatTimestamp(account.last_scan_at)}
        </Typography>
      </Box>
    );
  }
  return (
    <Stack spacing={0.75}>
      <Typography variant="caption" sx={{ color: "#8fb8d6", letterSpacing: "0.08em" }}>
        ACCOUNT
      </Typography>
      <Typography variant="body2" sx={{ fontWeight: 700 }}>
        {account.aws_account_id}
        {account.account_alias ? ` · ${account.account_alias}` : ""}
      </Typography>
      <Typography variant="caption" sx={{ color: "#c5d4e0" }}>
        {account.region}
      </Typography>
      <Typography variant="caption" sx={{ color: "#9aabba" }}>
        Last scan {formatTimestamp(account.last_scan_at)}
      </Typography>
      {account.mock_aws ? <Chip label="DEMO MODE" color="warning" size="small" sx={{ alignSelf: "flex-start", mt: 0.5 }} /> : null}
    </Stack>
  );
}

function ColorModeToggle({
  preference,
  onChange,
}: {
  preference: ColorModePreference;
  onChange: (preference: ColorModePreference) => void;
}) {
  return (
    <ToggleButtonGroup
      exclusive
      size="small"
      value={preference}
      onChange={(_event, value: ColorModePreference | null) => {
        if (value) onChange(value);
      }}
      aria-label="Color mode"
    >
      <ToggleButton value="light" aria-label="Light">
        <ModeIcon>
          <circle cx="12" cy="12" r="3.2" />
          <path d="M12 3.5v2.2M12 18.3v2.2M3.5 12h2.2M18.3 12h2.2M6 6l1.6 1.6M16.4 16.4 18 18M18 6l-1.6 1.6M7.6 16.4 6 18" />
        </ModeIcon>
      </ToggleButton>
      <ToggleButton value="dark" aria-label="Dark">
        <ModeIcon>
          <path d="M15.5 14.8A6.2 6.2 0 0 1 9.2 8.5 6.2 6.2 0 1 0 15.5 14.8Z" />
        </ModeIcon>
      </ToggleButton>
      <ToggleButton value="system" aria-label="System">
        <ModeIcon>
          <rect x="4" y="5" width="16" height="11" rx="1.6" />
          <path d="M9 19.5h6M12 16v3.5" />
        </ModeIcon>
      </ToggleButton>
    </ToggleButtonGroup>
  );
}

function ModeIcon({ children }: { children: ReactNode }) {
  return (
    <Box
      component="svg"
      viewBox="0 0 24 24"
      aria-hidden
      sx={{ width: 18, height: 18, display: "block" }}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </Box>
  );
}

function NavItem({ to, label }: { to: string; label: string }) {
  return (
    <NavLink to={to} style={{ textDecoration: "none", color: "inherit" }}>
      {({ isActive }) => (
        <Stack
          direction="row"
          spacing={1.25}
          alignItems="center"
          sx={{ px: 1.25, py: 1, borderRadius: 2, bgcolor: isActive ? "rgba(255,255,255,0.08)" : "transparent" }}
        >
          <Box sx={{ width: 8, height: 8, borderRadius: "50%", bgcolor: isActive ? "#8fd4b5" : "transparent" }} />
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {label}
          </Typography>
        </Stack>
      )}
    </NavLink>
  );
}
