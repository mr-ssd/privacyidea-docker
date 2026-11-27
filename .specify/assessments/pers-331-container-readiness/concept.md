# Concept — pers-331-container-readiness

Add a container readiness check to the image, e.g. a Docker `HEALTHCHECK` that probes `/healthz/readyz` (HTTP 200 + `"status": "ready"`), optionally surfaced to orchestrators via `depends_on: condition: service_healthy` / Kubernetes `readinessProbe`.

## Options (evidence-based)

1. `HEALTHCHECK` with a Python one-liner probe (the slim image has Python but no curl): native `docker inspect --health`, no sidecar needed.
2. Orchestrator-level probe only (compose `healthcheck:` on the service, or k8s `readinessProbe` on 8080): no change to the image, but nothing visible via plain `docker ps`.
3. Keep client-side polling only (status quo): zero image change, CI already covers it.

## Tradeoff

The core tradeoff is image self-containment versus probe tooling: option 1 gives a native signal but embeds a recurring probe process in the app container (Python-based, since curl is absent, running as `nobody`), while options 2-3 keep the image lean but leave `docker ps` health empty and push readiness detection to each deployment. Interval/timeout tuning and the risk of flapping during slow schema upgrades (`PI_AUTO_UPDATE`) are additional operational tradeoffs.
