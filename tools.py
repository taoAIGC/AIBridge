from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path


PLUGIN_DIR = Path(__file__).resolve().parent
RUNNER_RELATIVE_CANDIDATES = [
    Path("bin") / "ai-compare-openclaw-fast.cjs",
    Path("openclaw") / "ai-compare-openclaw-fast.js",
]
OPENCLAW_CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"
DEFAULT_TIMEOUT_MS = 190000
DEFAULT_BROWSER_APP = "Google Chrome"

PRODUCTION_ENVIRONMENT = "production"
DEVELOPMENT_ENVIRONMENT = "development"
DEFAULT_EXTENSION_ID = "dkhpgbbhlnmjbkihoeniojpkggkabbbl"
DEVELOPMENT_EXTENSION_ID = "hhkhgpadepocnmjfpohcmjdcgkmfnadi"
DEFAULT_INSTALL_URL = "https://chromewebstore.google.com/detail/dkhpgbbhlnmjbkihoeniojpkggkabbbl"
DEVELOPMENT_INSTALL_URL = "chrome://extensions"

SITE_ALIAS_RULES = [
    {"name": "ChatGPT", "patterns": [r"\bchatgpt\b"]},
    {"name": "Gemini", "patterns": [r"\bgemini\b"]},
    {"name": "Claude", "patterns": [r"\bclaude\b"]},
    {"name": "Grok", "patterns": [r"\bgrok\b"]},
    {"name": "Perplexity", "patterns": [r"\bperplexity\b"]},
    {"name": "DeepSeek", "patterns": [r"\bdeepseek\b"]},
    {"name": "Kimi", "patterns": [r"\bkimi\b"]},
    {"name": "Qwen", "patterns": [r"\bqwen\b", r"通义千问"]},
    {"name": "Doubao", "patterns": [r"\bdoubao\b", r"豆包"]},
    {"name": "Minimax", "patterns": [r"\bminimax\b"]},
    {"name": "ChatGLM", "patterns": [r"\bchatglm\b", r"智谱"]},
]

SEARCH_PREFIX_RULES = [
    r"^(?:请\s*)?(?:帮我\s*)?(?:直接\s*)?(?:用\s*)?(?:去\s*)?(?:搜索一下|搜索|搜一下|搜下|查一下|查下|帮我搜|替我搜|我要搜索)\s*",
    r"^(?:please\s+)?(?:search\s+for|search|look\s+up)\s+",
]

SOFT_SEARCH_PREFIX_RULES = [
    r"^(?:请\s*)?(?:帮我\s*)?(?:了解一下|了解下|研究一下|研究下|找一下|找下|查查|看看|看下|帮我看看|帮我看下|想了解一下|想研究一下|比较一下|对比一下)\s*",
    r"^(?:please\s+)?(?:learn\s+about|look\s+into|research|find\s+information\s+about|find\s+info\s+on|compare)\s+",
]

ALT_TOOL_RULES = [
    r"网页搜索",
    r"新闻搜索",
    r"\bweb\s+search\b",
    r"\bgoogle\s+search\b",
    r"\bbing\s+search\b",
    r"\bbaidu\s+search\b",
]

LOCAL_TASK_GUARD_RULES = [
    r"^(?:这个|这段|这份|当前|本地)",
    r"报错",
    r"错误日志",
    r"日志",
    r"代码",
    r"函数",
    r"方法",
    r"文件",
    r"脚本",
    r"仓库",
    r"接口",
    r"配置",
    r"单测",
    r"测试失败",
    r"\bbug\b",
    r"\berror\b",
    r"\bstack\b",
    r"\btrace\b",
    r"\btest\b",
    r"\btests\b",
    r"\bfunction\b",
    r"\bfile\b",
    r"\bscript\b",
    r"\brepo\b",
    r"\bconfig\b",
    r"\bcode\b",
]

_COMPILED_SITE_ALIASES = [
    {
        "name": item["name"],
        "patterns": [re.compile(pattern, re.IGNORECASE) for pattern in item["patterns"]],
    }
    for item in SITE_ALIAS_RULES
]
_SEARCH_PREFIX_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in SEARCH_PREFIX_RULES]
_SOFT_SEARCH_PREFIX_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in SOFT_SEARCH_PREFIX_RULES]
_ALT_TOOL_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in ALT_TOOL_RULES]
_LOCAL_TASK_GUARD_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in LOCAL_TASK_GUARD_RULES]


def _resolve_runner_path() -> Path:
    configured = os.getenv("AI_COMPARE_RUNNER_PATH", "").strip()
    if configured:
        configured_path = Path(configured).expanduser().resolve()
        if configured_path.exists():
            return configured_path

    candidates: list[Path] = []
    seen: set[Path] = set()
    bases = [PLUGIN_DIR]
    cwd = Path.cwd().resolve()
    bases.extend([cwd, *cwd.parents])

    for base in bases:
        if base in seen:
            continue
        seen.add(base)
        for relative in RUNNER_RELATIVE_CANDIDATES:
            candidates.append((base / relative).resolve())

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return (PLUGIN_DIR / RUNNER_RELATIVE_CANDIDATES[0]).resolve()


RUNNER_PATH = _resolve_runner_path()


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _strip_outer_quotes(value: str) -> str:
    return re.sub(r'^[\'"“”‘’「『]+|[\'"“”‘’」』]+$', "", value or "").strip()


def _build_intent_candidates(text: str) -> list[str]:
    raw = str(text or "")
    lines = [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and line.strip() not in {"```json", "```"}
    ]
    last_line = lines[-1] if lines else ""
    de_timestamped = re.sub(r"^\[[^\]]+\]\s*", "", last_line).strip()
    full_normalized = _normalize_whitespace(raw)
    return list(dict.fromkeys([candidate for candidate in [de_timestamped, last_line, full_normalized] if candidate]))


def _looks_like_local_task_query(query: str) -> bool:
    return any(pattern.search(query or "") for pattern in _LOCAL_TASK_GUARD_PATTERNS)


def _match_intent_with_patterns(normalized: str, patterns: list[re.Pattern], guard_local_tasks: bool = False) -> dict | None:
    for pattern in patterns:
        matched = pattern.match(normalized or "")
        if not matched:
            continue
        remainder = normalized[matched.end():].strip()
        query = _strip_outer_quotes(remainder)
        if not query:
            continue
        if guard_local_tasks and _looks_like_local_task_query(query):
            continue
        return {
            "query": query,
            "original": normalized,
        }
    return None


def extract_search_intent(text: str) -> dict | None:
    candidates = _build_intent_candidates(text)
    if not candidates:
        return None

    for candidate in candidates:
        if any(pattern.search(candidate) for pattern in _ALT_TOOL_PATTERNS):
            continue

        matched = _match_intent_with_patterns(candidate, _SEARCH_PREFIX_PATTERNS)
        if matched:
            matched["match_type"] = "explicit_search"
            return matched

        matched = _match_intent_with_patterns(candidate, _SOFT_SEARCH_PREFIX_PATTERNS, guard_local_tasks=True)
        if matched:
            matched["match_type"] = "soft_search"
            return matched

    return None


def detect_sites(text: str) -> list[str]:
    hits: list[str] = []
    normalized = str(text or "")
    for site in _COMPILED_SITE_ALIASES:
        if any(pattern.search(normalized) for pattern in site["patterns"]):
            hits.append(site["name"])
    return list(dict.fromkeys(hits))


def _read_openclaw_plugin_config() -> dict:
    try:
        payload = json.loads(OPENCLAW_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

    entry = (((payload or {}).get("plugins") or {}).get("entries") or {}).get("ai-compare-hard-router") or {}
    config = entry.get("config") if isinstance(entry, dict) else {}
    return config if isinstance(config, dict) else {}


def _read_local_plugin_config() -> dict:
    config_path = PLUGIN_DIR / "config.yaml"
    if not config_path.exists():
        return {}

    try:
        import yaml
    except Exception:
        return {}

    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}

    return payload if isinstance(payload, dict) else {}


def _read_env(name: str) -> str:
    value = os.getenv(name, "")
    return value.strip() if isinstance(value, str) else ""


def _normalize_environment(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {DEVELOPMENT_ENVIRONMENT, "dev", "local", "debug", "开发", "开发环境"}:
        return DEVELOPMENT_ENVIRONMENT
    if normalized in {PRODUCTION_ENVIRONMENT, "prod", "release", "live", "formal", "正式", "线上", "线上环境"}:
        return PRODUCTION_ENVIRONMENT
    return PRODUCTION_ENVIRONMENT


def get_runtime_options(overrides: dict | None = None) -> dict:
    overrides = overrides or {}
    openclaw_config = _read_openclaw_plugin_config()
    local_config = _read_local_plugin_config()

    environment = _normalize_environment(
        overrides.get("environment")
        or local_config.get("environment")
        or openclaw_config.get("environment")
        or _read_env("AI_COMPARE_ENVIRONMENT")
    )
    extension_id = (
        str(
            overrides.get("extension_id")
            or local_config.get("extension_id")
            or openclaw_config.get("extensionId")
            or _read_env("AI_COMPARE_EXTENSION_ID")
            or (DEVELOPMENT_EXTENSION_ID if environment == DEVELOPMENT_ENVIRONMENT else DEFAULT_EXTENSION_ID)
        ).strip()
    )
    browser_app = (
        str(
            overrides.get("browser_app")
            or local_config.get("browser_app")
            or openclaw_config.get("browserApp")
            or _read_env("AI_COMPARE_BROWSER_APP")
            or DEFAULT_BROWSER_APP
        ).strip()
    )

    raw_timeout = (
        overrides.get("timeout_ms")
        if overrides.get("timeout_ms") is not None
        else local_config.get("timeout_ms", openclaw_config.get("timeoutMs", _read_env("AI_COMPARE_TIMEOUT_MS")))
    )
    try:
        timeout_ms = max(1000, int(raw_timeout))
    except Exception:
        timeout_ms = DEFAULT_TIMEOUT_MS

    install_url = (
        str(
            local_config.get("install_url")
            or openclaw_config.get("installUrl")
            or _read_env("AI_COMPARE_INSTALL_URL")
            or (DEVELOPMENT_INSTALL_URL if environment == DEVELOPMENT_ENVIRONMENT else DEFAULT_INSTALL_URL)
        ).strip()
    )

    return {
        "environment": environment,
        "extension_id": extension_id,
        "browser_app": browser_app,
        "timeout_ms": timeout_ms,
        "install_url": install_url,
    }


def _build_runner_args(query: str, sites: list[str], runtime_options: dict) -> list[str]:
    args = [
        str(RUNNER_PATH),
        "--query",
        str(query or "").strip(),
    ]

    if sites:
        args.extend(["--sites", ",".join(sites)])
    if runtime_options.get("extension_id"):
        args.extend(["--extension-id", runtime_options["extension_id"]])
    if runtime_options.get("browser_app"):
        args.extend(["--browser-app", runtime_options["browser_app"]])

    return args


def _extract_json_payload(stdout: str) -> dict | None:
    trimmed = str(stdout or "").strip()
    if not trimmed:
        return None

    try:
        return json.loads(trimmed)
    except Exception:
        first_brace = trimmed.find("{")
        last_brace = trimmed.rfind("}")
        if first_brace == -1 or last_brace == -1 or last_brace <= first_brace:
            return None
        try:
            return json.loads(trimmed[first_brace:last_brace + 1])
        except Exception:
            return None


def _truncate_content(content: str, max_chars: int) -> str:
    text = str(content or "").strip()
    if not text or len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}\n\n[truncated {len(text) - max_chars} chars]"


def _format_site_block(site: dict, max_chars: int = 3000) -> str:
    lines = [f"## {site.get('siteName') or 'Unknown'}"]
    url = str(site.get("url") or "").strip()
    if url:
        lines.append(f"URL: {url}")
    lines.append("")
    body = str(site.get("content") or site.get("error") or "").strip() or "(empty)"
    lines.append(_truncate_content(body, max_chars))
    return "\n".join(lines)


def _format_payload_for_display(payload: dict, query: str) -> str:
    if not payload or not isinstance(payload, dict):
        return f"AI Compare hard route failed for query: {query}\n\nRunner returned unreadable JSON payload."

    if payload.get("ok") is not True:
        error_text = str(payload.get("error") or "").strip() or "Runner returned ok=false."
        return f"AI Compare hard route failed for query: {query}\n\n{error_text}"

    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    sites = result.get("results") if isinstance(result, dict) else []
    valid_sites = [site for site in sites or [] if str((site or {}).get("siteName") or "").strip()]
    if valid_sites:
        return "\n\n".join(_format_site_block(site) for site in valid_sites)
    return f"AI Compare hard route failed for query: {query}\n\nRunner returned no site results."


def ai_compare_search(args: dict, **kwargs) -> str:
    query = str((args or {}).get("query") or "").strip()
    if not query:
        return json.dumps({"error": "Missing required query."}, ensure_ascii=False)

    raw_sites = (args or {}).get("sites") or []
    if isinstance(raw_sites, str):
        requested_sites = [item.strip() for item in raw_sites.split(",") if item.strip()]
    elif isinstance(raw_sites, list):
        requested_sites = [str(item).strip() for item in raw_sites if str(item).strip()]
    else:
        requested_sites = []

    runtime_options = get_runtime_options(args)
    if not RUNNER_PATH.exists():
        return json.dumps({
            "error": f"Runner not found: {RUNNER_PATH}"
        }, ensure_ascii=False)

    try:
        completed = subprocess.run(
            [os.getenv("NODE_BINARY", "node"), *_build_runner_args(query, requested_sites, runtime_options)],
            capture_output=True,
            text=True,
            timeout=runtime_options["timeout_ms"] / 1000.0,
            cwd=str(PLUGIN_DIR),
        )
    except subprocess.TimeoutExpired:
        return json.dumps({
            "error": f"Timed out waiting for the AI Compare runner to finish after {runtime_options['timeout_ms']}ms."
        }, ensure_ascii=False)
    except FileNotFoundError as exc:
        return json.dumps({
            "error": f"Unable to start Node runner: {exc}"
        }, ensure_ascii=False)

    payload = _extract_json_payload(completed.stdout)
    if payload is None:
        stderr = str(completed.stderr or "").strip()
        stdout = str(completed.stdout or "").strip()
        return json.dumps({
            "ok": False,
            "error": "Runner did not return valid JSON.",
            "stderr": stderr,
            "stdout": stdout,
        }, ensure_ascii=False)

    if payload.get("ok") is not True:
        payload.setdefault("stderr", str(completed.stderr or "").strip())
        payload.setdefault("stdout", str(completed.stdout or "").strip())

    return json.dumps(payload, ensure_ascii=False)


def should_suggest_ai_compare(user_message: str) -> bool:
    return extract_search_intent(user_message) is not None


def build_prompt_hint(user_message: str) -> str:
    intent = extract_search_intent(user_message)
    if not intent:
        return ""

    detected_sites = detect_sites(intent.get("original") or user_message)
    query = intent.get("query") or user_message
    hint_lines = [
        "AI Compare routing hint:",
        f'- This request looks like an AI Compare search: "{query}".',
        "- Prefer calling the tool `ai_compare_search` instead of answering from memory."
    ]
    if detected_sites:
        hint_lines.append(f'- Pass `sites`: {", ".join(detected_sites)}.')
    else:
        hint_lines.append("- If the user did not name sites, let AI Compare use its default selected sites.")
    hint_lines.append("- After the tool returns, summarize the per-site results for the user when helpful.")
    return "\n".join(hint_lines)


def format_tool_result_for_humans(payload_json: str) -> str:
    payload = _extract_json_payload(payload_json)
    if payload is None:
        return str(payload_json or "").strip()
    query = ""
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    if isinstance(result, dict):
        query = str(result.get("query") or "").strip()
    return _format_payload_for_display(payload, query)
