# AI Compare Hermes Plugin

This repository now installs as a Hermes plugin named `ai-compare-hard-router`.

## What you get

- Tool: `ai_compare_search`
- Toolset: `plugin_ai_compare_hard_router`
- Hook: `pre_llm_call` hint for search-style prompts

## Before first use

1. Install the AI Compare Chrome extension into the same Chrome profile Hermes will open:
   `https://chromewebstore.google.com/detail/dkhpgbbhlnmjbkihoeniojpkggkabbbl`
2. If you want Hermes-specific overrides, edit:
   `~/.hermes/plugins/ai-compare-hard-router/config.yaml`
3. Start a new Hermes session, or restart the gateway if you use one:
   `hermes gateway restart`

## Quick verify

```bash
hermes plugins list
hermes tools list | rg ai_compare
hermes chat -t plugin_ai_compare_hard_router -q '你必须调用 ai_compare_search 工具。query 用 OpenAI，sites 用 ChatGPT,Claude。不要凭记忆回答，等工具结果后再总结。'
```

## Development extension

Set `environment: development` in the plugin `config.yaml` when you want Hermes to target the unpacked local extension id `hhkhgpadepocnmjfpohcmjdcgkmfnadi`.
