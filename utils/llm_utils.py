"""
Utility for automatic LLM provider detection and initialization.
Uses Google ADK with LiteLLM for multi-provider support.
"""

import os
import logging
from typing import Optional, List, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM initialization."""
    model: str
    provider: str
    api_key_env: str


def detect_llm_config() -> Optional[LLMConfig]:
    """
    Automatically detect which LLM provider to use based on environment variables.
    
    Priority order:
    1. ANTHROPIC_API_KEY -> Claude
    2. OPENAI_API_KEY -> GPT-4 or GPT-3.5
    3. GOOGLE_API_KEY -> Gemini
    
    Returns:
        LLMConfig with model and provider info, or None if no API key found
    """
    # Check for Anthropic first (often preferred for complex reasoning)
    if os.getenv("ANTHROPIC_API_KEY"):
        return LLMConfig(
            model="claude-3-opus-20240229",  # or claude-3-sonnet-20240229 for faster/cheaper
            provider="anthropic",
            api_key_env="ANTHROPIC_API_KEY"
        )
    
    # Check for OpenAI
    elif os.getenv("OPENAI_API_KEY"):
        # Use GPT-4 if specified, otherwise GPT-3.5 for cost efficiency
        model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        return LLMConfig(
            model=model,
            provider="openai",
            api_key_env="OPENAI_API_KEY"
        )
    
    # Check for Google
    elif os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
        return LLMConfig(
            model="gemini-1.5-flash",  # or gemini-1.5-pro for better quality
            provider="google",
            api_key_env="GOOGLE_API_KEY" if os.getenv("GOOGLE_API_KEY") else "GEMINI_API_KEY"
        )
    
    return None


def create_llm_agent(
    name: str,
    instruction: str,
    tools: Optional[List[Any]] = None,
    model: Optional[str] = None
):
    """
    Create an LLM agent with automatic provider detection.
    
    Args:
        name: Name of the agent
        instruction: System instruction/prompt for the agent
        tools: Optional list of tools (FunctionTool objects)
        model: Optional model override (if not provided, auto-detects)
    
    Returns:
        Configured LlmAgent instance
    
    Raises:
        RuntimeError: If no LLM API key is configured
    """
    try:
        from google.adk.agents.llm_agent import LlmAgent
    except ImportError:
        raise RuntimeError(
            "Google ADK not installed. Run: pip install google-adk"
        )
    
    # Use provided model or auto-detect
    if model:
        logger.info(f"Using specified model: {model}")
    else:
        config = detect_llm_config()
        if not config:
            raise RuntimeError(
                "No LLM API key found. Please set one of:\n"
                "- ANTHROPIC_API_KEY (for Claude)\n"
                "- OPENAI_API_KEY (for GPT-3.5/GPT-4)\n"
                "- GOOGLE_API_KEY (for Gemini)"
            )
        
        model = config.model
        logger.info(f"Auto-detected {config.provider} provider, using model: {model}")
    
    # Create the agent
    agent = LlmAgent(
        name=name,
        model=model,
        instruction=instruction,
        tools=tools or []
    )
    
    return agent


def create_simple_llm_runner(agent_name: str, instruction: str, tools: Optional[List[Any]] = None):
    """
    Create a simple LLM runner with automatic provider detection.
    Returns both the agent and runner for easy use.
    
    Args:
        agent_name: Name for the agent
        instruction: System instruction/prompt
        tools: Optional list of tools
    
    Returns:
        Tuple of (agent, runner)
    """
    try:
        from google.adk.runners import Runner
    except ImportError:
        raise RuntimeError(
            "Google ADK not installed. Run: pip install google-adk"
        )
    
    agent = create_llm_agent(agent_name, instruction, tools)
    runner = Runner(app_name=agent_name, agent=agent)
    
    return agent, runner


# Convenience function for simple text generation
async def generate_text(
    prompt: str,
    system_instruction: str = "You are a helpful AI assistant.",
    model: Optional[str] = None
) -> str:
    """
    Simple text generation with automatic LLM provider detection.
    
    Args:
        prompt: User prompt/question
        system_instruction: System instruction for the LLM
        model: Optional model override
    
    Returns:
        Generated text response
    """
    agent, runner = create_simple_llm_runner(
        agent_name="SimpleGenerator",
        instruction=system_instruction
    )
    
    response = ""
    async for event in runner.run_async(
        user_id="user",
        session_id="session",
        new_message=prompt
    ):
        if hasattr(event, 'text'):
            response += event.text
        elif hasattr(event, 'content'):
            if hasattr(event.content, 'text'):
                response += event.content.text
    
    return response if response else "No response generated"


# For backwards compatibility with examples that might use get_llm
def get_llm(system_instruction: str = "You are a helpful AI assistant.", **kwargs):
    """
    Compatibility function that mimics a simple LLM interface.
    
    Returns an object with a generate_text method.
    """
    class SimpleLLM:
        def __init__(self, instruction):
            self.instruction = instruction
            self.agent = None
            self.runner = None
        
        def generate_text(self, prompt: str, tools: Optional[List[Any]] = None) -> str:
            """Synchronous text generation (for compatibility)."""
            import asyncio
            
            if self.agent is None:
                self.agent, self.runner = create_simple_llm_runner(
                    agent_name="CompatibilityAgent",
                    instruction=self.instruction,
                    tools=tools
                )
            
            # Run async in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                response = ""
                async def _generate():
                    nonlocal response
                    async for event in self.runner.run_async(
                        user_id="user",
                        session_id="session",
                        new_message=prompt
                    ):
                        if hasattr(event, 'text'):
                            response += event.text
                        elif hasattr(event, 'content'):
                            if hasattr(event.content, 'text'):
                                response += event.content.text
                    return response
                
                return loop.run_until_complete(_generate())
            finally:
                loop.close()
    
    return SimpleLLM(system_instruction)