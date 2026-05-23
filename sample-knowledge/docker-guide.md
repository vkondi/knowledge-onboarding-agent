# Docker and Containerisation

Docker packages applications and their dependencies into portable, isolated containers that run consistently across environments.

## Core Concepts

- **Image**: a read-only template with the application code, runtime, libraries, and configuration. Built from a `Dockerfile`.
- **Container**: a running instance of an image. Isolated from the host and other containers.
- **Registry**: a repository for images (Docker Hub, GitHub Container Registry, AWS ECR).
- **Dockerfile**: a text file with instructions to build an image layer by layer.
- **Docker Compose**: a tool for defining and running multi-container applications with a single YAML file.

## Dockerfile

```dockerfile
# Base image — use specific tags, never just "latest" in production
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy dependency file first (layer caching optimisation)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Non-root user for security
RUN useradd --no-create-home appuser
USER appuser

# Document the port the app listens on (informational only — doesn't publish it)
EXPOSE 8000

# Default command
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Layer caching

Docker caches each layer. Copy files that change less frequently (like `requirements.txt`) before files that change more often (like source code). This way, a code change doesn't invalidate the dependency installation layer.

## Essential Commands

```bash
# Build an image
docker build -t my-app:1.0 .

# Run a container
docker run --rm -p 8000:8000 my-app:1.0

# Run in detached mode (background)
docker run -d --name my-app -p 8000:8000 my-app:1.0

# View running containers
docker ps

# View logs
docker logs my-app
docker logs -f my-app      # follow (tail -f equivalent)

# Execute a command inside a running container
docker exec -it my-app bash

# Stop and remove
docker stop my-app
docker rm my-app

# Pull from a registry
docker pull postgres:16-alpine
```

## Docker Compose

Manages multi-container applications (e.g., web server + database + cache).

```yaml
# docker-compose.yml
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/mydb
    depends_on:
      - db

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: mydb
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

```bash
docker compose up -d          # start all services in background
docker compose logs -f web    # follow logs for the web service
docker compose down           # stop and remove containers
docker compose down -v        # also remove named volumes
```

## Volumes and Data Persistence

Containers are ephemeral — data written to the container filesystem is lost when the container is removed.

```bash
# Named volume (managed by Docker — preferred for databases)
docker run -v postgres_data:/var/lib/postgresql/data postgres:16

# Bind mount (maps a host directory — preferred for development)
docker run -v ./src:/app/src my-app:1.0
```

## Networking

Containers in the same Compose project share a default network and can reach each other by service name:

```python
# Inside the 'web' container, this connects to the 'db' container
conn = psycopg2.connect(host="db", port=5432, ...)
```

## Multi-Stage Builds

Reduce final image size by separating build dependencies from the runtime image:

```dockerfile
# Stage 1: build
FROM python:3.11 AS builder
WORKDIR /build
COPY . .
RUN pip install build && python -m build

# Stage 2: runtime (smaller base image, no build tools)
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /build/dist/*.whl .
RUN pip install *.whl
CMD ["my-app"]
```

## Security Basics

- Never run containers as `root` — create a non-root user in the Dockerfile.
- Don't embed secrets in images — use environment variables or secret managers.
- Scan images for vulnerabilities: `docker scout cves my-app:1.0`
- Use minimal base images (`-slim`, `-alpine`) to reduce attack surface.
