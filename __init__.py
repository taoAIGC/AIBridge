from __future__ import annotations

from . import schemas, tools


def _pre_llm_call(user_message: str = "", **kwargs):
    hint = tools.build_prompt_hint(user_message or "")
    if not hint:
        return None
    return {"context": hint}


def register(ctx):
    ctx.register_tool(
        name="ai_compare_search",
        toolset="plugin_ai_compare_hard_router",
        schema=schemas.AI_COMPARE_SEARCH,
        handler=tools.ai_compare_search,
        description="Run the local AI Compare browser workflow and return per-site results.",
        emoji="🔎",
    )
    ctx.register_hook("pre_llm_call", _pre_llm_call)
