# DrugSLM

[![CCDS](https://img.shields.io/badge/CCDS-Project%20template-328F97?logo=cookiecutter)](https://cookiecutter-data-science.drivendata.org/)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](LICENSE)

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
docker compose up -d drugslm  # Base container
docker compose up -d mkdocs   # Documentation server (localhost:8000)

# Attach to container
docker exec -it drugslm_base bash
```

## 📁 Project Structure

## 🛠️ Development Workflow

## 🤝 Contributing

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

## 📄 License

This project is licensed under the BSD 3-Clause License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

**Vinícius de Lima Gonçalves**  
Master's Student in Computer Science  
Federal University of Paraná (UFPR)  
Curitiba, Brazil

> See more:
| [Documentation](docs/index.md)
| [Architecture](docs/architecture/index.md)
| [Infrastructure](docs/infrastructure.md)
| [Design](docs/design/index.md)
| [API Reference](docs/reference/index.md)
|