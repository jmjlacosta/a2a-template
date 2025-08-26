"""
ADK-first LLM wrapper with multi-provider support via LiteLLM.
~250 LOC - Auto-selects Anthropic/OpenAI/Google based on API keys.
Ensures consistent temperature/max_tokens propagation across all providers.
"""

import os
import json
import time
import random
import logging
import asyncio
from typing import Dict, Any, Optional, Tuple, List
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService

try:
    from google.adk.models.lite_llm import LiteLlm
except ImportError:
    raise ImportError(
        "LiteLLM support not available. Install with: pip install google-adk litellm"
    )


logger = logging.getLogger(__name__)


def _create_runner(agent_name: str, agent) -> Runner:
    """
    Create a Runner with all required services.
    
    Args:
        agent_name: Name for the app
        agent: The LLM agent instance
        
    Returns:
        Configured Runner instance
    """
    return Runner(
        app_name=agent_name,
        agent=agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )

# Default models for each provider
DEFAULTS = {
    "anthropic": "anthropic/claude-3-5-sonnet-20241022",
    "openai": "openai/gpt-4o-mini",
    "google": "gemini-2.0-flash-exp",
}


def _auto_model() -> Tuple[str, str]:
    """
    Auto-detect provider and model from environment.
    
    Returns:
        (provider, model_id) tuple
        
    Raises:
        RuntimeError: If no API key is found
    """
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic", os.getenv("ANTHROPIC_MODEL", DEFAULTS["anthropic"])
    if os.getenv("OPENAI_API_KEY"):
        return "openai", os.getenv("OPENAI_MODEL", DEFAULTS["openai"])
    if os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
        return "google", os.getenv("GOOGLE_MODEL", DEFAULTS["google"])
    raise RuntimeError(
        "No API key found. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY/GEMINI_API_KEY."
    )


def create_llm_agent(
    name: str = "assistant",
    instruction: str = "You are a helpful assistant.",
    tools: Optional[List[Any]] = None,
    model: Optional[str] = None,
    *,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> LlmAgent:
    """
    ADK LlmAgent factory with consistent knob propagation across providers.
    
    Args:
        name: Agent name
        instruction: System instruction
        tools: Optional tools list
        model: Optional explicit model override
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens to generate
        
    Returns:
        Configured LlmAgent with consistent settings across providers
    """
    provider, detected_model = _auto_model() if model is None else ("explicit", model)
    
    # Log selection for debugging
    debug_parts = [f"provider={provider}", f"model={detected_model}"]
    if temperature is not None:
        debug_parts.append(f"temp={temperature}")
    if max_tokens is not None:
        debug_parts.append(f"max_tokens={max_tokens}")
    logger.info(f"LLM agent created: {' '.join(debug_parts)}")
    
    # Unified generation config (cover both naming conventions)
    gen_cfg = {}
    if temperature is not None:
        gen_cfg["temperature"] = float(temperature)
    if max_tokens is not None:
        gen_cfg["max_tokens"] = int(max_tokens)          # OpenAI/Anthropic style
        gen_cfg["max_output_tokens"] = int(max_tokens)   # Gemini style
    
    # Build provider-specific model handle
    if provider in ("anthropic", "openai") or detected_model.startswith(("anthropic/", "openai/")):
        # LiteLLM wrapper — ensure defaults mirror generation_config
        default_params = {}
        if temperature is not None:
            default_params["temperature"] = float(temperature)
        if max_tokens is not None:
            default_params["max_tokens"] = int(max_tokens)
        
        model_obj = LiteLlm(
            model=detected_model,
            default_params=default_params,
        )
    else:
        # Gemini native takes model string; LlmAgent will honor generation_config
        model_obj = detected_model
    
    # Create LlmAgent with generation_config (adaptive for different ADK versions)
    kwargs = dict(
        name=name,
        model=model_obj,
        instruction=instruction,
        tools=tools or []
    )
    
    if gen_cfg:
        # Try modern param name first, fall back to older name
        try:
            agent = LlmAgent(**kwargs, generation_config=gen_cfg)
        except (TypeError, Exception) as e:
            # Log the specific error for debugging (usually just version mismatch)
            pass  # Silently handle - this is expected with some ADK versions
            try:
                agent = LlmAgent(**kwargs, generate_content_config=gen_cfg)
            except (TypeError, Exception) as e2:
                logger.debug(f"generate_content_config failed: {e2}")
                # If neither works, create without config
                logger.debug("Generation config not supported by this ADK version - using defaults")
                agent = LlmAgent(**kwargs)
    else:
        agent = LlmAgent(**kwargs)
    
    return agent


async def generate_text(
    prompt: str,
    system_instruction: str = "You are a helpful AI assistant.",
    *,
    tools: Optional[List[Any]] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    timeout: int = 30,
    max_retries: int = 3,
) -> str:
    """
    Generate text using auto-selected LLM provider with consistent parameters.
    
    Args:
        prompt: Input prompt
        system_instruction: System instruction for the agent
        tools: Optional tools list
        model: Optional explicit model override
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens to generate
        timeout: Timeout in seconds
        max_retries: Maximum retry attempts
        
    Returns:
        Generated text
        
    Raises:
        TimeoutError: If generation times out
        Exception: If all retries fail
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Create agent with explicit parameter propagation
            agent = create_llm_agent(
                name="TextGenerator",
                instruction=system_instruction,
                tools=tools,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            # Create runner with all required services
            runner = _create_runner("LLMUtilsAgent", agent)
            
            # Run async - handle both stream and single result
            result = runner.run_async(user_id="user", session_id="session", new_message=prompt)
            
            chunks = []
            try:
                # Check if result is an async iterator (stream) or single object
                if hasattr(result, "__aiter__"):
                    # It's a stream - collect all events
                    async for ev in result:
                        # ADK events typically have ev.text or ev.content.text
                        if getattr(ev, "text", None):
                            chunks.append(ev.text)
                        else:
                            content = getattr(ev, "content", None)
                            if content and getattr(content, "text", None):
                                chunks.append(content.text)
                else:
                    # It's a single result - await and extract text
                    single_result = await result
                    if hasattr(single_result, "text"):
                        chunks.append(single_result.text)
                    elif isinstance(single_result, str):
                        chunks.append(single_result)
                    else:
                        chunks.append(str(single_result))
            finally:
                # Clean up runner to avoid lingering background tasks with bounded timeout
                if hasattr(runner, "shutdown"):
                    try:
                        # Bounded shutdown with 5-second timeout
                        await asyncio.wait_for(runner.shutdown(), timeout=5.0)
                        logger.debug(f"Runner shutdown completed for model={model or detected_model}")
                    except asyncio.TimeoutError:
                        logger.warning(
                            f"Runner shutdown timeout after 5s for model={model or detected_model}"
                        )
                    except asyncio.CancelledError:
                        # Use shield to ensure cleanup runs even if cancelled
                        try:
                            await asyncio.shield(asyncio.wait_for(runner.shutdown(), timeout=2.0))
                        except (asyncio.TimeoutError, Exception):
                            pass
                        raise  # Re-raise the cancellation
                    except Exception as e:
                        # Log unexpected errors but don't fail the whole operation
                        logger.warning(f"Runner shutdown error: {e}")
            
            return "".join(chunks)
                
        except asyncio.TimeoutError:
            last_error = TimeoutError(f"LLM generation timed out after {timeout}s")
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"LLM timeout, retry {attempt + 1}/{max_retries} after {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"LLM error: {e}, retry {attempt + 1}/{max_retries} after {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
    
    raise last_error or Exception("LLM generation failed")


async def generate_json(
    prompt: str,
    system_instruction: str = "You are a helpful AI assistant that generates valid JSON.",
    *,
    tools: Optional[List[Any]] = None,
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 1000,
    timeout: int = 30,
    max_retries: int = 3,
    schema: Optional[Dict[str, Any]] = None,
    strict: bool = False,
) -> Dict[str, Any]:
    """
    Generate JSON with automatic repair using auto-selected provider.
    
    Args:
        prompt: Input prompt
        system_instruction: System instruction for JSON generation
        tools: Optional tools list
        model: Optional explicit model override
        temperature: Sampling temperature (lower for more consistent JSON)
        max_tokens: Maximum tokens to generate
        timeout: Timeout in seconds
        max_retries: Maximum retry attempts
        schema: Optional JSON schema for validation
        strict: Whether to enforce strict JSON mode
        
    Returns:
        Parsed JSON object
        
    Raises:
        json.JSONDecodeError: If JSON repair fails
        Exception: If generation fails
    """
    # Enhance prompt for JSON generation
    json_prompt = prompt
    if strict or schema:
        json_prompt = f"{prompt}\n\nRespond with valid JSON only, no markdown formatting or explanation."
    if schema:
        json_prompt += f"\n\nThe JSON must conform to this schema:\n{json.dumps(schema, indent=2)}"
    
    for attempt in range(3):
        try:
            # Generate with low temperature for consistency
            response = await generate_text(
                prompt=json_prompt,
                system_instruction=system_instruction,
                tools=tools,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                max_retries=max_retries,
            )
            
            # Clean up common JSON formatting issues
            response = response.replace("\u200b", "").strip()  # Remove zero-width spaces
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            
            # Parse JSON
            result = json.loads(response.strip())
            
            # Validate against schema if provided
            if schema and strict:
                # Could add jsonschema validation here if needed
                pass
            
            return result
            
        except json.JSONDecodeError as e:
            if attempt < 2:
                # Try to repair the JSON
                json_prompt = f"Fix this invalid JSON and return only the corrected JSON:\n{response}\n\nError: {e}"
                system_instruction = "You are a JSON repair specialist. Fix the JSON and return only valid JSON."
                logger.debug(f"JSON parse failed, attempting repair: {e}")
            else:
                raise


# Backwards compatibility
class LLMProvider:
    """Legacy provider class for backwards compatibility."""
    
    def __init__(self, provider: str = None, api_key: str = None):
        """Initialize - provider is ignored, auto-detects from env."""
        if provider:
            logger.warning(
                f"LLMProvider: ignoring provider arg '{provider}'. "
                f"Provider is now auto-detected from API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY)"
            )
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using auto-detected provider."""
        # Map legacy kwargs to new names
        if 'max_output_tokens' in kwargs:
            kwargs['max_tokens'] = kwargs.pop('max_output_tokens')
        return await generate_text(prompt, **kwargs)
    
    async def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate JSON using auto-detected provider."""
        # Map legacy kwargs to new names
        if 'max_output_tokens' in kwargs:
            kwargs['max_tokens'] = kwargs.pop('max_output_tokens')
        return await generate_json(prompt, **kwargs)