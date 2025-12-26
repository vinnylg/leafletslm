# Getting Started

<!-- TODO(!documentation): Sync this file with root README.md
     Currently duplicated because include-markdown causes link validation issues.
     README has links like docs/index.md which break when included inside docs/.
     Consider a pre-build script or MkDocs hook to transform links.
     labels: documentation, technical-debt -->

## Small Language Model (SLM) for Pharmaceutical Information

Master's thesis in Computer Science at the Federal University of Paraná (UFPR), focusing on the development of a specialized language model using drug package inserts and medical databases.

## 🎯 Overview

DrugSLM is a research project that aims to create a domain-specific language model trained on pharmaceutical data from regulatory agencies.

## 🚀 Quick Start

### Prerequisites

- **Docker & Docker Compose**
- [uv](https://github.com/astral-sh/uv) package manager
- make

### Installation

#### Option 1: Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/vinnylg/drugslm.git
cd drugslm

# Start services
docker compose up -d dev       # Base container
docker compose up -d mkdocs    # Documentation server (localhost:8000)

# Attach to container
docker exec -it drugslm-dev bash
```

## 📁 Project Structure

<!-- TODO(!documentation): Add project structure tree
     Document the directory layout and purpose of each folder.
     labels: documentation -->

*Project structure documentation coming soon.*

## 🛠️ Development Workflow

<!-- TODO(!documentation): Document development workflow
     Explain make targets, testing, and contribution guidelines.
     labels: documentation -->

*Development workflow documentation coming soon.*

## 📝 Citation

If you use this work in your research, please cite:

```bibtex
@mastersthesis{goncalves2026drugslm,
  author  = {Gonçalves, Vinícius de Lima},
  title   = {DrugSLM: A Small Language Model for Pharmaceutical Information},
  school  = {Federal University of Paraná},
  year    = {2026},
  type    = {Master's Thesis},
  address = {Curitiba, Brazil}
}
```

## 👤 Author

**Vinícius de Lima Gonçalves**  
Master's Student in Computer Science  
Federal University of Paraná (UFPR)  
Curitiba, Brazil
