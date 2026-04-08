# ---- Stage 1: Build Frontend ----
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --production=false
COPY frontend/ .
RUN npm run build

# ---- Stage 2: Python Backend + Serve Frontend ----
FROM python:3.11-slim

# Create non-root user (HF Spaces runs as uid 1000)
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Install backend dependencies
COPY --chown=user backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend code (includes __init__.py for package resolution)
COPY --chown=user backend/ ./backend/

# Copy built frontend
COPY --from=frontend-build --chown=user /app/frontend/dist ./frontend/dist

# Copy root-level files needed at runtime
COPY --chown=user openenv.yaml ./
COPY --chown=user inference.py ./

# Switch to non-root user
USER user

# Expose port (HF Spaces standard)
EXPOSE 7860

# Run the FastAPI server
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
