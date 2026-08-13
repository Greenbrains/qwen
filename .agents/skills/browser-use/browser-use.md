# browser-use

**browser-use** — фреймворк браузерной автоматизации под управлением LLM: агент открывает страницы, кликает, заполняет формы. Есть документация для подключения в Cursor / Claude Code (Agents.md), облако Browser Use Cloud.

## Стек
Python, зависимости по README; опционально API-ключи и браузерный рантайм.

## Лицензия
MIT (см. файл LICENSE в репозитории).

---

## Инструкция

**Name:** browser-use  
**Description:** Automates browser interactions for web testing, form filling, screenshots, and data extraction. Use when the user needs to navigate websites, interact with web pages, fill forms, take screenshots, or extract information from web pages.  
**Allowed tools:** Bash(browser-use:*)

---

## Browser Automation with browser-use CLI

The browser-use command provides fast, persistent browser automation. A background daemon keeps the browser open across commands, giving ~50ms latency per call.

### Prerequisites

```bash
browser-use doctor    # Verify installation
```

For setup details, see https://github.com/browser-use/browser-use/blob/main/browser_use/skill_cli/README.md

---

## Core Workflow

1. **Navigate:** `browser-use open <url>` — launches headless browser and opens page
2. **Inspect:** `browser-use state` — returns clickable elements with indices
3. **Interact:** use indices from state (`browser-use click 5`, `browser-use input 3 "text"`)
4. **Verify:** `browser-use state` or `browser-use screenshot` to confirm
5. **Repeat:** browser stays open between commands

If a command fails, run `browser-use close` first to clear any broken session, then retry.

To use the user's existing Chrome (preserves logins/cookies): run `browser-use connect` first.  
To use a cloud browser instead: run `browser-use cloud connect` first. After either, commands work the same way.

---

## Browser Modes

```bash
browser-use open <url>                         # Default: headless Chromium (no setup needed)
browser-use --headed open <url>                # Visible window (for debugging)
browser-use connect                            # Connect to user's Chrome (preserves logins/cookies)
browser-use cloud connect                      # Cloud browser (zero-config, requires API key)
browser-use --profile "Default" open <url>     # Real Chrome with specific profile
```

After `connect` or `cloud connect`, all subsequent commands go to that browser — no extra flags needed.

---

## Commands

### Navigation
```bash
browser-use open <url>                    # Navigate to URL
browser-use back                          # Go back in history
browser-use scroll down                   # Scroll down (--amount N for pixels)
browser-use scroll up                     # Scroll up
browser-use tab list                      # List all tabs
browser-use tab new [url]                 # Open a new tab (blank or with URL)
browser-use tab switch <index>            # Switch to tab by index
browser-use tab close <index> [index...]  # Close one or more tabs
```

### Page State — always run state first to get element indices
```bash
browser-use state                         # URL, title, clickable elements with indices
browser-use screenshot [path.png]         # Screenshot (base64 if no path, --full for full page)
```

For advanced browser control (CDP, device emulation, tab activation), see `references/cdp-python.md`.

---

## Cloud API

```bash
browser-use cloud connect                 # Provision cloud browser and connect (zero-config)
browser-use cloud login <api-key>         # Save API key (or set BROWSER_USE_API_KEY)
browser-use cloud logout                  # Remove API key
browser-use cloud v2 GET /browsers        # REST passthrough (v2 or v3)
browser-use cloud v2 POST /tasks '{"task":"...","url":"..."}'
browser-use cloud v2 poll <task-id>       # Poll task until done
browser-use cloud v2 --help               # Show API endpoints
```

`cloud connect` provisions a cloud browser with a persistent profile (auto-created on first use), connects via CDP, and prints a live URL. `browser-use close` disconnects AND stops the cloud browser. For custom browser settings (proxy, timeout, specific profile), use `cloud v2 POST /browsers` directly with the desired parameters.

### Agent Self-Registration

Only use this if you don't already have an API key (check `browser-use doctor` to see if api_key is set). If already logged in, skip this entirely.

```bash
browser-use cloud signup
browser-use cloud signup --verify <challenge-id> <answer>
browser-use cloud signup --claim
```

---

## Tunnels

```bash
browser-use tunnel <port>                 # Start Cloudflare tunnel (idempotent)
browser-use tunnel list                   # Show active tunnels
browser-use tunnel stop <port>            # Stop tunnel
browser-use tunnel stop --all             # Stop all tunnels
```

---

## Profile Management

```bash
browser-use profile list                  # List detected browsers and profiles
browser-use profile sync --all            # Sync profiles to cloud
browser-use profile update                # Download/update profile-use binary
```

---

## Command Chaining

Commands can be chained with `&&`. The browser persists via the daemon, so chaining is safe and efficient.

```bash
browser-use open https://example.com && browser-use state
browser-use input 5 "user@example.com" && browser-use input 6 "password" && browser-use click 7
```

Chain when you don't need intermediate output. Run separately when you need to parse `state` to discover indices first.

---

## Common Workflows

### Authenticated Browsing

When a task requires an authenticated site (Gmail, GitHub, internal tools), use Chrome profiles:

```bash
browser-use profile list                           # Check available profiles
# Ask the user which profile to use, then:
browser-use --profile "Default" open https://github.com  # Already logged in
```

### Exposing Local Dev Servers

```bash
browser-use tunnel 3000                            # → https://abc.trycloudflare.com
browser-use open https://abc.trycloudflare.com     # Browse the tunnel
```

---

## Multiple Browsers

For subagent workflows or running multiple browsers in parallel, use `--session NAME`. Each session gets its own browser. See `references/multi-session.md`.

---

## Configuration

```bash
browser-use config list                            # Show all config values
browser-use config set cloud_connect_proxy jp      # Set a value
browser-use config get cloud_connect_proxy         # Get a value
browser-use config unset cloud_connect_timeout     # Remove a value
browser-use doctor                                 # Shows config + diagnostics
browser-use setup                                  # Interactive post-install setup
```

Config stored in `~/.browser-use/config.json`.

---

## Global Options

- `--headed` — visible browser window
- `--profile [NAME]` — use specific Chrome profile
- `--cdp-url <url>` — connect to CDP endpoint (http:// or ws://)
- `--session NAME` — named session for parallel browsers
- `--json` — output as JSON
- `--mcp` — MCP mode

---

## Tips

- Always run `state` first to get element indices
- Use `--headed` for debugging
- Aliases: `bu`, `browser`, `browseruse` all work
- Use `browser-use close` to clean up

---

## Troubleshooting

- If stuck: `browser-use close`
- For debugging: `browser-use --headed open <url>`
- If scroll fails: `browser-use scroll down`
- Check state: `browser-use state`
- Verify install: `browser-use doctor`

---

## Cleanup

```bash
browser-use close                 # Close browser session
browser-use tunnel stop --all     # Stop tunnels (if any)
```
