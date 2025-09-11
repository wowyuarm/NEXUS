# AURA Frontend Dockerfile
# Multi-stage build for optimized production image

# Builder stage
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files for dependency installation
COPY package.json pnpm-lock.yaml* ./

# Install pnpm globally
RUN npm install -g pnpm@10

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Build the application
RUN pnpm run build

# Final stage
FROM nginx:stable-alpine

# Install curl for health checks and gettext for envsubst
RUN apk add --no-cache curl gettext

# Remove default nginx configuration
RUN rm /etc/nginx/conf.d/default.conf

# Copy nginx template and entrypoint
COPY nginx.conf /etc/nginx/conf.d/nginx.conf.template

# Copy built application from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80 || exit 1

# Start nginx with env substitution
ENV BACKEND_ORIGIN=""
CMD sh -c "envsubst '\$BACKEND_ORIGIN' < /etc/nginx/conf.d/nginx.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"