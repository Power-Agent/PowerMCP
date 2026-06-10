from typing import List, Dict, Any, Optional
import os
from mcp.server.fastmcp import FastMCP
from pscad_mcp.core.connection_manager import pscad_manager
from pscad_mcp.core.executor import robust_executor
from pscad_mcp.utils.doc_manager import doc_manager

async def get_local_pscad() -> str:
    """Attach to a running local PSCAD instance or launch a new one."""
    return await pscad_manager.attach_local()

async def get_pscad_status() -> Dict[str, Any]:
    """Get detailed health and status of the PSCAD instance."""
    try:
        pscad = pscad_manager.pscad
        return {
            "connected": True,
            "version": pscad.version,
            "busy": pscad.is_busy(),
            "workspace": str(pscad.workspace_path)
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}

async def sync_documentation() -> List[str]:
    """Synchronize AI reference files with the currently installed library version."""
    return doc_manager.sync()

async def list_documentation() -> List[str]:
    """List available PSCAD API documentation modules that can be read."""
    if not os.path.exists(doc_manager.md_dir):
        return ["No documentation found. Run sync_documentation first."]
    
    docs = []
    for f in os.listdir(doc_manager.md_dir):
        if f.endswith(".md"):
            # Return original module names (e.g. mhi_pscad_types.md -> mhi.pscad.types)
            module_name = f[:-3].replace("_", ".")
            docs.append(module_name)
    return sorted(docs)

async def read_documentation(module_name: str) -> str:
    """Read the Markdown documentation for a specific PSCAD module (e.g., 'mhi.pscad.types')."""
    # Normalize input
    normalized_name = module_name.replace(".", "_")
    if not normalized_name.endswith(".md"):
        normalized_name += ".md"
        
    filepath = os.path.join(doc_manager.md_dir, normalized_name)
    
    if not os.path.exists(filepath):
        return f"Error: Documentation for '{module_name}' not found. Available modules: {', '.join(await list_documentation())}"
        
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

async def repair_connection() -> str:
    """Force-reset the connection to PSCAD."""
    pscad_manager.disconnect()
    return await pscad_manager.attach_local()

async def quit_pscad() -> str:
    """Terminate the PSCAD application."""
    try:
        pscad = pscad_manager.pscad
        await robust_executor.run_safe(pscad.quit)
        pscad_manager.disconnect()
        return "PSCAD terminated."
    except Exception as e:
        return f"Error during quit: {str(e)}"

def register_app_tools(mcp: FastMCP):
    """Register core application lifecycle and sync tools."""
    mcp.tool()(get_local_pscad)
    mcp.tool()(get_pscad_status)
    mcp.tool()(sync_documentation)
    mcp.tool()(list_documentation)
    mcp.tool()(read_documentation)
    mcp.tool()(repair_connection)
    mcp.tool()(quit_pscad)
