AI_COMPARE_SEARCH = {
    "name": "ai_compare_search",
    "description": (
        "Compare answers from multiple AI sites through the local AI Compare browser extension. "
        "Use this when the user asks to search, look up, compare, research, or gather answers from AI sites. "
        "Returns per-site raw results instead of a model-written summary."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The question or search request to send into AI Compare."
            },
            "sites": {
                "type": "array",
                "description": "Optional list of site names such as ChatGPT, Gemini, Claude, Grok, DeepSeek, or Qwen.",
                "items": {
                    "type": "string"
                }
            },
            "environment": {
                "type": "string",
                "description": "Optional runtime environment override: production or development.",
                "enum": ["production", "development"]
            },
            "extension_id": {
                "type": "string",
                "description": "Optional explicit Chrome extension id override."
            },
            "browser_app": {
                "type": "string",
                "description": "Optional browser app name, for example Google Chrome."
            },
            "timeout_ms": {
                "type": "integer",
                "description": "Optional runner timeout in milliseconds."
            }
        },
        "required": ["query"]
    }
}
