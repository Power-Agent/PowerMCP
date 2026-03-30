import os
import pydoc
import inspect
import logging
import re
import ast
import importlib.util
from typing import List, Dict, Any, Optional

logger = logging.getLogger("pscad-mcp.doc_manager")

class SourceAnalyzer:
    """
    Parses Python source files using AST to extract metadata 
    that pydoc might miss (decorators like @rmi, type hints, etc.)
    """
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.classes = {}
        self.functions = {}
        self._analyze()

    def _analyze(self):
        if not os.path.exists(self.file_path):
            return
            
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
                
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    self.classes[node.name] = self._parse_class(node)
                elif isinstance(node, ast.FunctionDef):
                    self.functions[node.name] = self._parse_function(node)
        except Exception as e:
            logger.error(f"AST Analysis failed for {self.file_path}: {e}")

    def _parse_class(self, node: ast.ClassDef) -> Dict[str, Any]:
        methods = {}
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods[item.name] = self._parse_function(item)
        return {
            "name": node.name,
            "methods": methods,
            "bases": [ast.dump(b) for b in node.bases]
        }

    def _parse_function(self, node: ast.FunctionDef) -> Dict[str, Any]:
        decorators = []
        for d in node.decorator_list:
            if isinstance(d, ast.Name):
                decorators.append(d.id)
            elif isinstance(d, ast.Call) and isinstance(d.func, ast.Name):
                decorators.append(d.func.id)
            elif isinstance(d, ast.Attribute) and isinstance(d.attr, str):
                decorators.append(d.attr)
        
        # Extract basic type hints from arguments if available
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            args.append(arg_str)
            
        return {
            "name": node.name,
            "decorators": decorators,
            "args": args,
            "returns": ast.unparse(node.returns) if node.returns else None
        }

class DocumentationManager:
    """
    Handles extraction and synchronization of mhi-pscad documentation.
    Produces LLM-friendly Markdown output enriched with source analysis.
    """
    MODULES = [
        "mhi.pscad", 
        "mhi.pscad.project", 
        "mhi.pscad.canvas", 
        "mhi.pscad.component",
        "mhi.pscad.types",
        "mhi.pscad.definition",
        "mhi.pscad.control",
        "mhi.pscad.remote",
        "mhi.pscad.simset",
        "mhi.pscad.compiler",
        "mhi.pscad.graph",
        "mhi.pscad.instrument",
        "mhi.pscad.graphics",
        "mhi.pscad.parameter_grid",
        "mhi.pscad.resource",
        "mhi.pscad.unit",
        "mhi.pscad.wizard",
        "mhi.pscad.form",
        "mhi.pscad.certificate",
        "mhi.pscad.annotation"
    ]

    def __init__(self, docs_dir: str = None):
        if docs_dir is None:
            # Default to a "docs" folder next to the main project root (PSCAD/docs)
            current_file_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_file_dir))
            docs_dir = os.path.join(project_root, "docs")
            
        self.base_dir = os.path.abspath(docs_dir)
        self.md_dir = os.path.join(self.base_dir, "md")
        self.raw_dir = os.path.join(self.base_dir, "raw")
        
        # Ensure directory structure exists
        os.makedirs(self.md_dir, exist_ok=True)
        os.makedirs(self.raw_dir, exist_ok=True)

    def sync(self) -> List[str]:
        """Synchronize reference files from the installed mhi-pscad library."""
        results = []
        for mod_name in self.MODULES:
            try:
                # 1. Find source file
                spec = importlib.util.find_spec(mod_name)
                source_file = spec.origin if spec else None
                
                analyzer = None
                if source_file and source_file.endswith(".py"):
                    analyzer = SourceAnalyzer(source_file)

                # 2. Get raw output via pydoc
                try:
                    raw_doc = pydoc.render_doc(mod_name, renderer=pydoc.plaintext)
                except Exception as e:
                    logger.warning(f"pydoc failed for {mod_name}, falling back to manual: {e}")
                    raw_doc = self._manual_inspect_raw(mod_name)
                
                raw_path = os.path.join(self.raw_dir, f"{mod_name.replace('.', '_')}.txt")
                with open(raw_path, "w", encoding="utf-8") as f:
                    f.write(raw_doc)

                # 3. Process into enriched markdown
                enriched_md = self._extract_enriched_markdown(mod_name, raw_doc, analyzer)
                md_path = os.path.join(self.md_dir, f"{mod_name.replace('.', '_')}.md")
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(enriched_md)

                results.append(f"Synced {mod_name} (Enriched)")
            except Exception as e:
                logger.error(f"Failed to sync {mod_name}: {str(e)}")
                results.append(f"Failed {mod_name}: {str(e)}")
        return results

    def _clean_pydoc(self, text: str) -> str:
        """Remove overstriking and other pydoc artifacts."""
        text = re.sub(r'(.)\x08\1', r'\1', text)
        text = re.sub(r'.\x08', '', text)
        return text

    def _extract_enriched_markdown(self, mod_name: str, raw_doc: str, analyzer: Optional[SourceAnalyzer]) -> str:
        """Process raw pydoc text and enrich with AST analysis."""
        clean_doc = self._clean_pydoc(raw_doc)
        lines = clean_doc.splitlines()
        md_lines = [f"# Module {mod_name}\n"]
        
        if analyzer and analyzer.file_path:
            md_lines.append(f"*Source: {analyzer.file_path}*\n")

        skip_inheritance_for = {
            "builtins.object", "builtins.int", "builtins.tuple", 
            "enum.Enum", "enum.IntEnum", "enum.ReprEnum", "enum.EnumType"
        }
        
        in_skipped_inheritance = False
        current_class = None
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                md_lines.append("")
                continue
            
            if line.isupper() and not line.startswith(" "):
                md_lines.append(f"## {stripped}")
                continue
            
            if "Methods inherited from" in line or "Data descriptors inherited from" in line:
                if any(noise in line for noise in skip_inheritance_for):
                    in_skipped_inheritance = True
                    continue
                else:
                    in_skipped_inheritance = False
            
            if in_skipped_inheritance and not line.startswith("     |"):
                in_skipped_inheritance = False

            if in_skipped_inheritance:
                continue

            # Class identification
            if line.startswith("    class "):
                md_lines.append(f"### {stripped}")
                # Try to find class name to start tracking methods
                match = re.search(r'class (\w+)', stripped)
                if match:
                    current_class = match.group(1)
                continue

            # Method/Function identification
            is_method = line.startswith("    def ") or (line.startswith("     |  ") and "(" in line)
            if is_method:
                clean_meth = stripped.replace("|", "").strip()
                # Try to extract method name
                meth_match = re.search(r'(\w+)\s*\(', clean_meth)
                
                meta_info = ""
                if meth_match:
                    meth_name = meth_match.group(1)
                    # Enrichment logic
                    if current_class and analyzer and current_class in analyzer.classes:
                        cls_meta = analyzer.classes[current_class]
                        if meth_name in cls_meta["methods"]:
                            func_meta = cls_meta["methods"][meth_name]
                            # Add decorators
                            if func_meta["decorators"]:
                                tags = [f"`@{d}`" for d in func_meta["decorators"]]
                                meta_info += " " + " ".join(tags)
                            # Add type hints if pydoc lacks them
                            if func_meta["returns"]:
                                meta_info += f" -> `{func_meta['returns']}`"
                    elif analyzer and meth_name in analyzer.functions:
                        func_meta = analyzer.functions[meth_name]
                        if func_meta["decorators"]:
                            tags = [f"`@{d}`" for d in func_meta["decorators"]]
                            meta_info += " " + " ".join(tags)

                md_lines.append(f"- **{clean_meth}**{meta_info}")
            else:
                md_lines.append(line.replace("|", " ").rstrip())
        
        return "\n".join(md_lines)

    def _manual_inspect_raw(self, mod_name: str) -> str:
        """Fallback crude raw doc generation."""
        import importlib
        try:
            mod = importlib.import_module(mod_name)
            output = [f"MANUAL INSPECTION FOR {mod_name}\n"]
            # Add module docstring
            if mod.__doc__:
                output.append(f"{mod.__doc__}\n")
                
            for name, obj in inspect.getmembers(mod):
                if not name.startswith('_'):
                    doc = getattr(obj, "__doc__", "No docstring")
                    output.append(f"\n--- {name} ---\n{doc}\n")
            return "\n".join(output)
        except Exception as e:
            return f"CRITICAL FAILURE: {str(e)}"

# Shared instance
doc_manager = DocumentationManager()

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    print("🚀 Starting Rich Enriched PSCAD Documentation Sync...")
    results = doc_manager.sync()
    for res in results:
        print(f"  {res}")
    print("✅ Sync Complete.")
