# Exemplo de como usar o multi-stage no Dockerfile para alternar GPU/CPU

## Dockerfile

```
# --- Estágio Base (Comum) ---
# Define um 'template' base com o código comum
FROM python:3.10-slim AS base
WORKDIR /app
COPY requirements.txt .
COPY start.sh .
COPY /src /app/src

# --- Alvo CPU (cpu-target) ---
# Pega o 'base' e instala dependências de CPU
FROM base AS cpu-target
RUN pip install -r requirements.txt \
    && pip install torch --index-url https://download.pytorch.org/whl/cpu

# O start.sh aqui NÃO precisa detectar GPU, ele JÁ SABE que é CPU
ENTRYPOINT ["/app/start.sh"]


# --- Alvo GPU (gpu-target) ---
# Começa de uma imagem NVIDIA, depois copia o código do 'base'
FROM nvidia/cuda:12.1.1-devel-ubuntu22.04 AS gpu-base
# Instala python, etc
RUN apt-get update && apt-get install -y python3 python3-pip

# Agora copiamos o código que estava no estágio 'base'
COPY --from=base /app /app
WORKDIR /app

# Instala dependências de GPU
RUN pip install -r requirements.txt \
    && pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# O start.sh aqui NÃO precisa detectar GPU, ele JÁ SABE que é GPU
ENTRYPOINT ["/app/start.sh"]
```

## Construir a imagem só com o docker

```bash
docker build --target cpu-target -t meu-app:cpu .
```

ou

```bash
docker build --target gpu-target -t meu-app:gpu .
```

## Construir a iamgem com docker compose

### docker-compose.yaml (Base, sem GPU)

```yaml
services:
  meu-servico:
    build:
      context: .
      target: cpu-target # Manda construir o alvo de CPU
    image: meu-app:cpu
```

### docker-compose.gpu.yaml (Sobrescreve com GPU)

```yaml
services:
  meu-servico: # Sobrescreve o serviço
    build:
      context: .
      target: gpu-target # Manda construir o alvo de GPU
    image: meu-app:gpu
    deploy: # E adiciona o hardware de GPU
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]
```
