# Install AI Compare For Hermes

Use this guide when you want Hermes to call AI Compare directly from this repository.

## Install the plugin

```bash
hermes plugins install taoAIGC/AIBridge
```

Hermes installs this repository into:

`~/.hermes/plugins/ai-compare-hard-router`

If you already installed it before, update it with:

```bash
hermes plugins update ai-compare-hard-router
```

## Install the browser extension

Install AI Compare into the same Chrome profile Hermes will open:

`https://chromewebstore.google.com/detail/dkhpgbbhlnmjbkihoeniojpkggkabbbl`

If you are using an unpacked local build instead, switch the Hermes plugin config to:

```yaml
environment: development
```

The development environment targets extension id:

`hhkhgpadepocnmjfpohcmjdcgkmfnadi`

## Optional Hermes config

The installer copies `config.yaml.example` to:

`~/.hermes/plugins/ai-compare-hard-router/config.yaml`

Default example:

```yaml
environment: production
browser_app: Google Chrome
timeout_ms: 190000
```

Optional overrides:

- `extension_id`: force a private or custom Chrome extension id
- `install_url`: override the install page shown in guidance

The plugin also reuses `~/.openclaw/openclaw.json` when you already have matching AI Compare settings there.

## Verify the install

```bash
hermes chat -t plugin_ai_compare_hard_router -q '搜索一下本地论，不要做总结，不要做摘要'
```

## Natural-language usage

The plugin also adds a `pre_llm_call` hint for search-style prompts, so natural prompts such as these should nudge Hermes toward the tool:

- `搜索一下 OpenAI`
- `帮我比较一下 ChatGPT 和 Claude 对同一个问题的回答`
- `look up OpenAI with ChatGPT and Gemini`

## Troubleshooting

- If Hermes says the browser extension is missing, confirm the extension is installed in the same Chrome profile Hermes opens.
- If you use the unpacked extension, set `environment: development`.
- If Chrome opens but no structured result comes back, retry with fewer sites first, for example `ChatGPT,Gemini`.
