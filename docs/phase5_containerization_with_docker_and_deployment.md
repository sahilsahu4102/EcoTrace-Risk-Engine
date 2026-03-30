# Phase 5: Containerization with Docker and Deployment

## 1. Overview
The final phase containerizes the entire stack (FastAPI backend + Next.js frontend) using Docker and Docker Compose. This ensures the application runs consistently across different environments and is ready for production deployment.

## 2. Docker Architecture

### Backend (`Dockerfile`)
- Uses `python:3.11-slim` as the base image to minimize size
- Installs dependencies from `requirements.txt`
- Exposes port `8000`
- Runs the FastAPI application with `uvicorn`

### Frontend (`frontend/Dockerfile`)
- Uses a multi-stage build based on `node:18-alpine`
- **Stage 1 (deps):** Installs package dependencies
- **Stage 2 (builder):** Builds the Next.js application leveraging the `standalone` output mode
- **Stage 3 (runner):** Copies only necessary files (public/, .next/standalone/, .next/static/) reducing final image size
- Runs Next.js as a non-root user (`nextjs`)

### Orchestration (`docker-compose.yml`)
- Maps the host's `./data` directory to `/code/data` in the backend ensuring Trase and Forest 500 CSVs don't need rebuilding inside the image
- Passes `.env` variables to backend
- Links backend and frontend via the internal Docker network
- Exposes port `3000` for the dashboard and `8000` for the API

## 3. Running with Docker

### Prerequisites
1. Ensure [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine) is installed and running.
2. Confirm your `.env` file is present in the root folder with the necessary API keys.
3. Verify your CSV datasets are populated inside `data/trase/` and `data/forest500/`.

### Commands

**Start the stack:**
```bash
# From the project root (where docker-compose.yml is located)
docker-compose up -d --build
```
> This will build both images, wire up the network, and start them in the background.

**View Dashboard:** Open http://localhost:3000
**View API Docs:** Open http://localhost:8000/docs

**View Logs:**
```bash
docker-compose logs -f
```

**Stop the stack:**
```bash
docker-compose down
```

## 4. Environment Variables in Docker
The backend automatically reads from your `.env` file using the `env_file:` declaration in Docker Compose.
The Next.js frontend communicates with the backend via the `NEXT_PUBLIC_API_URL` environment variable. By default, this is set to `http://localhost:8000` so client-side browsers can fetch the data externally over localhost. If you had internal server-side requests inside Next.js, they would use `http://backend:8000`, but this app relies tightly on client-side React fetching.

---

**Congratulations! ✅** The EcoTrace Deforestation Risk Scorer is now fully containerized and production-ready!
