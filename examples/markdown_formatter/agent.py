"""
Markdown Formatter Agent
LLM-powered agent that takes plain text input and formats it as nice markdown.
Returns the formatted content as an artifact with a TextPart.
"""

from typing import List, Dict, Any, Union

from a2a.types import AgentSkill
from base import A2AAgent
from utils.logging import get_logger
from utils.llm_utils import generate_text

logger = get_logger(__name__)


class MarkdownFormatterAgent(A2AAgent):
    """
    LLM-powered markdown formatter that takes plain text and returns nicely formatted markdown.
    """

    # --- A2A Metadata ---
    def get_agent_name(self) -> str:
        return "Markdown Formatter"

    def get_agent_description(self) -> str:
        return (
            "LLM-powered agent that takes plain text input and formats it as clean, "
            "well-structured markdown with proper headings, lists, emphasis, and formatting."
        )

    def get_agent_version(self) -> str:
        return "1.0.0"

    def get_agent_skills(self) -> List[AgentSkill]:
        return [
            AgentSkill(
                id="format_markdown",
                name="Format Text as Markdown",
                description="Convert plain text to well-formatted markdown",
                tags=["markdown", "formatting", "text", "llm"],
                inputModes=["text/plain"],
                outputModes=["text/markdown"],
            )
        ]

    def supports_streaming(self) -> bool:
        return True

    def get_system_instruction(self) -> str:
        return (
            "You are a markdown formatting specialist. Take the provided text and format it "
            "as clean, well-structured markdown. Add appropriate headings, bullet points, "
            "emphasis (bold/italic), code blocks where relevant, and proper spacing. "
            "Make the content more readable and organized while preserving all information. "
            "Return only the formatted markdown, no additional commentary."
        )

    # --- Core Processing ---
    async def process_message(self, message: str) -> Union[Dict[str, Any], str]:
        """
        Format input text as markdown using LLM.
        Returns an artifact containing the formatted markdown as a TextPart.
        """
        try:
            # Build prompt for markdown formatting
            prompt = f"Format the following text as clean, well-structured markdown:\n\n{message}"
            
            # Generate formatted markdown using LLM
            formatted_markdown = await generate_text(
                prompt=prompt,
                system_instruction=self.get_system_instruction(),
                temperature=0.3,  # Low temperature for consistent formatting
                max_tokens=2000
            )
            
            if not formatted_markdown or not formatted_markdown.strip():
                logger.warning("LLM returned empty response, using original text")
                formatted_markdown = message
            
            # Return the formatted markdown text
            # The base class will automatically wrap this in a TextPart within an artifact
            return formatted_markdown.strip()
            
        except Exception as e:
            logger.error(f"Error formatting markdown: {e}")
            # Return original text as fallback
            # The base class will automatically wrap this in a TextPart within an artifact  
            return message