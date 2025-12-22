FROM python:3.12-slim AS dev

ARG USER=devil
ARG UID=1000
ARG GID=1000

EXPOSE 3000
EXPOSE 8000

ENV TERM=xterm-256color
ENV PATH="/home/${USER}/.local/bin:${PATH}"

ENV PATH="/workspace/.venv/bin:$PATH"
ENV UV_PROJECT_ENVIRONMENT="/workspace/.venv"
ENV UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y sudo \
    git \
    vim \
    make \
    curl \
    tree \
    procps \
    entr \
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

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

RUN echo '' >> ~/.bashrc && \
    echo '# Snippet inserted by Dockerfile' >> ~/.bashrc && \
    echo '' >> ~/.bashrc && \
    echo 'eval "$(uv generate-shell-completion bash)"' >> ~/.bashrc && \
    echo 'eval "$(uvx --generate-shell-completion bash)"' >> ~/.bashrc && \
    echo '' >> ~/.bashrc && \
    echo 'source /workspace/.scripts/bash_options' >> ~/.bashrc && \
    echo 'source /workspace/.venv/bin/activate' >> ~/.bashrc 

WORKDIR /workspace

COPY --chown=${UID}:${GID} entrypoint.sh .
RUN chmod +x ./entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]

FROM dev AS prod

RUN echo "Not implemented yet"

# COPY --chown=${UID}:${GID} . .

## vou deixar incompleto mesmo, mas aqui não vai ser usado volumes e sera configurado tudo na imagem
# 
# CMD ["python", "-m", "drugslm"]
#
##
