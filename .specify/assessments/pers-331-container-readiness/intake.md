# Intake — pers-331-container-readiness (PERS-331)

Prompt: "PERS-331: assess whether a container readiness check is warranted from repository docs/code evidence only. Do not implement. Record evidence, uncertainty, sources, confidence, evidence for and against, and operational tradeoffs. The concept must include the exact lowercase word tradeoff. The decision must contain exactly one unformatted line: Verdict: go, Verdict: needs-clarification, or Verdict: kill. Case key pers-331-container-readiness."

## Request

Assess whether the privacyidea-docker image should carry a container-level readiness check (Docker `HEALTHCHECK` and/or an orchestrator readiness probe condition), based only on repository docs/code evidence. No implementation.

## Evidence gathered (sources)

- `run-tests.sh:9-27` — the Compose integration suite polls `http://pi-app:8080/healthz/readyz` (HTTP 200 and body `"status": "ready"`) in a 30x1s loop from the `sut` sidecar container.
- `docker-compose-test.yml` — `sut` uses `depends_on: [pi-app]` with no health condition; readiness is handled client-side by `run-tests.sh`.
- `Dockerfile` (whole file) and all tracked `*.yml`/`*.sh` — no `HEALTHCHECK` instruction exists anywhere.
- `structure-tests.yaml` — container-structure-test asserts image metadata/files/config, not runtime readiness.
- `Dockerfile:48-70` — final image is `python:3.14-slim` based, runs as `nobody`, entrypoint `tini -- privacyidea_entrypoint.sh`, exposes `8080/tcp`.
- `rootfs/usr/local/bin/privacyidea_entrypoint.sh` — execs Gunicorn as a direct child of tini.
- The slim final image has Python but no `curl` (curl is installed via `apk` only in the alpine `sut` image in `run-tests.sh:3`).

## Uncertainty

- Whether orchestrators in real deployments (compose `service_healthy`, Kubernetes probes) would benefit is outside what repo evidence can show; no deployment-specific verification is claimed.

## Confidence

High that the repo currently has no container-level readiness signal and relies on client-side polling of `/healthz/readyz`; medium on whether adding one is net-positive given the probe-tooling constraint.
