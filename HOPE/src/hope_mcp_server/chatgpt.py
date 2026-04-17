from __future__ import annotations

from .server import create_mcp_server


def main() -> None:
    create_mcp_server(read_only=True).run("streamable-http")


if __name__ == "__main__":
    main()
