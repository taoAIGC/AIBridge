# AIBridge: AI Compare Hard Router

AIBridge packages the AI Compare browser runner for both OpenClaw and Hermes.

## What it does

- Reuses the same AI Compare Chrome extension page for multi-site execution
- Detects search-style prompts such as `搜索 XX`, `查一下 XX`, `了解一下 XX`, `compare XX`, and `look up XX`
- Routes those requests into the local AI Compare browser workflow
- Returns per-site raw results instead of model-written summaries

## Required companion

Install the AI Compare browser extension in the same Chrome profile your runtime will open:

`https://chromewebstore.google.com/detail/dkhpgbbhlnmjbkihoeniojpkggkabbbl`

For local development, load the unpacked extension from `chrome://extensions` and make sure the loaded extension id is `hhkhgpadepocnmjfpohcmjdcgkmfnadi`.

More browser-extension help:

- [docs/install-browser-extension.md](./docs/install-browser-extension.md)

## OpenClaw install

```bash
openclaw plugins install git:github.com/taoAIGC/AIBridge --dangerously-force-unsafe-install
openclaw gateway restart
```

Why the extra flag:

- The plugin intentionally uses local runner scripts and `child_process` to open the AI Compare browser flow.
- OpenClaw's safety scanner blocks that pattern by default.
- Users should only install it from a trusted source.

### OpenClaw config

Add plugin config to `~/.openclaw/openclaw.json`:

```json
{
  "plugins": {
    "entries": {
      "ai-compare-hard-router": {
        "enabled": true,
        "config": {
          "environment": "production",
          "browserApp": "Google Chrome",
          "timeoutMs": 190000,
          "debugLogPath": "~/.openclaw/logs/ai-compare-hard-router.log"
        }
      }
    }
  }
}
```

Environment behavior:

- `environment: "production"` uses extension id `dkhpgbbhlnmjbkihoeniojpkggkabbbl`
- `environment: "development"` uses extension id `hhkhgpadepocnmjfpohcmjdcgkmfnadi`
- `extensionId` and `installUrl` still work as explicit overrides

### OpenClaw verify

```bash
openclaw tui --message '搜索一下 OpenAI'
```

## Hermes install

```bash
hermes plugins install taoAIGC/AIBridge
hermes gateway restart
```

Hermes installs this repository as the plugin:

`~/.hermes/plugins/ai-compare-hard-router`

The Hermes plugin exposes:

- tool: `ai_compare_search`
- toolset: `plugin_ai_compare_hard_router`
- hook: `pre_llm_call`

Optional Hermes-specific overrides live in:

`~/.hermes/plugins/ai-compare-hard-router/config.yaml`

The default sample is:

```yaml
environment: production
browser_app: Google Chrome
timeout_ms: 190000
```

More Hermes-specific setup details:

- [docs/install-hermes-plugin.md](./docs/install-hermes-plugin.md)

### Hermes verify

```bash
hermes chat -q '搜索一下本地论，不要做总结，不要做摘要'
hermes chat -q 'search for OpenAI, do not summarize, do not make an abstract'
```

## Usage notes

- Install the browser extension into the same Chrome profile that OpenClaw or Hermes will open.
- Make sure that Chrome profile is already logged into the target AI sites you want AI Compare to use.
- If the user explicitly asks for `web search`, `google search`, `bing search`, `网页搜索`, or `新闻搜索`, the OpenClaw router does not claim the request.
- If the user explicitly names sites like `ChatGPT`, `Claude`, or `Gemini`, the router/tool adds those sites to the run.
