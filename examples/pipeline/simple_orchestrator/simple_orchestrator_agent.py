# simple_orchestrator_agent.py
from __future__ import annotations

import json
import logging
import os
import time
from typing import List, Dict, Any, Optional, Callable, Union

from a2a.types import AgentSkill, TextPart, DataPart, Message
from google.adk.tools import FunctionTool

from base import A2AAgent  # your golden base


class SimpleOrchestratorAgent(A2AAgent):
    """
    Dead-simple orchestrator that walks a fixed pipeline:
      keyword -> grep -> chunk -> summarize
    Uses DataPart for structured JSON payloads where possible (spec-preferred).
    """

    # ---- knobs you can tweak safely ----
    MAX_PATTERNS: int = 20
    MAX_MATCHES_FOR_CHUNKS: int = 5
    LINES_BEFORE: int = 2
    LINES_AFTER: int = 2
    CALL_TIMEOUT_SEC: float = float(os.getenv("ORCH_AGENT_TIMEOUT", "30"))

    def __init__(
        self,
        keyword_agent: str | None = None,
        grep_agent: str | None = None,
        chunk_agent: str | None = None,
        summarize_agent: str | None = None,
        logger: Optional[logging.Logger] = None,
    ):
        super().__init__()
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        # Resolve target agents (constructor args -> default names; resolved via config/agents.json in base)
        self.keyword_agent = keyword_agent or "keyword"
        self.grep_agent = grep_agent or "grep"
        self.chunk_agent = chunk_agent or "chunk"
        self.summarize_agent = summarize_agent or "summarize"

        # Bind the tool to this instance without global state
        def _tool(document: str) -> str:
            return self._run_pipeline_sync(document)

        self._pipeline_tool: Callable[[str], str] = _tool

    # --------------- A2A metadata --------------- #
    def get_agent_name(self) -> str:
        return "Simple Pipeline Orchestrator"

    def get_agent_description(self) -> str:
        return (
            "Runs a fixed document-analysis pipeline (keyword → grep → chunk → summarize). "
            "No branching or tools selection logic; purely sequential for traceability."
        )

    def get_agent_skills(self) -> List[AgentSkill]:
        return [
            AgentSkill(
                id="simple_pipeline",
                name="Simple Pipeline Execution",
                description="Execute keyword → grep → chunk → summarize in order.",
                tags=["pipeline", "sequential", "orchestrator"],
                input_modes=["text/plain"],
                output_modes=["text/markdown"],
            )
        ]

    # Keep streaming off unless you implement SSE in the server
    def supports_streaming(self) -> bool:
        return False

    def get_system_instruction(self) -> str:
        # If your LLM uses tools, this nudge directs it to call the pipeline tool.
        return (
            "You are a medical document analysis pipeline coordinator. "
            "When given a document, use the run_simple_pipeline tool."
        )

    def get_tools(self) -> list:
        # Expose the tool; no globals, no side effects
        return [FunctionTool(func=self._pipeline_tool)]

    # --------------- Orchestration --------------- #
    async def process_message(self, message: str) -> str:
        """
        Base requires this. If tools are used, LLM will call the tool.
        We still implement it so direct calls work (e.g., tests).
        """
        return await self.execute_pipeline(message)

    async def execute_pipeline(self, document: str) -> str:
        """
        Full async pipeline (used by HTTP path or tests).
        Prefer DataPart for structured payloads when calling other agents.
        """
        t0 = time.time()
        self.logger.info("🚀 Starting simple pipeline")

        # --- STEP 1: KEYWORDS --- #
        kw_prompt = self._keyword_prompt(document)
        kw_resp = await self._call_structured(self.keyword_agent, kw_prompt)  # text → TextPart
        patterns = self._extract_patterns(kw_resp)[: self.MAX_PATTERNS]
        self.logger.info(f"STEP 1: extracted {len(patterns)} patterns")

        # --- STEP 2: GREP --- #
        grep_req = {
            "patterns": patterns,
            "document_content": document,
            "case_sensitive": False,
        }
        grep_resp = await self._call_structured(self.grep_agent, grep_req)  # dict → DataPart
        matches = self._parse_grep_results(grep_resp)
        self.logger.info(f"STEP 2: grep found {len(matches)} matches")

        # Deduplicate by line_number (stabilizes chunk count on single-line docs)
        unique_by_line: Dict[int, Dict[str, Any]] = {}
        for m in matches:
            ln = int(m.get("line_number", 1))
            unique_by_line.setdefault(ln, m)

        matches_to_chunk = list(unique_by_line.values())[: self.MAX_MATCHES_FOR_CHUNKS]
        self.logger.info(f"STEP 2: deduped to {len(matches_to_chunk)} to chunk")

        # --- STEP 3: CHUNK --- #
        chunks: List[str] = []
        for m in matches_to_chunk:
            chunk_req = {
                "match_info": m,
                "lines_before": self.LINES_BEFORE,
                "lines_after": self.LINES_AFTER,
            }
            chunk_resp = await self._call_structured(self.chunk_agent, chunk_req)  # dict → DataPart
            chunks.append(chunk_resp)
        self.logger.info(f"STEP 3: extracted {len(chunks)} chunks")

        # --- STEP 4: SUMMARIZE --- #
        combined = "\n\n".join(chunks[: self.MAX_MATCHES_FOR_CHUNKS])
        sum_req = {
            "chunk_content": combined,
            "chunk_metadata": {
                "source": "input_document",
                "total_matches": len(matches),
                "chunks_extracted": len(chunks),
            },
            "summary_style": "clinical",
        }
        summary = await self._call_structured(self.summarize_agent, sum_req)  # dict → DataPart
        self.logger.info("STEP 4: summarization complete")

        dt = time.time() - t0
        self.logger.info(f"✅ Pipeline complete in {dt:.2f}s")

        return (
            f"## Medical Document Analysis Complete\n\n"
            f"**Execution Time:** {dt:.2f} seconds\n\n"
            f"**Pipeline Statistics:**\n"
            f"- Patterns generated: {len(patterns)}\n"
            f"- Matches found: {len(matches)}\n"
            f"- Chunks extracted: {len(chunks)}\n"
            f"- Chunks analyzed: {min(len(chunks), self.MAX_MATCHES_FOR_CHUNKS)}\n\n"
            f"**Summary:**\n{summary}\n\n"
            f"---\n*Analysis performed by Simple Pipeline Orchestrator*"
        )

    # Synchronous wrapper for the tool surface (tool functions are typically sync)
    def _run_pipeline_sync(self, document: str) -> str:
        import asyncio

        return asyncio.get_event_loop().run_until_complete(self.execute_pipeline(document))

    # --------------- Helpers --------------- #
    async def _call_structured(self, agent_name_or_url: str, payload: Union[str, Dict[str, Any], List[Any]]) -> str:
        """
        Prefer sending a spec-native A2A Message with Parts:
          - dict/list  -> DataPart
          - str        -> TextPart
        If the underlying client only accepts a string, we fall back to JSON text.
        Returns the other agent's textual response (final message text).
        """
        # Try to use a spec-native Message if the client supports it.
        # We keep the fallback to a string for compatibility with older clients.
        try:
            # Lazy import to avoid coupling base template to client shape
            from utils.a2a_client import A2AAgentClient  # same client your base uses

            # Build Parts
            if isinstance(payload, (dict, list)):
                parts = [DataPart(kind="data", data=payload)]
            else:
                parts = [TextPart(kind="text", text=str(payload))]

            msg = Message(
                role="user",
                parts=parts,
                kind="message",
                # messageId/taskId/contextId are typically filled by server;
                # we omit them for a client-initiated send.
            )

            # Attempt a structured send if the client exposes a message API
            async with A2AAgentClient() as client:
                if hasattr(client, "call_agent_message"):
                    # Preferred path: send a Message (Parts preserved)
                    return await client.call_agent_message(agent_name_or_url, msg, timeout=self.CALL_TIMEOUT_SEC)
                else:
                    # Fallback: send text; for structured payloads, serialize to JSON text
                    text_payload = json.dumps(payload) if isinstance(payload, (dict, list)) else str(payload)
                    return await client.call_agent(agent_name_or_url, text_payload, timeout=self.CALL_TIMEOUT_SEC)

        except Exception as e:
            # If anything about structured send fails, fall back to your base helper
            self.logger.warning(f"Structured call failed or unsupported, falling back to text: {e}")
            text_payload = json.dumps(payload) if isinstance(payload, (dict, list)) else str(payload)
            return await self.call_other_agent(agent_name_or_url, text_payload, timeout=self.CALL_TIMEOUT_SEC)

    @staticmethod
    def _keyword_prompt(document: str) -> str:
        head = document[:1000]
        return (
            "Generate regex patterns (as literal code fragments between backticks) to find medically relevant info "
            "in the following document. Include diagnoses, meds/doses, vitals, treatments, labs, and dates.\n\n"
            f"{head}\n\n"
            "Return only patterns; no prose."
        )

    @staticmethod
    def _extract_patterns(keyword_response: str) -> List[str]:
        import re

        patterns: List[str] = []
        for line in keyword_response.splitlines():
            if "`" in line and not line.strip().startswith("#"):
                patterns.extend(re.findall(r"`([^`]+)`", line))

        if not patterns:
            patterns = [
                r"diabetes",
                r"hypertension",
                r"diagnosis",
                r"treatment",
                r"\b\d+\s*(mg|ml|mcg)\b",
                r"blood\s+pressure",
                r"heart\s+rate",
                r"temperature",
                r"medication",
            ]
        # de-dup while preserving order
        seen = set()
        deduped = []
        for p in patterns:
            if p not in seen:
                seen.add(p)
                deduped.append(p)
        return deduped

    @staticmethod
    def _parse_grep_results(grep_response: str) -> List[Dict[str, Any]]:
        # Accept either a structured JSON string or plain text
        try:
            data = json.loads(grep_response)
        except json.JSONDecodeError:
            # fallback: synthesize basic matches from plain text
            matches: List[Dict[str, Any]] = []
            for i, line in enumerate(grep_response.splitlines()[:100], 1):
                if line.strip():
                    matches.append(
                        {
                            "file_path": "document.txt",
                            "line_number": i,
                            "match_text": line[:200],
                            "file_content": grep_response,
                        }
                    )
            return matches

        if isinstance(data, dict) and "matches" in data and isinstance(data["matches"], list):
            return data["matches"]
        if isinstance(data, list):
            return data
        return []