# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install --legacy-peer-deps

# Copy source code
COPY env.d.ts index.html vite.config.ts tsconfig.json tsconfig.node.json ./
COPY src ./src

# Build parameters for Vite
ARG VITE_AZURE_CLIENT_ID
ARG VITE_AZURE_AUTHORITY
ARG VITE_AZURE_REDIRECT_URI

# Build Vue app with environment variables
RUN VITE_AZURE_CLIENT_ID=${VITE_AZURE_CLIENT_ID} \
    VITE_AZURE_AUTHORITY=${VITE_AZURE_AUTHORITY} \
    VITE_AZURE_REDIRECT_URI=${VITE_AZURE_REDIRECT_URI} \
    npm run build

# Runtime stage - Serve SPA and proxy /api to the internal backend
FROM nginx:1.27-alpine

RUN apk add --no-cache gettext

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY docker-entrypoint.sh /docker-entrypoint.sh

RUN chmod +x /docker-entrypoint.sh

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# Expose port
EXPOSE 80

# Start the application
ENTRYPOINT ["/docker-entrypoint.sh"]
