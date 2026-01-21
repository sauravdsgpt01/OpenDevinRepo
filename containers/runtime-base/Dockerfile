# OpenHands Runtime Base Image
# This image contains all heavy dependencies that rarely change:
# - System packages (git, curl, build-essential, etc.)
# - Node.js 22.x
# - Docker CE
# - Micromamba + Python 3.12 + Poetry
# - VS Code Server
# - Playwright + Chromium
# - uv package manager
#
# Build frequency: Weekly or on-demand (not on every PR)
# Expected build time: ~15-20 minutes
# Expected size: ~2-3 GB

FROM ubuntu:24.04

SHELL ["/bin/bash", "-c"]

# Shared environment variables (must match Dockerfile.j2)
ENV POETRY_VIRTUALENVS_PATH=/openhands/poetry \
    MAMBA_ROOT_PREFIX=/openhands/micromamba \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    EDITOR=code \
    VISUAL=code \
    GIT_EDITOR="code --wait" \
    OPENVSCODE_SERVER_ROOT=/openhands/.openvscode-server \
    PATH="/usr/bin:/bin:/usr/sbin:/sbin:/openhands/bin:$PATH"

# ================================================================
# Install base system dependencies
# ================================================================
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget curl ca-certificates sudo apt-utils git jq tmux build-essential ripgrep ffmpeg \
        coreutils util-linux procps findutils grep sed \
        libasound2-plugins libatomic1 && \
    (apt-get install -y --no-install-recommends libgl1 || apt-get install -y --no-install-recommends libgl1-mesa-glx) && \
    # Install Docker dependencies
    apt-get install -y --no-install-recommends apt-transport-https ca-certificates curl gnupg lsb-release && \
    # Install Node.js 22.x
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    TZ=Etc/UTC DEBIAN_FRONTEND=noninteractive \
        apt-get install -y --no-install-recommends nodejs python3.12 python-is-python3 python3-pip python3.12-venv && \
    # Setup corepack/yarn
    ln -s "$(dirname $(which node))/corepack" /usr/local/bin/corepack && \
    npm install -g corepack && corepack enable yarn && \
    # Install Poetry (system-level, for fallback)
    curl -fsSL --compressed https://install.python-poetry.org | python - && \
    # Clean up
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ================================================================
# Install uv (required by MCP)
# ================================================================
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="/openhands/bin" sh

# ================================================================
# Install Docker CE
# ================================================================
RUN apt-get update && \
    apt-get install -y ca-certificates curl && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc && \
    chmod a+r /etc/apt/keyrings/docker.asc && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Configure Docker daemon with MTU 1450 to prevent packet fragmentation issues
RUN mkdir -p /etc/docker && \
    echo '{"mtu": 1450}' > /etc/docker/daemon.json

# ================================================================
# Create openhands user
# ================================================================
RUN (if getent passwd 1000 | grep -q pn; then userdel pn; fi) && \
    (if getent passwd 1000 | grep -q ubuntu; then userdel ubuntu; fi) && \
    (if getent group 1000 | grep -q pn; then groupdel pn; fi) && \
    (if getent group 1000 | grep -q ubuntu; then groupdel ubuntu; fi)

RUN (if getent group 1000 >/dev/null 2>&1; then \
        groupadd openhands; \
    else \
        groupadd -g 1000 openhands; \
    fi) && \
    (if getent passwd 1000 >/dev/null 2>&1; then \
        useradd -g openhands -m -s /bin/bash openhands; \
    else \
        useradd -u 1000 -g openhands -m -s /bin/bash openhands; \
    fi) && \
    usermod -aG sudo openhands && \
    echo 'openhands ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers && \
    passwd -d openhands && \
    passwd -d root && \
    sed -i '/pam_rootok.so/d' /etc/pam.d/su && \
    sed -i '1i auth sufficient pam_rootok.so' /etc/pam.d/su

# Create necessary directories
RUN mkdir -p /openhands && \
    mkdir -p /openhands/logs && \
    mkdir -p /openhands/poetry && \
    mkdir -p /openhands/code/openhands && \
    touch /openhands/code/openhands/__init__.py && \
    chown -R openhands:openhands /openhands

# ================================================================
# Install Micromamba + Python 3.12 + Poetry
# ================================================================
RUN mkdir -p /openhands/micromamba/bin && \
    /bin/bash -c "PREFIX_LOCATION=/openhands/micromamba BIN_FOLDER=/openhands/micromamba/bin INIT_YES=no CONDA_FORGE_YES=yes $(curl -L https://micro.mamba.pm/install.sh)" && \
    /openhands/micromamba/bin/micromamba config remove channels defaults && \
    /openhands/micromamba/bin/micromamba config list && \
    chown -R openhands:openhands /openhands/micromamba && \
    chmod -R 755 /openhands/micromamba && \
    mkdir -p /root/.local/share/micromamba && \
    echo 'export PATH="/openhands/micromamba/bin:$PATH"' >> /etc/environment

# Create the openhands virtual environment and install poetry and python
USER openhands
RUN /openhands/micromamba/bin/micromamba create -n openhands -y && \
    /openhands/micromamba/bin/micromamba install -n openhands -c conda-forge poetry python=3.12 -y
USER root

# Set global git configuration
RUN git config --global user.name "openhands" && \
    git config --global user.email "openhands@all-hands.dev"

# ================================================================
# Install VS Code Server
# ================================================================
ARG RELEASE_TAG="openvscode-server-v1.98.2"
ARG RELEASE_ORG="gitpod-io"

RUN arch=$(uname -m) && \
    if [ "${arch}" = "x86_64" ]; then \
        arch="x64"; \
    elif [ "${arch}" = "aarch64" ]; then \
        arch="arm64"; \
    elif [ "${arch}" = "armv7l" ]; then \
        arch="armhf"; \
    fi && \
    wget https://github.com/${RELEASE_ORG}/openvscode-server/releases/download/${RELEASE_TAG}/${RELEASE_TAG}-linux-${arch}.tar.gz && \
    tar -xzf ${RELEASE_TAG}-linux-${arch}.tar.gz && \
    if [ -d "${OPENVSCODE_SERVER_ROOT}" ]; then rm -rf "${OPENVSCODE_SERVER_ROOT}"; fi && \
    mv ${RELEASE_TAG}-linux-${arch} ${OPENVSCODE_SERVER_ROOT} && \
    cp ${OPENVSCODE_SERVER_ROOT}/bin/remote-cli/openvscode-server ${OPENVSCODE_SERVER_ROOT}/bin/remote-cli/code && \
    rm -f ${RELEASE_TAG}-linux-${arch}.tar.gz && \
    chown -R openhands:openhands ${OPENVSCODE_SERVER_ROOT}

# ================================================================
# Install Playwright browsers (Chromium)
# ================================================================
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libnss3 libnspr4 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libxcomposite1 \
        libxdamage1 libxrandr2 libgbm1 libxss1 && \
    (apt-get install -y --no-install-recommends libasound2t64 || apt-get install -y --no-install-recommends libasound2) && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Playwright browsers in shared location
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers
RUN mkdir -p /opt/playwright-browsers && \
    /openhands/micromamba/bin/micromamba run -n openhands pip install playwright && \
    /openhands/micromamba/bin/micromamba run -n openhands playwright install chromium && \
    chmod -R 755 /opt/playwright-browsers && \
    # Create cache directories and symlinks for both users
    mkdir -p /home/openhands/.cache && \
    mkdir -p /root/.cache && \
    ln -sf /opt/playwright-browsers /home/openhands/.cache/ms-playwright && \
    ln -sf /opt/playwright-browsers /root/.cache/ms-playwright && \
    chown -h openhands:openhands /home/openhands/.cache/ms-playwright && \
    echo 'export PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers' >> /etc/environment

# ================================================================
# Final setup and environment configuration
# ================================================================
RUN chmod -R 755 /openhands/poetry && \
    chmod -R 755 /openhands/micromamba && \
    mkdir -p /openhands/workspace && chmod -R g+rws,o+rw /openhands/workspace && \
    chown -R openhands:openhands /openhands/workspace && \
    # Ensure PATH includes system binaries early in startup
    echo 'export PATH="/usr/bin:/bin:/usr/sbin:/sbin:$PATH"' >> /etc/environment && \
    echo 'export PATH="/usr/bin:/bin:/usr/sbin:/sbin:$PATH"' >> /etc/bash.bashrc && \
    # Set up conda environment activation for all users
    echo 'eval "$(/openhands/micromamba/bin/micromamba shell hook --shell bash)"' >> /etc/bash.bashrc && \
    echo 'micromamba activate openhands 2>/dev/null || true' >> /etc/bash.bashrc && \
    # Set up environment for root user
    echo 'export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/openhands/micromamba/bin:$PATH"' >> /root/.bashrc && \
    echo 'export PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers' >> /root/.bashrc && \
    echo 'eval "$(/openhands/micromamba/bin/micromamba shell hook --shell bash)"' >> /root/.bashrc && \
    echo 'micromamba activate openhands 2>/dev/null || true' >> /root/.bashrc && \
    # Set up environment for openhands user
    echo 'export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/openhands/micromamba/bin:$PATH"' >> /home/openhands/.bashrc && \
    echo 'export PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers' >> /home/openhands/.bashrc && \
    echo 'eval "$(/openhands/micromamba/bin/micromamba shell hook --shell bash)"' >> /home/openhands/.bashrc && \
    echo 'micromamba activate openhands 2>/dev/null || true' >> /home/openhands/.bashrc && \
    chown openhands:openhands /home/openhands/.bashrc && \
    # Final cleanup
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /openhands/code
