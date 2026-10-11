const path = require("path");

const python = process.platform === "win32"
  ? path.join(__dirname, ".venv", "Scripts", "python.exe")
  : path.join(__dirname, ".venv", "bin", "python");

module.exports = {
  apps: [
    {
      name: "case-viewer",
      cwd: __dirname,
      script: python,
      args: "-m streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true",
      interpreter: "none",
      autorestart: true,
      max_restarts: 10,
      min_uptime: "10s",
    },
  ],
};
