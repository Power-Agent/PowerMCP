from __future__ import annotations

from .server import (
    DEFAULT_CHATGPT_PORT,
    configured_host,
    configured_port,
    configured_transport_security,
    create_mcp_server,
)


def main() -> None:
    host = configured_host()
    create_mcp_server(read_only=True).run(
        "streamable-http",
        host=host,
        port=configured_port(DEFAULT_CHATGPT_PORT),
        transport_security=configured_transport_security(
            read_only=True,
            host=host,
        ),
    )


if __name__ == "__main__":
    main()
