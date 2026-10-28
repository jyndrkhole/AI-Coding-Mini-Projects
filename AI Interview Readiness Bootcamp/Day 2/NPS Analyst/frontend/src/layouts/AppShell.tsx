import ArticleOutlinedIcon from "@mui/icons-material/ArticleOutlined";
import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";
import ForumOutlinedIcon from "@mui/icons-material/ForumOutlined";
import InsightsOutlinedIcon from "@mui/icons-material/InsightsOutlined";
import PaymentsOutlinedIcon from "@mui/icons-material/PaymentsOutlined";
import PhoneOutlinedIcon from "@mui/icons-material/PhoneOutlined";
import ScienceOutlinedIcon from "@mui/icons-material/ScienceOutlined";
import TimelineOutlinedIcon from "@mui/icons-material/TimelineOutlined";
import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import MenuIcon from "@mui/icons-material/Menu";
import { AppBar, Box, Drawer, IconButton, List, ListItemButton, ListItemIcon, ListItemText, Toolbar, Typography, useMediaQuery, useTheme } from "@mui/material";
import { ReactNode, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

const NAV = [
  { path: "/", label: "Executive Overview", icon: <InsightsOutlinedIcon /> },
  { path: "/trends", label: "NPS Trends", icon: <TimelineOutlinedIcon /> },
  { path: "/voice", label: "Voice of Customer", icon: <ForumOutlinedIcon /> },
  { path: "/revenue", label: "Revenue at Risk", icon: <PaymentsOutlinedIcon /> },
  { path: "/callbacks", label: "Customer Callbacks", icon: <PhoneOutlinedIcon /> },
  { path: "/simulations", label: "Simulations", icon: <ScienceOutlinedIcon /> },
  { path: "/trace", label: "AI Analysis Trace", icon: <AccountTreeOutlinedIcon /> },
  { path: "/report", label: "Leadership Report", icon: <ArticleOutlinedIcon /> },
  { path: "/quality", label: "Data Quality", icon: <FactCheckOutlinedIcon /> },
];

export function AppShell({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const wide = useMediaQuery(theme.breakpoints.up("md"));
  const [open, setOpen] = useState(false);
  const drawer = (
    <Box sx={{ width: 260 }}>
      <Box sx={{ px: 2, py: 2.5 }}>
        <Typography variant="overline" color="text.secondary">
          Future with Shivank Bank
        </Typography>
        <Typography variant="h6">NPS Analyst</Typography>
      </Box>
      <List>
        {NAV.map((item) => (
          <ListItemButton
            key={item.path}
            selected={location.pathname === item.path}
            onClick={() => {
              navigate(item.path);
              setOpen(false);
            }}
          >
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>
    </Box>
  );
  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      {wide ? (
        <Drawer variant="permanent" sx={{ "& .MuiDrawer-paper": { position: "relative" } }}>
          {drawer}
        </Drawer>
      ) : (
        <Drawer open={open} onClose={() => setOpen(false)}>
          {drawer}
        </Drawer>
      )}
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <AppBar position="sticky" color="inherit" elevation={0} sx={{ borderBottom: "1px solid #e6ebf2" }}>
          <Toolbar>
            {wide ? null : (
              <IconButton edge="start" onClick={() => setOpen(true)} aria-label="Open navigation">
                <MenuIcon />
              </IconButton>
            )}
            <Typography sx={{ flex: 1 }} color="text.secondary">
              Fictional survey. Recommendations only. No customer is contacted.
            </Typography>
          </Toolbar>
        </AppBar>
        <Box sx={{ p: { xs: 2, md: 4 }, maxWidth: 1200 }}>{children}</Box>
      </Box>
    </Box>
  );
}
