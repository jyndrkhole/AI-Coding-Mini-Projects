export function renderPortalLoginPage(errorMessage = ""): string {
  const error = errorMessage
    ? `<div class="flash">${escapeHtml(errorMessage)}</div>`
    : "";
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Sign in · Push Notifications Test Portal</title>
    <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
    <script>
      document.documentElement.setAttribute(
        "data-theme",
        localStorage.getItem("portal-theme") === "dark" ? "dark" : "light"
      );
    </script>
    <style>
      :root, [data-theme="light"] {
        --navy: #16324f;
        --teal: #0f766e;
        --paper: #f3f5f8;
        --card: #ffffff;
        --line: #d7dee8;
        --text: #1c2b3a;
        --muted: #5c6f82;
        --danger: #b42318;
        --danger-bg: #fef3f2;
        --btn-secondary-bg: #ffffff;
        color-scheme: light;
      }
      [data-theme="dark"] {
        --navy: #7dd3fc;
        --teal: #2dd4bf;
        --paper: #0b1220;
        --card: #151d2e;
        --line: #2a3a52;
        --text: #e8eef4;
        --muted: #9aa8b8;
        --danger: #f97066;
        --danger-bg: #3b1511;
        --btn-secondary-bg: #1a2436;
        color-scheme: dark;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: "Segoe UI", sans-serif;
        background: var(--paper);
        color: var(--text);
      }
      form {
        width: 100%;
        max-width: 420px;
        margin: 24px;
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 28px;
      }
      .kicker {
        margin: 0 0 6px;
        font-size: 11px;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--teal);
      }
      h1 { margin: 0; font-size: 22px; }
      label { display: block; margin: 14px 0 6px; font-weight: 600; font-size: 14px; }
      input {
        width: 100%;
        padding: 10px 12px;
        border: 1px solid var(--line);
        border-radius: 8px;
        font: inherit;
        background: var(--card);
        color: var(--text);
      }
      .actions {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: 20px;
      }
      .submit {
        padding: 10px 16px;
        border: 0;
        border-radius: 8px;
        background: #16324f;
        color: #fff;
        font: inherit;
        font-weight: 600;
        cursor: pointer;
      }
      [data-theme="dark"] .submit {
        background: #0f766e;
      }
      .theme-toggle {
        border: 1px solid var(--line);
        background: var(--btn-secondary-bg);
        color: var(--text);
        border-radius: 8px;
        width: 36px;
        height: 36px;
        padding: 0;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        overflow: hidden;
      }
      .theme-toggle svg { display: none; }
      [data-theme="light"] #icon-moon,
      [data-theme="dark"] #icon-sun { display: block; }
      .flash {
        background: var(--danger-bg);
        color: var(--danger);
        padding: 10px 12px;
        border-radius: 8px;
        margin-bottom: 12px;
      }
    </style>
  </head>
  <body>
    <form method="post" action="/api/portal/login">
      <p class="kicker">Application Status</p>
      <h1>Push Notifications Test Portal</h1>
      ${error}
      <label for="username">Username</label>
      <input id="username" name="username" value="admin" autocomplete="username" />
      <label for="password">Password</label>
      <input id="password" name="password" type="password" autocomplete="current-password" />
      <div class="actions">
        <button class="submit" type="submit">Sign in</button>
        <button class="theme-toggle" id="theme-toggle" type="button" aria-label="Switch theme" title="Switch theme">
          <svg id="icon-moon" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <path fill="currentColor" d="M21 14.3A9 9 0 1 1 9.7 3a7 7 0 1 0 11.3 11.3Z" />
          </svg>
          <svg id="icon-sun" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <circle cx="12" cy="12" r="4" fill="currentColor" />
            <path d="M12 3v2m0 14v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M3 12h2m14 0h2M4.9 19.1l1.4-1.4m11.4-11.4 1.4-1.4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" fill="none" />
          </svg>
        </button>
      </div>
    </form>
    <script>
      (function () {
        var key = "portal-theme";
        var button = document.getElementById("theme-toggle");
        function current() {
          return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
        }
        function apply(theme) {
          document.documentElement.setAttribute("data-theme", theme);
          document.documentElement.style.colorScheme = theme;
          localStorage.setItem(key, theme);
          var next = theme === "light" ? "dark" : "light";
          button.setAttribute("aria-label", "Switch to " + next + " theme");
          button.setAttribute("title", "Switch to " + next + " theme");
        }
        apply(current());
        button.addEventListener("click", function () {
          apply(current() === "light" ? "dark" : "light");
        });
      })();
    </script>
  </body>
</html>`;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
