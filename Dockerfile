FROM python:3.12-slim

ARG USER=devel
ARG UID=1000
ARG GID=1000

EXPOSE 3000
EXPOSE 8000

ENV TERM=xterm-256color
ENV PATH="/home/${USER}/.local/bin:${PATH}"
ENV UV_LINK_MODE=copy
ENV VIRTUAL_ENV="/opt/venv"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV UV_PROJECT_ENVIRONMENT="$VIRTUAL_ENV"

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

RUN mkdir -p /opt/venv && chown ${UID}:${GID} /opt/venv

USER ${USER}
WORKDIR /workspace
COPY --chown=${UID}:${GID} . .

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Try to use uv.lock but if it doesn't works run without it (this force update)
RUN uv sync --all-extras --locked || echo "uv.lock not found" && uv sync --all-extras

RUN echo 'eval "$(uv generate-shell-completion bash)"' >> ~/.bashrc && \
    echo 'eval "$(uvx --generate-shell-completion bash)"' >> ~/.bashrc && \
    echo 'source $VIRTUAL_ENV/bin/activate' >> ~/.bashrc

RUN which python && python --version && python -c "import drugslm; print(f'{drugslm}')"

# ENTRYPOINT ["make"]

CMD ["make", "sleep"]

