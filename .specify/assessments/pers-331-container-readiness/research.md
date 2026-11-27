# Research — pers-331-container-readiness

## Sources

- `run-tests.sh:3,9-27` (readiness polling of `/healthz/readyz` from the `sut` container).
- `docker-compose-test.yml:8-18` (`depends_on` without a health condition).
- `Dockerfile:1-70` (slim runtime image, `USER nobody`, tini entrypoint, `EXPOSE 8080/tcp`; no `HEALTHCHECK`).
- `structure-tests.yaml:1-96` (image-structure assertions only).
- `rootfs/usr/local/bin/privacyidea_entrypoint.sh:1-55` (startup sequence, exec'd Gunicorn).

## Evidence for a container readiness check

- A readiness endpoint already exists and is cheap: `/healthz/readyz` returns HTTP 200 with `"status": "ready"` once privacyIDEA is up (consumed by `run-tests.sh`).
- Today that signal is only reachable by client-side polling from a sidecar; the image itself reports nothing to Docker (`docker ps` HEALTH STATUS stays empty), and compose/Kubernetes cannot use `depends_on: condition: service_healthy` or native probe wiring without a `HEALTHCHECK`.
- A `HEALTHCHECK` would give operators `docker inspect --health` visibility with no sidecar.

## Evidence against

- The final image is `python:3.14-slim` and has no `curl`/`wget`; a `HEALTHCHECK` would need a Python-based probe (e.g. `python -c 'urllib.request...'`), adding a small recurring process and failure-mode surface inside the app container running as `nobody`.
- Readiness is already covered in CI by the `sut` polling loop; orchestrators can poll the HTTP endpoint directly, which is the more common pattern for app-level readiness.
- `HEALTHCHECK` status does not stop or restart the container by itself; orchestrators remain responsible for action.

## Confidence

High on the factual claims (all verified against tracked files at the pilot base); the for/against weighting depends on deployment environment, which repo evidence cannot settle.
