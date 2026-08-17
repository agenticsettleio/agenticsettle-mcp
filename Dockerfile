# AgenticSettle Verify MCP Server — container image
#
# This is an MCP *stdio* server: it talks over stdin/stdout, not a network
# port, so there's no EXPOSE and no HTTP entrypoint here — `docker run -i`
# is how an MCP client actually drives it. This Dockerfile exists mainly so
# directory sites (e.g. Glama, which builds every listed server from a
# Dockerfile to verify it actually installs and runs — see
# https://glama.ai/mcp/methodology) can validate the package, and so anyone
# who prefers a container over a local Python env has one.
#
# AGENTIC_SETTLE_API_KEY must be supplied at `docker run` time via -e (get a
# free one: see README.md). AGENTIC_SETTLE_BASE_URL defaults to
# https://app.agenticsettle.io if unset.

FROM python:3.12-slim

WORKDIR /app

# Only the wheel-buildable package — the repo's checked-in lib/ directory
# holds Windows-only binaries (PyWin32, a compiled .pyd) bundled solely for
# the .mcpb Claude Desktop extension package, and would be non-portable
# (and pointless) inside this Linux image.
COPY pyproject.toml README.md LICENSE ./
COPY agenticsettle_verify_mcp/ ./agenticsettle_verify_mcp/

RUN pip install --no-cache-dir .

# Run as a non-root user — this server never needs elevated privileges.
RUN useradd --create-home --uid 1000 mcp
USER mcp

ENTRYPOINT ["python", "-m", "agenticsettle_verify_mcp"]
