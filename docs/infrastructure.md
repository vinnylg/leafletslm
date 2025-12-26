# Infrastructure

This document details the infrastructure setup, deployment configurations, and experimental hardware used in the DrugSLM project.

<!-- TODO(!documentation): Document complete hardware specifications
     Include CPU, RAM, storage details for the development machine.
     Add GPU model, VRAM, and CUDA version information.
     labels: documentation, infrastructure -->

## 🖥️ Hardware Specifications

<!-- TODO(!documentation): Add hardware specs table
     Document the physical machine constraints for reproducibility.
     labels: documentation -->

*Hardware specifications to be documented.*

## 🐳 Container Orchestration

The project uses Docker Compose for service orchestration. See `compose.yaml` for the complete configuration.

<!-- TODO(!documentation): Create container architecture diagram
     Visualize service dependencies and network topology.
     Use Mermaid flowchart following the standards in architecture/standards.md.
     labels: documentation, diagram -->

### Service Profiles

| Profile | Services | Purpose |
|:--------|:---------|:--------|
| `dev` | dev, mkdocs | Development environment |
| `chat` | ollama, chat | AI chat interface |
| `scrap` | selenium, firefox, chrome | Data collection |
| `nginx` | nginx, docs, chat, ollama | Production gateway |
| `funnel` | tailscale funnels | External exposure |

<!-- TODO(!documentation): Document each service in detail
     Explain purpose, ports, volumes, and dependencies for each service.
     labels: documentation -->

## 🌐 Network Architecture

<!-- TODO(!documentation): Document network topology
     Explain drugslm_network, service discovery, and port mappings.
     labels: documentation, infrastructure -->

*Network architecture to be documented.*

## 💾 Storage & Volumes

<!-- TODO(!documentation): Document volume strategy
     Explain ollama and chat volume persistence.
     Document data directory structure and backup strategy.
     labels: documentation, infrastructure -->

| Volume | Purpose | Persistence |
|:-------|:--------|:------------|
| `ollama` | Model weights storage | Persistent |
| `chat` | Chat history and config | Persistent |

## 🔐 Secrets Management

<!-- TODO(!documentation): Document secrets handling
     Explain .secrets/ directory structure and tailscale.env usage.
     Do not include actual secrets, only structure and examples.
     labels: documentation, security -->

*Secrets management approach to be documented.*

## 📊 Resource Constraints

<!-- TODO(!documentation): Document GPU requirements per task
     Specify VRAM needs for training, inference, and data processing.
     Include memory/CPU requirements for non-GPU tasks.
     labels: documentation, infrastructure -->

*Resource requirements to be documented.*
