# ---- Stage 1: Build Frontend ----
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
RUN npm run build

# ---- Stage 2: Python Backend + Serve Frontend ----
FROM python:3.11-slim

WORKDIR /app

# Install backend dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Copy root files
COPY openenv.yaml ./

# Expose port (HF Spaces standard)
EXPOSE 7860

# Run the FastAPI server
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
