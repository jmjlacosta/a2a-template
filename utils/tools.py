"""
Tool utilities for A2A agents.

Provides utilities for tool validation, creation, and management.
"""

import json
import inspect
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field, asdict
from jsonschema import validate, ValidationError
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolParameter:
    """Tool parameter definition."""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None
    pattern: Optional[str] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    

@dataclass
class AgentTool:
    """A2A compliant tool definition."""
    name: str
    description: str
    inputSchema: Dict[str, Any]
    func: Optional[Callable] = field(default=None, repr=False)
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    

class ToolValidator:
    """Validates tool definitions and inputs against A2A spec."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.ToolValidator")
        
    def validate_tool_definition(self, tool: Union[Dict, AgentTool]) -> bool:
        """
        Validate a tool definition against A2A spec.
        
        Args:
            tool: Tool definition to validate
            
        Returns:
            True if valid, raises ValidationError otherwise
        """
        if isinstance(tool, AgentTool):
            tool_dict = {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema
            }
        else:
            tool_dict = tool
            
        required_fields = ["name", "description", "inputSchema"]
        for field in required_fields:
            if field not in tool_dict:
                raise ValidationError(f"Tool missing required field: {field}")
                
        if not isinstance(tool_dict["inputSchema"], dict):
            raise ValidationError("inputSchema must be a JSON Schema object")
            
        if "type" not in tool_dict["inputSchema"]:
            raise ValidationError("inputSchema must have a 'type' field")
            
        self.logger.info(f"✅ Tool '{tool_dict['name']}' validation passed")
        return True
        
    def validate_tool_input(self, tool: AgentTool, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data against tool's schema.
        
        Args:
            tool: Tool definition
            input_data: Input data to validate
            
        Returns:
            True if valid, raises ValidationError otherwise
        """
        try:
            validate(instance=input_data, schema=tool.inputSchema)
            self.logger.debug(f"✅ Input validation passed for tool '{tool.name}'")
            return True
        except ValidationError as e:
            self.logger.error(f"❌ Input validation failed: {e.message}")
            raise


class ToolBuilder:
    """Helper for building A2A compliant tools."""
    
    @staticmethod
    def create_agent_tool(
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parameters: Optional[List[ToolParameter]] = None
    ) -> AgentTool:
        """
        Create an A2A compliant tool from a Python function.
        
        Args:
            func: Python function to wrap
            name: Tool name (defaults to function name)
            description: Tool description (defaults to docstring)
            parameters: Parameter definitions (auto-detected if not provided)
            
        Returns:
            AgentTool instance
        """
        name = name or func.__name__
        description = description or (func.__doc__ or "").strip()
        
        if not parameters:
            parameters = ToolBuilder._extract_parameters(func)
            
        input_schema = ToolBuilder._build_schema(parameters)
        
        return AgentTool(
            name=name,
            description=description,
            inputSchema=input_schema,
            func=func
        )
        
    @staticmethod
    def _extract_parameters(func: Callable) -> List[ToolParameter]:
        """Extract parameters from function signature."""
        sig = inspect.signature(func)
        params = []
        
        for param_name, param in sig.parameters.items():
            if param_name == "self" or param_name == "cls":
                continue
                
            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                type_map = {
                    int: "integer",
                    float: "number",
                    bool: "boolean",
                    str: "string",
                    list: "array",
                    dict: "object"
                }
                for py_type, json_type in type_map.items():
                    if param.annotation == py_type:
                        param_type = json_type
                        break
                        
            required = param.default == inspect.Parameter.empty
            default = None if required else param.default
            
            params.append(ToolParameter(
                name=param_name,
                type=param_type,
                description=f"Parameter {param_name}",
                required=required,
                default=default
            ))
            
        return params
        
    @staticmethod
    def _build_schema(parameters: List[ToolParameter]) -> Dict[str, Any]:
        """Build JSON Schema from parameters."""
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param in parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }
            
            if param.enum:
                prop["enum"] = param.enum
            if param.pattern:
                prop["pattern"] = param.pattern
            if param.minimum is not None:
                prop["minimum"] = param.minimum
            if param.maximum is not None:
                prop["maximum"] = param.maximum
            if param.default is not None:
                prop["default"] = param.default
                
            schema["properties"][param.name] = prop
            
            if param.required:
                schema["required"].append(param.name)
                
        return schema


class ToolExecutor:
    """Executes tools with validation and error handling."""
    
    def __init__(self, validator: Optional[ToolValidator] = None):
        self.validator = validator or ToolValidator()
        self.logger = logging.getLogger(f"{__name__}.ToolExecutor")
        
    async def execute(
        self,
        tool: AgentTool,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a tool with input validation.
        
        Args:
            tool: Tool to execute
            input_data: Input data for the tool
            
        Returns:
            Tool execution result
        """
        try:
            self.validator.validate_tool_input(tool, input_data)
            
            if not tool.func:
                raise ValueError(f"Tool '{tool.name}' has no function implementation")
                
            self.logger.info(f"🔧 Executing tool '{tool.name}'")
            
            if inspect.iscoroutinefunction(tool.func):
                result = await tool.func(**input_data)
            else:
                result = tool.func(**input_data)
                
            self.logger.info(f"✅ Tool '{tool.name}' executed successfully")
            
            return {
                "success": True,
                "result": result
            }
            
        except ValidationError as e:
            self.logger.error(f"❌ Validation error: {e}")
            return {
                "success": False,
                "error": {
                    "code": -32602,
                    "message": "Invalid params",
                    "data": str(e)
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ Execution error: {e}")
            return {
                "success": False,
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": str(e)
                }
            }


class ToolRegistry:
    """Registry for managing agent tools."""
    
    def __init__(self):
        self.tools: Dict[str, AgentTool] = {}
        self.validator = ToolValidator()
        self.logger = logging.getLogger(f"{__name__}.ToolRegistry")
        
    def register(self, tool: AgentTool) -> None:
        """Register a tool."""
        self.validator.validate_tool_definition(tool)
        self.tools[tool.name] = tool
        self.logger.info(f"📝 Registered tool '{tool.name}'")
        
    def unregister(self, name: str) -> None:
        """Unregister a tool."""
        if name in self.tools:
            del self.tools[name]
            self.logger.info(f"🗑️ Unregistered tool '{name}'")
            
    def get(self, name: str) -> Optional[AgentTool]:
        """Get a tool by name."""
        return self.tools.get(name)
        
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema
            }
            for tool in self.tools.values()
        ]
        
    def export_tools(self) -> List[Dict[str, Any]]:
        """Export tools for A2A agent card."""
        return self.list_tools()


def create_simple_tool(
    name: str,
    description: str,
    func: Callable,
    **kwargs
) -> AgentTool:
    """
    Convenience function to create a simple tool.
    
    Args:
        name: Tool name
        description: Tool description
        func: Function to execute
        **kwargs: Additional tool properties
        
    Returns:
        AgentTool instance
    """
    builder = ToolBuilder()
    tool = builder.create_agent_tool(
        func=func,
        name=name,
        description=description
    )
    
    for key, value in kwargs.items():
        if hasattr(tool, key):
            setattr(tool, key, value)
            
    return tool


async def execute_tool_chain(
    tools: List[AgentTool],
    inputs: List[Dict[str, Any]],
    executor: Optional[ToolExecutor] = None
) -> List[Dict[str, Any]]:
    """
    Execute a chain of tools in sequence.
    
    Args:
        tools: List of tools to execute
        inputs: List of input data for each tool
        executor: Tool executor (creates new one if not provided)
        
    Returns:
        List of execution results
    """
    if len(tools) != len(inputs):
        raise ValueError("Number of tools must match number of inputs")
        
    executor = executor or ToolExecutor()
    results = []
    
    for tool, input_data in zip(tools, inputs):
        result = await executor.execute(tool, input_data)
        results.append(result)
        
        if not result.get("success"):
            logger.warning(f"Tool chain stopped at '{tool.name}' due to error")
            break
            
    return results