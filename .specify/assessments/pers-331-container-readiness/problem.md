# Problem statement — pers-331-container-readiness

The container image exposes a runtime readiness endpoint (`/healthz/readyz`) but declares no container-level readiness signal: no `HEALTHCHECK` in the `Dockerfile`, and the Compose test setup waits for readiness only client-side (`run-tests.sh` polling loop from the `sut` service, `depends_on` without a health condition). Operators and orchestrators therefore cannot consume a Docker-native health status, and the only readiness verification is CI-side.
