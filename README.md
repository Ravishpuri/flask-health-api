# Flask Health API — Containerized CI/CD Assessment

A lightweight Python Flask API, containerized with Docker, tested and shipped through
a GitHub Actions CI/CD pipeline (test → security scan → build & push to Docker Hub),
and deployed locally to a **Kubernetes** cluster using standard manifests.

---

## 1. Bug Fix Explanation

**Root cause:** Flask was bound to `127.0.0.1` (`app.run(host="127.0.0.1", ...)`). Inside a
container that is the container's own loopback, so the published port answered with
*connection refused* from the host and the health check never passed. The app was not
crashing — it was simply unreachable. The fix was to bind to `0.0.0.0`.

**How I debugged it:**
- Saw the container was `Up` in `docker ps`, yet `curl http://localhost:5000/health` from the host returned *connection refused* — so the process was running but nothing answered on the mapped port.
- Checked `docker logs` and spotted Flask reporting `Running on http://127.0.0.1:5000` — the giveaway that it was listening on loopback only.
- `exec`'d into the container and curled `http://127.0.0.1:5000/health` from inside, which returned **HTTP 200** — confirming the app was healthy but reachable only on the container's own loopback.
- Re-bound to `0.0.0.0` so Flask listens on all interfaces; the host probe then returned **HTTP 200**.

**Proof — before the fix (`host="127.0.0.1"`):**
```console
$ docker compose up --build -d
$ docker logs flask-health-api | grep -i "running on"
 * Running on http://127.0.0.1:5000        # listening on loopback only

$ curl http://localhost:5000/health         # from the host -> FAILS
curl: (56) Recv failure: Connection reset by peer

# health monitor logs the outage every 10s:
2026-08-13T15:53:20Z | http://localhost:5000/health | HTTP 000 | NOT OK (unreachable)
2026-08-13T15:53:30Z | http://localhost:5000/health | HTTP 000 | NOT OK (unreachable)
```

**Proof — after the fix (`host="0.0.0.0"`):**
```console
$ docker compose up --build -d
$ docker logs flask-health-api | grep -i "running on"
 * Running on all addresses (0.0.0.0)       # now listening on every interface
 * Running on http://172.18.0.2:5000

$ curl http://localhost:5000/health          # from the host -> WORKS
{"status":"healthy","version":"1.0.0","uptime_seconds":3.1,"timestamp":"2026-08-13T15:58:10Z"}

# health monitor flips to healthy:
2026-08-13T15:58:10Z | http://localhost:5000/health | HTTP 200 | OK (healthy)
2026-08-13T15:58:20Z | http://localhost:5000/health | HTTP 200 | OK (healthy)
```

---

## 2. Links

- **GitHub repository:** `https://github.com/Ravishpuri/flask-health-api`
- **Docker Hub image:** `https://hub.docker.com/r/ravish24/flask-health-api`
- **Image tags:** a unique immutable version per build in the form
  `<major.minor>.<commit-count>.<short-sha>` (e.g. `0.0.12.a1b2c3d`). No `latest` tag is published.

---

## 3. Local Setup & Execution Guide

### Prerequisites
- Docker + Docker Compose
- Python 3.12 (for running tests locally)
- A local Kubernetes cluster and `kubectl` (for the deployment)

### Clone & configure
```bash
git clone https://github.com/Ravishpuri/flask-health-api.git
cd flask-health-api

# Create your local secrets file from the template (.env is gitignored).
cp .env.example .env
# Edit .env and set a strong SECRET_KEY.
```

### Run the tests
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -v
```

### Run locally with Docker Compose
```bash
docker compose up --build
# App:     http://localhost:5000/
# Health:  http://localhost:5000/health
```

### Pull the published image from Docker Hub
```bash
# Use the version tag produced by the pipeline (no latest tag is published).
docker pull ravish24/flask-health-api:0.0.12.a1b2c3d
docker run --rm -p 5000:5000 --env-file .env ravish24/flask-health-api:0.0.12.a1b2c3d
```

### Deploy to Kubernetes
```bash
# Edit k8s/deployment.yaml and replace <IMAGE_VERSION> with the tag the pipeline
# pushed (shown in the Actions log / on Docker Hub), since no latest is published.

# Create the secret (value never touches git).
kubectl create secret generic flask-health-api-secrets \
  --from-literal=SECRET_KEY="$(openssl rand -hex 32)"

# Apply the manifests (image is pulled from Docker Hub).
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Verify rollout and pods.
kubectl rollout status deployment/flask-health-api
kubectl get pods,svc

# Access the service. Port-forward maps local 5000 -> Service 80 -> container 5000,
# so the endpoint is http://localhost:5000 — the same as compose and the
# monitor.sh default. (Works from anywhere kubectl works; no node IP needed.)
kubectl port-forward svc/flask-health-api 5000:80
curl http://localhost:5000/health

# ...or, if the node IP is reachable from your machine, hit the NodePort directly:
curl http://<node-ip>:30080/health
```

### Health monitoring
```bash
chmod +x monitor.sh
# Endpoint defaults to http://localhost:5000/health, which matches both the
# compose run and the `kubectl port-forward svc/flask-health-api 5000:80` above.
./monitor.sh
```
The script polls `/health` every 10 seconds and appends `timestamp | url | HTTP <code>`
to `health-monitor.log`. Docker Compose also runs a **native** healthcheck (visible in
`docker ps` / `docker inspect`), and Kubernetes runs readiness + liveness probes against
`/health`.

---

## 4. Architecture & Design Choices

**Deployment method — Option B (Kubernetes).** A local Kubernetes cluster gives a
realistic, production-like target: rolling updates, self-healing, and readiness/liveness
probes on `/health`. The Deployment runs 2 replicas with a `maxUnavailable: 0` rolling
strategy so updates happen with zero downtime, and a NodePort Service exposes it.

**Secrets management.** No credentials are committed. Locally, config is loaded from a
gitignored `.env` (only `.env.example` is committed). In CI, Docker Hub auth uses GitHub
Secrets (`DOCKER_USERNAME`, `DOCKER_PASSWORD`). In Kubernetes, `SECRET_KEY` is injected
from a `Secret` created imperatively, so the value never lands in the repo.

**CI/CD scope.** The pipeline automates test → Trivy security scan → build & push to
Docker Hub. Deployment to the local Kubernetes cluster is a manual `kubectl apply` step,
because GitHub's cloud runners cannot reach a cluster running on your local machine
(and the assessment requires no paid cloud resources).

**Container hardening.** The image uses `python:3.12-slim`, runs as a non-root user,
and defines a `HEALTHCHECK`.

---

## 5. Live Demo Video Walkthrough

- **Video link:** `<VIDEO_URL>`

Covers: the app running locally passing unit + health tests, the GitHub Actions pipeline
building and pushing to Docker Hub, and a walkthrough of the code changes, Dockerfile,
and pipeline logic.
