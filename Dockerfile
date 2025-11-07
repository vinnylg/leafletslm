FROM python:3.12-slim

# Variáveis de ambiente para uv
ENV PATH="/workspace/.venv/bin:$PATH" \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y sudo \
    git \
    vim \
    make \
    curl \
    tree \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/* &&\
    update-ca-certificates

ARG USER=devel
ARG UID=1000
ARG GID=1000

RUN if ! getent group ${GID} >/dev/null 2>&1; then \
    groupadd --gid ${GID} ${USER}; \
    fi

RUN if id -u ${USER} >/dev/null 2>&1; then \
    usermod --uid ${UID} --gid ${GID} ${USER}; \
    else \
    useradd --uid ${UID} --gid ${GID} -m -s /bin/bash ${USER}; \
    fi

RUN echo "${USER} ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/${USER} && \
    chmod 0440 /etc/sudoers.d/${USER}

USER ${USER}

# Instalar uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/${USER}/.local/bin:${PATH}"

WORKDIR /workspace

# COPY --chown=${USER}:${USER} pyproject.toml uv.lock* ./

# RUN uv sync --locked --no-install-project

# 3. Copiar código fonte
COPY --chown=${USER}:${USER} . .

RUN uv sync --locked

# Shell completions
RUN echo 'eval "$(uv generate-shell-completion bash)"' >> ~/.bashrc && \
    echo 'eval "$(uvx --generate-shell-completion bash)"' >> ~/.bashrc