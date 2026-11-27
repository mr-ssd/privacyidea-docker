# Decision — pers-331-container-readiness

A container readiness check is warranted in principle (the `/healthz/readyz` endpoint exists but no `HEALTHCHECK` consumes it), but the probe mechanism inside the slim runtime image (Python-based, since no curl) and the choice between image-level `HEALTHCHECK` versus orchestrator-level probes need a maintainer decision before implementation.

Verdict: needs-clarification

A go would require a separate feature issue and approval; this PR is assessment-only.
