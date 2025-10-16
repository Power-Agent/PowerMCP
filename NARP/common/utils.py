from dataclasses import dataclass
from typing import Callable, Dict, Any, Optional
import functools
from mcp.server.fastmcp import FastMCP




def power_mcp_tool(mcp: FastMCP):
    """
    Decorator to register a PowerMCP tool.

    A decorator that wraps a function and transforms the result to a dictionary if it is an instance of PowerError.
    It also adds the function to the MCP server automatically.

    Args:
        mcp: The MCP server to register the tool to.

    Example:
        @power_mcp_tool(mcp)
        def my_tool(x: int) -> str:
            return str(x)
    """
    def decorator(func):

        @mcp.tool()
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            return _transform_power_mcp_result(result)
        return wrapper
    return decorator



def _transform_power_mcp_result(result: Any) -> Any:
    """
    Transforms the result of a function to a dictionary if it is an instance of PowerError.
    """
    if isinstance(result, PowerError):
        base: Dict[str, Any] = {
            "status": result.status,
            "message": result.message
        }
        if result.info:
            # We have some additional data, we will add the keys.
            for key, value in result.info.items():
                base[key] = value
        return base
    else:
        return result

@dataclass
class PowerError:
    """
    A custom error class that is used to return errors from the MCP server.
    It is used to return errors in a consistent format.
    The info field is used to return additional data about the error.

    Attributes:
        status: The status of the error.
        message: The message of the error.
        info: Additional data about the error, this is a dictionary of key-value pairs,
        and is added alongside the other fields. For instance, if this field were to be {"hello": "world"},
        then the returned object would be {"status": "error", "message": "An error occurred", "hello": "world"}
    """
    status: str
    message: str
    info: Optional[Dict[str, Any]] = None
