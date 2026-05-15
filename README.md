# OpenClaw Extension: AI Compare Hard Router

This is the publishable OpenClaw plugin package for AI Compare.

## What it does

- Intercepts search-style messages in `before_dispatch`
- Matches explicit search phrases such as `搜索 XX`, `查一下 XX`, `搜一下 XX`, `我要搜索 XX`, `search for XX`, and `look up XX`
- Also matches softer research-style phrases such as `了解一下 XX`, `研究一下 XX`, `看看 XX`, `比较一下 XX`, `learn about XX`, `look into XX`, and `compare XX`
- Calls the AI Compare GUI runner directly
- Returns the raw runner JSON payload instead of model-written summaries

## Install

### Recommended: release package

```bash
openclaw plugins install /path/to/ai-compare-hard-router.zip
openclaw plugins enable ai-compare-hard-router
openclaw gateway restart
```

### Direct from GitHub

```bash
openclaw plugins install https://github.com/taoAIGC/AIBridge.git
openclaw plugins enable ai-compare-hard-router
openclaw gateway restart
```

### Development: linked local plugin

```bash
openclaw plugins install --link <AIBRIDGE_REPO_ROOT>
openclaw plugins enable ai-compare-hard-router
openclaw gateway restart
```

## Required companion

Install the AI Compare browser extension in the same Chrome profile that OpenClaw will use. The plugin only routes requests; the browser extension does the actual multi-site execution.

If the browser extension is not installed yet, use the Chrome Web Store page:

`https://chromewebstore.google.com/detail/dkhpgbbhlnmjbkihoeniojpkggkabbbl`

## Configuration

Add plugin config to `~/.openclaw/openclaw.json`:

```json
{
  "plugins": {
    "entries": {
      "ai-compare-hard-router": {
        "enabled": true,
        "config": {
          "extensionId": "dkhpgbbhlnmjbkihoeniojpkggkabbbl",
          "browserApp": "Google Chrome",
          "timeoutMs": 190000,
          "installUrl": "https://chromewebstore.google.com/detail/dkhpgbbhlnmjbkihoeniojpkggkabbbl",
          "debugLogPath": "~/.openclaw/logs/ai-compare-hard-router.log"
        }
      }
    }
  }
}
```

For a release build, the defaults already point at the Chrome Web Store build above. For a private or unpacked browser-extension build, override `extensionId` and `installUrl` with the installed extension id and the matching onboarding page.

## Behavior notes

- If the user explicitly asks for `web search`, `google search`, `bing search`, `网页搜索`, or `新闻搜索`, this plugin does not claim the request
- If the user explicitly names sites like `ChatGPT` or `Gemini`, the plugin adds `--sites`
- Missing extension and callback timeout errors are surfaced directly instead of falling back to web search
- Successful runs are passed through as raw JSON from the bundled runner
