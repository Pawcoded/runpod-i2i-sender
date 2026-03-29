# RunPod I2I Sender

A lightweight web UI for manual image-to-image request testing against a RunPod Serverless endpoint.

This project was created to work with [Pawcoded/runpod_serverless_housemaid](https://github.com/Pawcoded/runpod_serverless_housemaid), stable tag: [`v1.0.0`](https://github.com/Pawcoded/runpod_serverless_housemaid/releases/tag/v1.0.0).

<img width="1621" height="855" alt="image" src="https://github.com/user-attachments/assets/0f6b5c4a-ef44-4f2c-8bc2-35bdcf0aec66" />

## Local Run (Docker)

1. Create `.env` from the example file:

```bash
cp .env.example .env
```

2. Fill in your values:

```env
RUNPOD_API_KEY=your-runpod-api-key
ENDPOINT_ID=your-endpoint-id
```

3. Build the Docker image:

```bash
docker build -t runpod-i2i-sender .
```

4. Run the container:

```bash
docker run --rm --env-file .env -p 7860:7860 -v "${PWD}/output:/app/output" runpod-i2i-sender
```

5. Open: [http://localhost:7860](http://localhost:7860)
6. Stop with `Ctrl+C` in the same terminal.

The container starts with WSGI by default (`gunicorn` + `gevent`).

## What This UI Does

- Uploads an input image (drag-and-drop or file picker).
- Sends a request to the configured RunPod endpoint.
- Streams status updates via SSE and shows the resulting image.
- Blocks request submission until an image is selected.

## Environment Variables

- `RUNPOD_API_KEY` — RunPod API key.
- `ENDPOINT_ID` — RunPod Serverless endpoint ID.
- `OUTPUT_DIR` (optional) — output path for logs and `response.json` (default: `/app/output`).
- `PORT` (optional) — app port inside container (default: `7860`).
- `WEB_CONCURRENCY` (optional) — number of gunicorn workers (default: `1`).
- `GUNICORN_TIMEOUT` (optional) — timeout for long-running requests in seconds (default: `1200`).

## GitHub Actions (Docker Publish)

This repository includes `.github/workflows/docker-publish.yml`.

It pushes a Docker image to Docker Hub on:
- manual run (`workflow_dispatch`),
- tag push matching `v*` or `V*`.

Required GitHub secrets:
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

