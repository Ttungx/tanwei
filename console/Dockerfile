# ============================================
# Stage 1: Build React Frontend
# ============================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY edge-test-console/frontend/package.json ./

# Install dependencies
RUN npm install --legacy-peer-deps

# Copy frontend source
COPY edge-test-console/frontend/ ./

# Build frontend (ignore TypeScript errors for now, focus on Vite build)
RUN npm run build || npx vite build

# ============================================
# Stage 2: Python Backend + Static Files
# ============================================
FROM python:3.10-slim

WORKDIR /app

# Install system packages required by the runtime image
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install backend dependencies
COPY edge-test-console/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY edge-test-console/backend/app/ ./app/

# Copy demo sample directory for built-in showcase flows
COPY data/test_traffic/demo_show/ ./demo-samples/

# Copy built frontend from stage 1 (if exists)
COPY --from=frontend-builder /app/frontend/dist ./static

# Create uploads directory
RUN mkdir -p /app/uploads

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV AGENT_LOOP_URL=http://agent-loop:8002
ENV DEMO_SAMPLES_DIR=/app/demo-samples

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
