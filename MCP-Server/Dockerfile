FROM n8nio/n8n:latest

USER root

# Install bash and MCP nodes globally
RUN apk add --no-cache bash && npm install --location=global n8n-nodes-mcp

# Copy NodeJS start script
COPY start.sh /start.sh
RUN chmod +x /start.sh

USER node

# Override entrypoint to run our script
ENTRYPOINT ["/bin/bash", "/start.sh"]
