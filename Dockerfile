FROM python:3.12-slim

ARG USER=devel
ARG UID=1000
ARG GID=1000

ENV PATH="/home/${USER}/.local/bin:${PATH}"
ENV PATH="/workspace/.venv/bin:${PATH}"
ENV VIRTUAL_ENV=/workspace/.venv
ENV UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y sudo \
    git \
    vim \
    make \
    curl \
    tree \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/* &&\
    update-ca-certificates

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

WORKDIR /workspace

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

COPY --chown=${USER}:${USER} . .

RUN uv venv ${VIRTUAL_ENV}}
# RUN source ${VIRTUAL_ENV}/bin/activate
RUN uv sync --all-extras --locked

RUN echo 'eval "$(uv generate-shell-completion bash)"' >> ~/.bashrc && \
    echo 'eval "$(uvx --generate-shell-completion bash)"' >> ~/.bashrc

RUN chmod -R 777 /workspace/scripts

# ENTRYPOINT ["/workspace/scripts/start-dagster.sh"]