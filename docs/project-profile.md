# Project profile: privacyidea-docker

Docker image packaging upstream privacyIDEA on `python:3.14-slim`; the repository holds build, configuration, test and release tooling, not the application source (`Dockerfile:44`, `README.md:5`).

## Languages and versions

- Python 3.14: base image `python:3.14-slim`, pinned by index digest in both stages (`Dockerfile:10`, `Dockerfile:48`). No `.python-version`, `pyproject.toml`, `setup.py`, `tox.ini` or `pytest.ini` exists in the tree.
- privacyIDEA installed from PyPI as `privacyidea==${VERSION}` (`Dockerfile:44`); supported floor is 3.14 (`ci.yml:107`, `release.yml:28`, `check-pi-version.yml:15`, `README.md:30`).
- `PI_VERSION=main` (the default, `Dockerfile:2`) resolves the newest version from the PyPI JSON API (`Dockerfile:16-25`); CI resolves the latest PyPI release, rejects anything that is not numeric or is below 3.14, and later asserts the installed distribution version (`ci.yml:104-125`, `ci.yml:156-167`).
- Extra Python dependencies pinned in `requirements.txt`: `psycopg2==2.9.13`, `gunicorn==26.2.0`, `certifi==2026.10.19` (`requirements.txt:1-2`, `requirements.txt:11`), installed last so they upgrade the transitive set (`Dockerfile:43-45`, `requirements.txt:4-10`).
- Shell: bash for container scripts (`rootfs/usr/local/bin/privacyidea_entrypoint.sh:1`, `rootfs/usr/local/bin/configure_privacyidea.sh:1`); POSIX `sh` for `run-tests.sh:1` and `prebuildfs/usr/sbin/install_packages:1`.
- privacyIDEA's own requirements are fetched at build time from the upstream ref (`Dockerfile:28-39`), so the full transitive dependency set is not pinned in this repo — `unverified` in-repo, resolved only during an image build.

## Frameworks

- Docker multi-stage build: builder stage creates the venv (`Dockerfile:10`), runtime stage copies it (`Dockerfile:48`, `Dockerfile:66`).
- `tini` as PID 1 with the entrypoint as its argument (`Dockerfile:70`).
- gunicorn WSGI server, config in `rootfs/opt/privacyidea/gunicorn_conf.py` (`rootfs/usr/local/bin/privacyidea_entrypoint.sh:41-50`).
- privacyIDEA as a Flask app: `privacyidea.app:create_app(config_name='production', config_file=...)` (`rootfs/usr/local/bin/privacyidea_entrypoint.sh:46`, `:50`).
- SQLAlchemy, used directly for the "schema already present?" preflight and in the password round-trip test (`rootfs/usr/local/bin/configure_privacyidea.sh:230-239`, `tests/test-db-uri-encoding.sh:30-37`).
- `envsubst` renders `pi.cfg` from `rootfs/opt/templates/pi-config.template` (`rootfs/usr/local/bin/configure_privacyidea.sh:116`).
- container-structure-test v1.22.1 for image assertions (`structure-tests.yaml:1`, `ci.yml:129-145`).
- No Python test framework: `tests/` contains shell scripts only (`tests/test-db-uri-encoding.sh:1`, `tests/test-release-input.sh:1`).

## Repo layout

```text
Dockerfile                multi-stage image build                          Dockerfile:10,48
Makefile                  dev targets; default goal is help                Makefile:6,40
requirements.txt          additional pinned Python deps                    requirements.txt:1-11
structure-tests.yaml      container-structure-test schema 2.0.0             structure-tests.yaml:1
run-tests.sh              integration client run inside the compose "sut"  run-tests.sh:1-41
docker-compose.yml        demo stack: pi+mariadb, wordpress+mariadb        docker-compose.yml:1-58
docker-compose-test.yml   CI stack: pi-app + alpine sut                    docker-compose-test.yml:1-34
prebuildfs/               install_packages apt helper                      prebuildfs/usr/sbin/install_packages:1
rootfs/usr/local/bin/     entrypoint, configure, common shell functions    rootfs/usr/local/bin/_privacyidea_common.sh:1
rootfs/opt/               gunicorn_conf.py, pi-logging.yml, templates/     rootfs/opt/privacyidea/gunicorn_conf.py:1
tests/                    4 shell test scripts                             tests/test-release-input.sh:1
.github/workflows/        ci.yml, release.yml, check-pi-version.yml        .github/workflows/ci.yml:1
.github/scripts/          release input, promotion and ref helpers         .github/scripts/resolve-release-input.sh:1
docs/                     release runbook and this profile                 docs/release-runbook.md:1
example/                  PostgreSQL compose example                       example/docker-compose-posgresql.yml:1
```

## Build / test / lint / run commands

| Command | Defined at | Status in this verification |
| :-- | :-- | :-- |
| `make build` | `Makefile:12-13` | exists; `make -n build` resolves to `docker build -t mr-ssd/privacyidea:dev .`; image build not executed (`unverified`) |
| `make run` | `Makefile:18-19` | exists; runs `cleanup create_volume secretkey pipepper` then `docker run -p 8080:8080 --env-file=secretkey --env-file=pipepper`; not executed (`unverified`) |
| `make test` | `Makefile:37-38` | exists; runs `container-structure-test test --image $(IMAGE):$(IMAGE_TAG) --config structure-tests.yaml`; binary absent here, not executed (`unverified`) |
| `make push` | `Makefile:15-16` | exists; `docker push $(IMAGE):$(IMAGE_TAG)`; no credentials, not executed (`unverified`) |
| `make cleanup` | `Makefile:32-35` | exists; stops/removes `privacyidea-dev` and `sudo rm -rf /tmp/privacyidea-data` |
| `make help` | `Makefile:6-10`, default `Makefile:40` | exists; default goal |
| `docker build --build-arg PI_VERSION=<version> -t privacyidea:test .` | `ci.yml:122-125` | exists; image build not executed (`unverified`) |
| `container-structure-test test --image privacyidea:test --config structure-tests.yaml` | `ci.yml:147-148` | exists; not executed (`unverified`) |
| `docker compose --file docker-compose-test.yml up --no-build --exit-code-from sut --timeout 120` (after building `pi-app`) | `ci.yml:150-154`, `docker-compose-test.yml:3-7` | exists; not executed (`unverified`) |
| `bash tests/test-release-input.sh` | `ci.yml:83-84` | exists; **executed here and passes** (script reports `all 32 release input cases passed`); ends by running `tests/test-release-promotion.sh` (`tests/test-release-input.sh:333`) |
| `IMAGE=privacyidea:test bash tests/test-db-uri-encoding.sh` | `tests/test-db-uri-encoding.sh:10`, `:13` | exists; needs a built image, not executed (`unverified`) |
| hadolint (`failure-threshold: error`) | `ci.yml:27-33` | CI-only, no Makefile target |
| shellcheck (`severity: error`) | `ci.yml:47-53` | CI-only, no Makefile target |
| actionlint 1.7.12 | `ci.yml:55-69` | CI-only, no Makefile target |

There is no lint, format or `fmt` target in the `Makefile` (`Makefile:1-40`); lint runs only in CI. `tests/test-release-input.sh` has 32 `assert_case` call sites and needs no network, Docker or GitHub (`tests/test-release-input.sh:5-9`). `tests/test-release-promotion.sh` stubs `docker` and a bare git remote (`tests/test-release-promotion.sh:2`, `:9-37`).

## CI/CD

- `.github/workflows/ci.yml` — `pull_request` only (`ci.yml:3-4`), per-PR concurrency with cancel-in-progress (`ci.yml:9-11`), no secrets. Jobs: `lint` (hadolint + SARIF upload, shellcheck, actionlint; `ci.yml:14-69`), `release-input` (`bash tests/test-release-input.sh`; `ci.yml:71-84`), `test` matrix on native `ubuntu-24.04` / `ubuntu-24.04-arm` (`ci.yml:88-97`) building the image, running structure tests, the compose integration test, an installed-version assertion and cleanup (`ci.yml:122-171`).
- `.github/workflows/release.yml` — triggers on `v*` tag pushes, pushes to `main`, and `workflow_dispatch` with `channel` (`release`/`edge`) and optional `pi_version` (`release.yml:3-21`); default permissions `{}` (`release.yml:25`). Jobs: `validate` (routing via `.github/scripts/resolve-release-input.sh`, publish decision from the GitHub release ledger; `release.yml:52-109`), `reserve` (dated identity intent; `release.yml:115-158`), `build` (one multi-arch staging index, `linux/amd64,linux/arm64`, provenance `mode=max`, SBOM; `release.yml:160-292`), `test` (pulls the exact digest per arch, structure tests, compose integration test, installed-version assertion, Trivy SARIF plus a blocking CRITICAL table gate; `release.yml:294-423`), `publish` (numeric release promotion, `environment: release`, serialized `release-publish` concurrency, GitHub release, `latest` move; `release.yml:425-685`), `publish-edge` (GHCR-only `edge` + `sha-<12>`; `release.yml:690-749`).
- `.github/workflows/check-pi-version.yml` — daily cron at midnight UTC (`check-pi-version.yml:3-5`): discovers numeric upstream tags at or above 3.14, creates only versions listed in `vars.FEEDER_APPROVED_VERSIONS` (`check-pi-version.yml:84-151`, `:93`), dispatches `release.yml` per new tag and verifies a queued run (`check-pi-version.yml:153-201`), then re-dispatches approved tags that have no GitHub release (`check-pi-version.yml:203-283`).
- Dependabot: weekly updates for `github-actions`, `docker`, `docker-compose` and `pip` (`.github/dependabot.yml:2-41`); Actions are pinned to full commit SHAs (`ci.yml:23`).
- No merge/PR automation, deploy workflow or IaC (no Terraform, Ansible or Kubernetes manifests) exists in-repo.

## Environments

- Image: `python:3.14-slim` pinned by index digest in both stages (`Dockerfile:10`, `Dockerfile:48`); exact Debian release behind the digest is not stated in-repo (`README.md:12` says "Debian") — `unverified`.
- Runtime: user `nobody` (`Dockerfile:64`), workdir `/opt/privacyidea` (`Dockerfile:65`), `EXPOSE 8080/tcp` (`Dockerfile:68`), `VOLUME /data/privacyidea` (`Dockerfile:69`), `ENTRYPOINT` = tini + entrypoint script (`Dockerfile:70`); asserted by `structure-tests.yaml:17-21`.
- Default environment: `PI_SKIP_BOOTSTRAP=false`, `PI_AUTO_UPDATE=false`, `PI_DB_VENDOR=sqlite`, `PI_DATA_DIR=/data/privacyidea`, `PI_CFG_DIR=/etc/privacyidea`, `PI_CFG_FILE=pi.cfg` (`Dockerfile:51-57`).
- Mount directory: `/etc/privacyidea/mount` when it exists, otherwise `/mnt/privacyidea` (`rootfs/usr/local/bin/privacyidea_entrypoint.sh:15-21`).
- Local dev: `make run` with generated `secretkey`/`pipepper` files (`Makefile:24-30`); no data volume is passed, so state dies with the container (`Makefile:19`).
- Demo stack: `docker-compose.yml` — `pi` built from `.`, `pi-db` `mariadb:10.11`, plus an unrelated WordPress stack (`docker-compose.yml:1-58`); fixed test credentials (`docker-compose.yml:22-26`).
- CI/test stack: `docker-compose-test.yml` — `pi-app` on SQLite and an alpine `sut` running `run-tests.sh` (`docker-compose-test.yml:1-34`).
- PostgreSQL example: `postgres:14` plus `docker.io/kheeklab/privacyidea:dev` (`example/docker-compose-posgresql.yml:1-31`).
- CI runners: GitHub-hosted `ubuntu-24.04` and `ubuntu-24.04-arm` (`ci.yml:94-97`, `release.yml:303-306`).
- Release job environment: GitHub environment `release` (`release.yml:437`); secrets `GITHUB_TOKEN`, `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`; variable `DOCKERHUB_NAMESPACE` (`release.yml:200-202`); approval list variable `FEEDER_APPROVED_VERSIONS` (`check-pi-version.yml:93`). Whether those exist on this fork is outside the repo — `unverified`.
- Registries: GHCR for all channels, Docker Hub for stable releases only (`README.md:19-22`; `release.yml:211-220`).
- No staging or production deployment environment exists in the repo (inferred from the complete file tree).

## Conventions

- Container shell scripts use `set -e` only (`rootfs/usr/local/bin/privacyidea_entrypoint.sh:2`, `rootfs/usr/local/bin/configure_privacyidea.sh:2`); `_privacyidea_common.sh` sets no shell option (`rootfs/usr/local/bin/_privacyidea_common.sh:1-3`); tests use `set -euo pipefail` or `set -eu` (`tests/test-release-input.sh:10`, `run-tests.sh:2`).
- Both `function name {` and `name() {` forms coexist, even in one file (`rootfs/usr/local/bin/configure_privacyidea.sh:20` vs `:34`).
- Dockerfile: ARGs declared before the first `FROM` and re-declared inside each stage (`Dockerfile:1-13`, `Dockerfile:48-49`); all ENV defaults in one block (`Dockerfile:51-57`); runtime packages installed and directories chowned before `USER nobody` (`Dockerfile:61-64`).
- Configuration is env-var-only; `pi.cfg` is generated output and never hand-edited (`rootfs/usr/local/bin/configure_privacyidea.sh:106-118`).
- Hook scripts are `source`d into the entrypoint shell, not run in a subshell (`rootfs/usr/local/bin/_privacyidea_common.sh:23`, `README.md:163`); they run in alphabetical order (`rootfs/usr/local/bin/_privacyidea_common.sh:12`, `:18`).
- Variable namespaces: `PI_*` for app/config, `GUNICORN_*` for server tuning, `PI_DB_*` for database (`rootfs/opt/privacyidea/gunicorn_conf.py:5-37`, `rootfs/usr/local/bin/configure_privacyidea.sh:51-103`).
- Commit subjects: recent history uses conventional-commit prefixes (`fix:`, `refactor:`, `test:`; HEAD `f3c01c2`); older commits use gitmoji and plain imperative subjects (16 of the last 200 subjects start with a non-alphanumeric character). No CI or hook enforces a message format (`git log`, `ci.yml:1-171`).
- Branches: `main`, numeric release branches (`3.9`, `3.9.2`, `3.10`, `3.11.0`, …), feature/fix branches, and `agent/<role>/<id>` agent branches (`git branch -r`).
- User docs are tables in `README.md` (`README.md:80-131`); operational rules live in `docs/release-runbook.md:1-60`.
- Stated invariant: non-root image (`Dockerfile:64`) and an `exec`-based handoff to gunicorn so SIGTERM reaches gunicorn (`rootfs/usr/local/bin/privacyidea_entrypoint.sh:36-51`).

## Key directories

Container paths:

| Path | Contents | Citation |
| :-- | :-- | :-- |
| `/opt/privacyidea` | Python venv and privacyIDEA app code | `Dockerfile:8`, `Dockerfile:66` |
| `/opt/templates` | `pi-config.template` rendered by envsubst | `Dockerfile:67`, `rootfs/opt/templates/pi-config.template:1`, `structure-tests.yaml:24-29` |
| `/etc/privacyidea` | generated `pi.cfg`, optional `server.key`/`server.crt` | `Dockerfile:55`, `Dockerfile:62`, `rootfs/usr/local/bin/privacyidea_entrypoint.sh:39-46` |
| `/data/privacyidea` | SQLite DB, `keys/`, `.privacyidea_initialized` marker | `Dockerfile:54`, `rootfs/usr/local/bin/configure_privacyidea.sh:95`, `:201-209` |
| `/var/log/privacyidea` | log directory created at build time | `Dockerfile:62`, `structure-tests.yaml:54-56` |
| `/usr/local/bin` | entrypoint, configure and common scripts | `Dockerfile:67`, `structure-tests.yaml:30-41` |
| `/usr/local/privacyidea/scripts` | user `pre-configure` / `pre-startup` hook dirs | `rootfs/usr/local/bin/privacyidea_entrypoint.sh:24`, `:27` |

Repository paths: `.github/workflows/`, `.github/scripts/`, `rootfs/`, `prebuildfs/`, `tests/`, `docs/`, `example/` (see Repo layout).

## Known gotchas

- **Vendor alias**: `PI_DB_VENDOR` accepts exactly `mariadb`, `mysql`, `postgresql`, `sqlite`; unset means SQLite (`rootfs/usr/local/bin/configure_privacyidea.sh:53-96`). Any other value, including `postgres`, hits the unsupported-vendor error and exits (`rootfs/usr/local/bin/configure_privacyidea.sh:97-101`, message lists the four accepted values at `:99`).
- **Secrets are mandatory**: startup exits if `PI_SECRET_KEY` or `PI_PEPPER` is unset/empty (`rootfs/opt/templates/pi-config.template:5-13`); `make` generates both into repo-root files `secretkey` and `pipepper` (`Makefile:24-30`). `PI_DB_PASSWORD` is likewise required for MariaDB/MySQL and PostgreSQL (`rootfs/usr/local/bin/configure_privacyidea.sh:22`).
- **Bootstrap runs once**: marker `${PI_DATA_DIR}/.privacyidea_initialized` (`rootfs/usr/local/bin/configure_privacyidea.sh:205-211`, `:293`); `PI_SKIP_BOOTSTRAP=true` forces skipping (`:213-217`); with an external DB, a missing encfile while privacyIDEA tables exist aborts startup instead of regenerating keys (`:229-246`).
- **Admin defaults differ by vendor**: SQLite without `PI_ADMIN_USER`/`PI_ADMIN_PASSWORD` creates `admin`/`privacyidea`; non-SQLite refuses to start without them (`rootfs/usr/local/bin/configure_privacyidea.sh:274-291`).
- **`PI_DB_ARGS` is inserted verbatim** after comma-to-`&` conversion and quote/space stripping, so values containing `&`, `=`, `%`, `,` or spaces break the URI (`rootfs/usr/local/bin/configure_privacyidea.sh:62`, `:63`, `:75`; `README.md:94`).
- **`make run` keeps no data volume**: `create_volume` only `mkdir`s `/tmp/privacyidea-data` (`Makefile:21-22`) and `docker run` passes no `-v` (`Makefile:19`), so state lives in the container and `make cleanup` deletes it (`Makefile:32-35`, which uses `sudo rm -rf`).
- **Logging default is stdout**: `pi-logging.yml` uses the `console` handler (`rootfs/opt/privacyidea/pi-logging.yml:8-12`, `:25`), and only a real `PI_LOGFILE` path switches to the rotating file handler; `/dev/stdout` is explicitly not used for it (`rootfs/usr/local/bin/configure_privacyidea.sh:129-164`). `/var/log/privacyidea` exists but stays unused by default (`Dockerfile:62`).
- **No HEALTHCHECK**: `curl` is installed in the image (`Dockerfile:61`), but the Dockerfile defines no `HEALTHCHECK` instruction; `AGENTS.md:116` records that the install was intended for one.
- **Ownership**: `/data/privacyidea` and `/etc/privacyidea` are chowned to `nobody` at build time (`Dockerfile:62-63`); bind mounts and reused named volumes do not inherit it (`README.md:218`).
- **Two scanned mount roots**: the entrypoint prefers `/etc/privacyidea/mount` and falls back to `/mnt/privacyidea` (`rootfs/usr/local/bin/privacyidea_entrypoint.sh:15-21`); `README.md:146-147` documents only `/mnt/privacyidea`.
- **Structure tests hardcode Dockerfile defaults**: env values, `user: nobody`, workdir, entrypoint, port and volume are asserted in `structure-tests.yaml:4-21`, so changing a Dockerfile default requires editing that file in the same change.
- **`.gitignore` lists tracked paths**: `example`, `LICENSE`, `Makefile` and `.gitignore` itself are ignored (`.gitignore:1`, `:3-5`), although they are tracked; new files under `example/` are ignored unless force-added.
- **Release approval gate**: the daily feeder creates/dispatches a version only when it is listed in `FEEDER_APPROVED_VERSIONS` (`check-pi-version.yml:93`, `:124-127`); Docker Hub staging must match the tested GHCR digest or promotion refuses (`release.yml:286-289`); provenance/SBOM are attached to the GHCR index only (`release.yml:591`).
- **TLS**: HTTPS is used only when both `/etc/privacyidea/server.key` and `/etc/privacyidea/server.crt` exist, bound to `PI_SSLPORT` (default 8443) (`rootfs/usr/local/bin/privacyidea_entrypoint.sh:39-46`, `README.md:110`).

### Doc-vs-code disagreements found (recorded, not fixed)

| # | Doc claim | What the code does | Citation |
| :-- | :-- | :-- | :-- |
| 1 | `README.md` prose says "on postgres" when describing `PI_DB_HOST`/`PI_DB_PORT`, inviting `postgres` as a vendor value | Code accepts only `postgresql` (plus `mariadb`, `mysql`, `sqlite`); `postgres` is rejected. README never lists the accepted vendor values | `README.md:92-93` vs `rootfs/usr/local/bin/configure_privacyidea.sh:67`, `:99` |
| 2 | `AGENTS.md` pins "psycopg2==2.9.10, gunicorn==23.0.0" | Actual pins are `psycopg2==2.9.13`, `gunicorn==26.2.0` | `AGENTS.md:41` vs `requirements.txt:1-2` |
| 3 | `AGENTS.md` cites Dockerfile lines that do not exist in the current 70-line file (`Dockerfile:28–50`, `:1–50`, `:49` for VOLUME, `:44` for USER, `:41` for curl, `:42–43` for chown) | Actual locations: stages `:10`/`:48`, `VOLUME` `:69`, `USER nobody` `:64`, curl `:61`, chown `:62-63` | `AGENTS.md:7`, `:37`, `:95`, `:96`, `:116`, `:118` vs `Dockerfile:10`, `:48`, `:61`, `:62-63`, `:64`, `:69` |
| 4 | `AGENTS.md` says shellcheck runs at `warning` | CI uses `severity: error` | `AGENTS.md:32` vs `ci.yml:52` |
| 5 | `AGENTS.md` says `tests/test-release-input.sh` has 18 cases | The script runs 32 cases | `AGENTS.md:44` vs `tests/test-release-input.sh:114-265` |
| 6 | `AGENTS.md` says recent commits use gitmoji + imperative subject | Recent history uses conventional prefixes (`fix:`, `refactor:`, `test:`) | `AGENTS.md:106` vs HEAD `f3c01c2` and `git log` |
| 7 | `release.yml` and `release-refs.sh` claim regression coverage by `tests/test-release-refs.sh` | That file does not exist; `tests/` holds four other scripts and CI runs only `tests/test-release-input.sh` | `release.yml:35`, `.github/scripts/release-refs.sh:8` vs `tests/`, `ci.yml:84` |
| 8 | `README.md` lists only `/mnt/privacyidea` and `/usr/local/privacyidea/scripts` as scanned folders | The entrypoint prefers `/etc/privacyidea/mount` when present and falls back to `/mnt/privacyidea`; `CLAUDE.md:41` documents both | `README.md:146-147`, `:182` vs `rootfs/usr/local/bin/privacyidea_entrypoint.sh:15-20`, `CLAUDE.md:41` |

## Last verified date

Last verified date: 2026-11-23 (HEAD `f3c01c28cefd6f3df6ea2fe95c4653088ee4024e`).

Verified by reading every cited file at that commit; `make -n build`, `make -n test` and `make -n run` resolve to the commands above; `bash tests/test-release-input.sh` was executed and passed (it also runs `tests/test-release-promotion.sh`); `bash -n` passes on all twelve shell scripts in the repo. Marked `unverified`: image build/run, container-structure-test execution, the compose integration test, `tests/test-db-uri-encoding.sh` (needs a built image), the exact Debian release behind the pinned base-image digest, the transitive privacyIDEA dependency set, any registry/publishing path (no credentials or network), and fork-level settings (Actions, `release` environment, `FEEDER_APPROVED_VERSIONS`, `DOCKERHUB_*`).

Note: this repository checkout is a fork of `kheeklab/privacyidea-docker`; the fork has no pull requests, so PR and release history referenced above lives upstream (`gh repo view`, `gh pr list`).
