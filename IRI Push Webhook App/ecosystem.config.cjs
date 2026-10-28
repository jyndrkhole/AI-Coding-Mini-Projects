module.exports = {
  apps: [
    {
      name: process.env.PM2_APP_NAME || "PushNotifications-QA-Receiver",
      cwd: __dirname,
      script: "node_modules/tsx/dist/cli.mjs",
      args: "src/server.ts",
      interpreter: "node",
      instances: 1,
      exec_mode: "fork",
      watch: false,
      autorestart: true,
      max_memory_restart: "300M"
    }
  ]
};
