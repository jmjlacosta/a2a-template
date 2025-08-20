"""
Pipeline orchestrator tools for coordinating medical document analysis.
Compatible with Google ADK - all parameters are required.
"""
import json
import asyncio
from typing import Dict, List, Any, Optional
from google.adk.tools import FunctionTool


def understand_request(
    user_query: str,
    available_capabilities_json: str  # Changed from Optional[List[str]] with default
) -> str:
    """
    Understand user request and determine required capabilities.
    
    Args:
        user_query: The user's natural language request
        available_capabilities_json: JSON string of available pipeline capabilities (use "[]" for defaults)
        
    Returns:
        JSON string with request understanding
    """
    # Parse JSON and handle defaults
    try:
        available_capabilities = json.loads(available_capabilities_json) if available_capabilities_json else []
    except (json.JSONDecodeError, TypeError):
        available_capabilities = []
    
    if not available_capabilities:
        available_capabilities = [
            "pattern_generation", "document_search", "chunk_extraction",
            "summarization", "temporal_analysis", "encounter_grouping", 
            "reconciliation", "timeline_building", "verification",
            "entity_extraction", "narrative_synthesis"
        ]
    
    understanding_request = {
        "action": "understand_request",
        "user_query": user_query,
        "available_capabilities": available_capabilities,
        "instructions": """Analyze the user's request to determine:
        1. What type of medical document analysis is needed
        2. Which pipeline capabilities should be activated
        3. The desired output format
        4. Any specific constraints or requirements
        
        Return a structured analysis of the request."""
    }
    
    return json.dumps(understanding_request)


def plan_pipeline_execution(
    request_understanding_json: str,  # Changed from Dict[str, Any]
    document_info: str,
    available_agents_json: str  # Changed from Optional[Dict[str, Any]] with default
) -> str:
    """
    Plan the optimal pipeline execution strategy.
    
    Args:
        request_understanding_json: JSON string of parsed request understanding
        document_info: Information about the document to process
        available_agents_json: JSON string of available agents and their capabilities (use "{}" for defaults)
        
    Returns:
        JSON string with execution plan
    """
    # Parse JSON inputs
    try:
        request_understanding = json.loads(request_understanding_json)
    except (json.JSONDecodeError, TypeError):
        request_understanding = {}
    
    try:
        available_agents = json.loads(available_agents_json) if available_agents_json else {}
    except (json.JSONDecodeError, TypeError):
        available_agents = {}
    
    if not available_agents:
        available_agents = {
            "keyword": "Generate search patterns",
            "grep": "Search documents",
            "chunk": "Extract context",
            "temporal_tagging": "Extract temporal info",
            "encounter_grouping": "Group by encounters",
            "reconciliation": "Reconcile conflicts",
            "summary_extractor": "Extract structured summaries",
            "timeline_builder": "Build timelines",
            "checker": "Verify accuracy",
            "unified_extractor": "Extract entities",
            "unified_verifier": "Final verification",
            "narrative_synthesis": "Create narratives"
        }
    
    planning_request = {
        "action": "plan_execution",
        "request_understanding": request_understanding,
        "document_info": document_info,
        "available_agents": available_agents,
        "instructions": """Create an execution plan that:
        1. Identifies which agents to call and in what order
        2. Specifies data flow between agents
        3. Defines success criteria
        4. Includes error handling strategies
        
        Return a detailed execution plan."""
    }
    
    return json.dumps(planning_request)


def synthesize_results(
    pipeline_results_json: str,  # Changed from Dict[str, Any]
    original_request: str
) -> str:
    """
    Synthesize results from multiple agents into final response.
    
    Args:
        pipeline_results_json: JSON string of results from all pipeline stages
        original_request: The original user request
        
    Returns:
        JSON string with synthesis request
    """
    # Parse JSON input
    try:
        pipeline_results = json.loads(pipeline_results_json)
    except (json.JSONDecodeError, TypeError):
        pipeline_results = {}
    
    synthesis_request = {
        "action": "synthesize_results",
        "pipeline_results": pipeline_results,
        "original_request": original_request,
        "instructions": """Synthesize all pipeline results into a comprehensive response that:
        1. Directly addresses the user's original request
        2. Integrates information from all relevant agents
        3. Highlights key findings and insights
        4. Provides appropriate context and explanations
        5. Formats output according to user preferences
        
        Return a complete, user-ready response."""
    }
    
    return json.dumps(synthesis_request)


def handle_pipeline_error(
    error_info_json: str,  # Changed from Dict[str, Any]
    partial_results_json: str,  # Changed from Optional[Dict[str, Any]] with default
    recovery_options_json: str  # Changed from Optional[List[str]] with default
) -> str:
    """
    Handle errors during pipeline execution.
    
    Args:
        error_info_json: JSON string with error information
        partial_results_json: JSON string of any partial results obtained (use "{}" for none)
        recovery_options_json: JSON string array of recovery options (use "[]" for defaults)
        
    Returns:
        JSON string with error handling strategy
    """
    # Parse JSON inputs
    try:
        error_info = json.loads(error_info_json)
    except (json.JSONDecodeError, TypeError):
        error_info = {}
    
    try:
        partial_results = json.loads(partial_results_json) if partial_results_json else {}
    except (json.JSONDecodeError, TypeError):
        partial_results = {}
    
    try:
        recovery_options = json.loads(recovery_options_json) if recovery_options_json else []
    except (json.JSONDecodeError, TypeError):
        recovery_options = []
    
    if not recovery_options:
        recovery_options = [
            "retry_with_fallback",
            "skip_failed_stage",
            "use_partial_results",
            "terminate_gracefully"
        ]
    
    error_request = {
        "action": "handle_error",
        "error_info": error_info,
        "partial_results": partial_results,
        "recovery_options": recovery_options,
        "instructions": """Determine the best error recovery strategy:
        1. Analyze the error type and severity
        2. Consider available partial results
        3. Evaluate recovery options
        4. Recommend specific actions
        
        Return a recovery strategy with detailed steps."""
    }
    
    return json.dumps(error_request)


def optimize_pipeline_performance(
    execution_history_json: str,  # Changed from List[Dict[str, Any]]
    current_request_json: str  # Changed from Dict[str, Any]
) -> str:
    """
    Optimize pipeline performance based on execution history.
    
    Args:
        execution_history_json: JSON string of previous pipeline executions
        current_request_json: JSON string of current request details
        
    Returns:
        JSON string with optimization recommendations
    """
    # Parse JSON inputs
    try:
        execution_history = json.loads(execution_history_json)
        if not isinstance(execution_history, list):
            execution_history = []
    except (json.JSONDecodeError, TypeError):
        execution_history = []
    
    try:
        current_request = json.loads(current_request_json)
    except (json.JSONDecodeError, TypeError):
        current_request = {}
    
    optimization_request = {
        "action": "optimize_performance",
        "execution_history": execution_history,
        "current_request": current_request,
        "instructions": """Analyze performance and suggest optimizations:
        1. Identify bottlenecks in previous executions
        2. Suggest parallel execution opportunities
        3. Recommend caching strategies
        4. Propose agent selection optimizations
        5. Identify unnecessary pipeline stages
        
        Return specific optimization recommendations."""
    }
    
    return json.dumps(optimization_request)


# Create FunctionTool instances for Google ADK
understand_request_tool = FunctionTool(func=understand_request)
plan_execution_tool = FunctionTool(func=plan_pipeline_execution)
synthesize_results_tool = FunctionTool(func=synthesize_results)
handle_error_tool = FunctionTool(func=handle_pipeline_error)
optimize_performance_tool = FunctionTool(func=optimize_pipeline_performance)

# Export all tools
# Global reference to orchestrator agent instance
_orchestrator_agent = None

def set_orchestrator_agent(agent):
    """Set the global orchestrator agent reference."""
    global _orchestrator_agent
    _orchestrator_agent = agent

async def coordinate_agents(
    document: str,
    agents_to_use_json: str,  # JSON array of agent names or "all"
    execution_mode: str  # "sequential" or "parallel"
) -> str:
    """
    Coordinate multiple agents to process a document.
    This is the PRIMARY tool for agent orchestration.
    
    Args:
        document: The full document text to analyze
        agents_to_use_json: JSON array of agent names to use, or the string "all" for full pipeline
        execution_mode: How to execute agents - "sequential" or "parallel"
        
    Returns:
        JSON string with all agent responses
    """
    global _orchestrator_agent
    
    if not _orchestrator_agent:
        return json.dumps({
            "error": "Orchestrator not initialized",
            "message": "Cannot coordinate agents without orchestrator instance"
        })
    
    # Parse agents list
    if agents_to_use_json == "all":
        agents = [
            "keyword", "grep", "chunk",
            "temporal_tagging", "encounter_grouping", "reconciliation",
            "summary_extractor", "timeline_builder", "checker",
            "unified_extractor", "unified_verifier", "narrative_synthesis"
        ]
    else:
        try:
            agents = json.loads(agents_to_use_json)
        except:
            agents = ["keyword", "grep", "chunk"]
    
    results = {}
    
    try:
        if execution_mode == "sequential":
            # Sequential execution with data passing
            current_data = document
            
            for agent_name in agents:
                _orchestrator_agent.logger.info(f"Coordinating with {agent_name} agent...")
                
                # Prepare message based on agent type and previous results
                if agent_name == "keyword":
                    message = f"Generate search patterns for this document:\n{document[:1000]}"
                
                elif agent_name == "grep":
                    patterns = results.get("keyword", {}).get("patterns", [])
                    message = json.dumps({
                        "patterns": patterns,
                        "document_content": document
                    })
                
                elif agent_name == "chunk":
                    matches = results.get("grep", {}).get("matches", [])
                    message = json.dumps({
                        "matches": matches[:5],  # Limit to first 5
                        "document": document
                    })
                
                elif agent_name == "summarize":
                    chunks = results.get("chunk", {}).get("chunks", [])
                    message = json.dumps({
                        "chunks": chunks,
                        "focus": "medical information"
                    })
                
                elif agent_name == "temporal_tagging":
                    message = json.dumps({
                        "text": document,
                        "focus": "medical_events"
                    })
                
                elif agent_name == "encounter_grouping":
                    temporal = results.get("temporal_tagging", {})
                    message = json.dumps({
                        "temporal_events": temporal,
                        "document_text": document
                    })
                
                elif agent_name == "reconciliation":
                    encounters = results.get("encounter_grouping", {})
                    chunks = results.get("chunk", {}).get("chunks", [])
                    message = json.dumps({
                        "encounter_groups": encounters,
                        "facts": chunks
                    })
                
                elif agent_name == "summary_extractor":
                    reconciled = results.get("reconciliation", {})
                    message = json.dumps({
                        "reconciled_data": reconciled,
                        "document_text": document
                    })
                
                elif agent_name == "timeline_builder":
                    temporal = results.get("temporal_tagging", {})
                    encounters = results.get("encounter_grouping", {})
                    message = json.dumps({
                        "temporal_events": temporal,
                        "encounter_groups": encounters
                    })
                
                elif agent_name == "checker":
                    timeline = results.get("timeline_builder", {})
                    summary = results.get("summary_extractor", {})
                    message = json.dumps({
                        "timeline": timeline,
                        "summary": summary,
                        "original_text": document
                    })
                
                elif agent_name == "unified_extractor":
                    chunks = results.get("chunk", {}).get("chunks", [])
                    temporal = results.get("temporal_tagging", {})
                    message = json.dumps({
                        "document_text": document,
                        "chunks": chunks,
                        "temporal_events": temporal
                    })
                
                elif agent_name == "unified_verifier":
                    extracted = results.get("unified_extractor", {})
                    timeline = results.get("timeline_builder", {})
                    message = json.dumps({
                        "extracted_data": extracted,
                        "original_text": document,
                        "timeline": timeline
                    })
                
                elif agent_name == "narrative_synthesis":
                    summary = results.get("summary_extractor", {})
                    timeline = results.get("timeline_builder", {})
                    verified = results.get("unified_verifier", {})
                    message = json.dumps({
                        "summary": summary,
                        "timeline": timeline,
                        "verified_data": verified,
                        "patient_name": "Patient"
                    })
                
                else:
                    message = document
                
                # Call the agent
                try:
                    response = await _orchestrator_agent.call_other_agent(
                        agent_name, 
                        message,
                        timeout=60.0
                    )
                    
                    # Try to parse response as JSON
                    try:
                        results[agent_name] = json.loads(response)
                    except:
                        results[agent_name] = {"response": response}
                        
                except Exception as e:
                    _orchestrator_agent.logger.error(f"Error calling {agent_name}: {e}")
                    results[agent_name] = {"error": str(e)}
        
        else:
            # Parallel execution where possible
            # For now, just do sequential (parallel would need dependency analysis)
            return await coordinate_agents(document, agents_to_use_json, "sequential")
            
    except Exception as e:
        return json.dumps({
            "error": "Pipeline coordination failed",
            "message": str(e),
            "partial_results": results
        })
    
    return json.dumps({
        "success": True,
        "agents_called": agents,
        "execution_mode": execution_mode,
        "results": results
    })

# Create tool instance
coordinate_agents_tool = FunctionTool(func=coordinate_agents)

ORCHESTRATOR_TOOLS = [
    understand_request_tool,
    plan_execution_tool,
    coordinate_agents_tool,  # Add the new coordination tool
    synthesize_results_tool,
    handle_error_tool,
    optimize_performance_tool
]
