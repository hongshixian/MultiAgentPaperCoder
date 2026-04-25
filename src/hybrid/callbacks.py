"""LangChain callback handler for structured logging.

Logs LLM and tool invocations at the appropriate levels:
- INFO  – user-facing: "Agent正在思考...", "Agent调用了工具: xx"
- DEBUG – developer-facing: LLM request prompts and response content
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger("papercoder.callbacks")

# Truncation limits for log output
_PROMPT_PREVIEW = 500
_RESPONSE_PREVIEW = 2000
_TOOL_RESULT_PREVIEW = 200


class PapercoderCallbackHandler(BaseCallbackHandler):
    """Callback handler that emits structured log messages for LLM/tool calls."""

    # -- LLM / Chat Model callbacks -------------------------------------------

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[Any]],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Run when a chat model starts."""
        logger.info("Agent正在思考...")
        # DEBUG: log prompt messages
        for msg_list in messages:
            for msg in msg_list:
                content = getattr(msg, "content", str(msg))
                if isinstance(content, list):
                    # multimodal content – extract text parts
                    content = " ".join(
                        p.get("text", "") if isinstance(p, dict) else str(p)
                        for p in content
                    )
                preview = str(content)[:_PROMPT_PREVIEW]
                logger.debug("LLM请求: %s", preview)

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Run when a non-chat LLM starts (fallback)."""
        logger.info("Agent正在思考...")
        for p in prompts:
            logger.debug("LLM请求: %s", p[:_PROMPT_PREVIEW])

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Run when LLM ends."""
        # Extract text content from response generations
        try:
            generations = response.generations  # type: ignore[union-attr]
            for gen_list in generations:
                for gen in gen_list:
                    text = getattr(gen, "text", None) or ""
                    if not text:
                        msg = getattr(gen, "message", None)
                        if msg:
                            text = getattr(msg, "content", str(msg))
                    if text:
                        logger.debug("LLM响应: %s", str(text)[:_RESPONSE_PREVIEW])
                        return  # only log first generation
        except Exception:
            pass

    # -- Tool callbacks -------------------------------------------------------

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Run when a tool starts."""
        tool_name = serialized.get("name", "unknown_tool")
        args_preview = input_str[:100] if input_str else ""
        if args_preview:
            logger.info("Agent调用了工具: %s (%s)", tool_name, args_preview)
        else:
            logger.info("Agent调用了工具: %s", tool_name)

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Run when a tool ends."""
        output_str = str(output)[:_TOOL_RESULT_PREVIEW]
        logger.info("工具执行完成: %s", output_str)
