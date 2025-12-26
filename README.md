# DrugSLM

[![CCDS](https://img.shields.io/badge/CCDS-Project%20template-328F97?logo=cookiecutter)](https://cookiecutter-data-science.drivendata.org/)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-MkDocs-blue?logo=materialformkdocs)](docs/index.md)

**Small Language Model for Pharmaceutical Information**

Master's thesis in Computer Science at the Federal University of Paraná (UFPR), focusing on domain-specific language models trained on drug package inserts and medical databases.

## 🚀 Quick Start

```bash
# Clone and start
git clone https://github.com/vinnylg/drugslm.git
cd drugslm
docker compose up -d dev      # Development container
docker compose up -d mkdocs   # Docs at localhost:8000

# Attach to dev container
docker exec -it drugslm-dev bash
```

**Prerequisites:** Docker & Docker Compose, [uv](https://github.com/astral-sh/uv), make

## 📖 Documentation

| Section | Description |
|:--------|:------------|
| [Getting Started](docs/getting-started.md) | Installation and setup guide |
| [Architecture](docs/architecture/index.md) | Visual standards and roadmap |
| [Infrastructure](docs/infrastructure.md) | Hardware and container setup |
| [Design Reference](docs/design/index.md) | System design and workflows |
| [API Reference](docs/reference/index.md) | Code documentation |

## 📝 Citation

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

## 📄 License

BSD 3-Clause License - see [LICENSE](LICENSE) for details.

---

**Author:** Vinícius de Lima Gonçalves | UFPR, Curitiba, Brazil
