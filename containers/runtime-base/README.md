# OpenHands Runtime Base Image

This directory contains the Dockerfile for the `runtime-base` image, a pre-built base image that contains all the heavy dependencies needed for the OpenHands runtime environment.

## Purpose

The runtime-base image significantly speeds up CI builds by pre-installing dependencies that rarely change:

| Component | Description |
|-----------|-------------|
| System packages | wget, curl, git, build-essential, ripgrep, ffmpeg, etc. |
| Node.js | Version 22.x |
| Docker CE | Full Docker Engine with buildx and compose plugins |
| Micromamba | With Python 3.12 and Poetry pre-installed |
| VS Code Server | OpenVSCode Server for IDE support |
| Playwright | Chromium browser for automation |
| uv | Package manager required by MCP |

## Build Time Improvements

| Scenario | Without runtime-base | With runtime-base |
|----------|---------------------|-------------------|
| Runtime image build | ~15 minutes | ~2-4 minutes |

## Building the Image

### Manual Build (via GitHub Actions)

1. Go to Actions → "Build Runtime Base Image"
2. Click "Run workflow"
3. The image will be pushed to `ghcr.io/openhands/runtime-base:latest`

### Local Build

```bash
# From repository root
docker buildx build \
  --platform linux/amd64 \
  -t ghcr.io/openhands/runtime-base:latest \
  ./containers/runtime-base
```

## Update Schedule

The image is automatically rebuilt:
- **Weekly**: Every Sunday at 2am UTC via scheduled workflow
- **On-demand**: Manual trigger when dependencies need updating

## Usage

The `ghcr-build.yml` workflow automatically uses this image as the base for runtime builds. No manual configuration is needed.

If you need to fall back to building from scratch (e.g., if runtime-base is broken), update the `define-matrix` job in `.github/workflows/ghcr-build.yml`:

```yaml
# Change from:
{ image: "ghcr.io/openhands/runtime-base:latest", tag: "ubuntu" }

# To:
{ image: "ubuntu:24.04", tag: "ubuntu" }
```

## Sunset Notice

⚠️ **Note**: The runtime image is scheduled to be deprecated on April 1st. This runtime-base image is a temporary optimization to reduce CI times until then.
