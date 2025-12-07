# Architecture

This document describes the technical architecture, design decisions, and data flows of the DrugsLM project.

---

## Table of Contents

- [System Overview](#system-overview)
- [Data Pipeline Architecture](#data-pipeline-architecture)
- [Scraper Design](#scraper-design)
- [Orchestration Strategy](#orchestration-strategy)
- [Storage Layer](#storage-layer)
- [Execution Modes](#execution-modes)
- [Design Decisions](#design-decisions)

---

## System Overview

DrugsLM follows a **modular pipeline architecture** where each stage is independently executable and composable through Dagster orchestration.

```mermaid
flowchart TB
    subgraph Sources["Data Sources"]
        ANVISA[ANVISA API/Web]
        WIKI[Wikipedia API]
        DRUGS[Medical Databases]
    end
    
    subgraph Acquisition["Acquisition Layer"]
        SC1[ANVISA Scraper]
        SC2[Wikipedia Scraper]
        SC3[PubMed Scraper]
    end
    
    subgraph Storage["Raw Storage"]
        PG[(PostgreSQL)]
        FS[File System<br/>Parquet/Pickle]
    end
    
    subgraph Processing["Processing Layer"]
        CLEAN[Data Cleaning]
        VALID[Validation]
        ENRICH[Enrichment]
    end
    
    subgraph Features["Feature Engineering"]
        NER[Named Entity<br/>Recognition]
        EMBED[Embeddings<br/>Generation]
    end
    
    subgraph Model["Model Layer"]
        VDB[(Vector DB)]
        GDB[(Graph DB)]
        LLM[LLM Training]
    end
    
    Sources --> Acquisition
    Acquisition --> Storage
    Storage --> Processing
    Processing --> Features
    Features --> Model
    
    style SC1 fill:#198754
    style SC2 fill:#e9ecef
    style SC3 fill:#e9ecef
```

**Legend**: 🟢 Implemented | ⚪ Planned

---

## Data Pipeline Architecture

### Current State (MVP)

The project currently focuses on the **data acquisition layer**, specifically the ANVISA scraper module.

```mermaid
flowchart LR
    A[ANVISA Website] -->|Selenium| B[Catalog Scraper]
    B -->|Pickle/CSV| C[Local Index]
    C --> D[Validation]
    D -->|Metadata| E[Progress Tracking]
    
    B -.->|Future| F[PDF Downloader]
    F -.->|Future| G[Text Extraction]
    
    style B fill:#198754
    style C fill:#198754
    style D fill:#198754
    style E fill:#198754
```

### Planned Architecture

```mermaid
flowchart TB
    subgraph Input["Data Ingestion"]
        WEB[Web Scraping]
        API[API Calls]
        FILE[File Upload]
    end
    
    subgraph Raw["Raw Layer"]
        RAW_PG[(PostgreSQL<br/>Metadata)]
        RAW_FS[File System<br/>PDFs/HTML]
    end
    
    subgraph Process["Processing"]
        PARSE[PDF Parser]
        NLP[NLP Pipeline]
        STRUCT[Structuring]
    end
    
    subgraph Interim["Interim Layer"]
        INT_FS[Parquet Files]
        INT_PG[(PostgreSQL)]
    end
    
    subgraph Analytics["Analytics"]
        AGG[Aggregations]
        FEAT[Feature Store]
    end
    
    subgraph Final["Final Layer"]
        VDB[(Chroma<br/>Vector DB)]
        NEO[(Neo4j<br/>Graph DB)]
        TRAIN[Training Data]
    end
    
    Input --> Raw
    Raw --> Process
    Process --> Interim
    Interim --> Analytics
    Analytics --> Final
```

---

## Scraper Design

### ANVISA Scraper Architecture

The ANVISA scraper follows a **resilient, resumable, parallel execution** pattern.

```mermaid
sequenceDiagram
    participant CLI
    participant Orchestrator
    participant Metadata
    participant Worker
    participant Selenium
    participant Storage
    
    CLI->>Orchestrator: run(threads=4, force=False)
    Orchestrator->>Metadata: fetch_metadata()
    Metadata->>Selenium: Connect to Hub
    
    loop For Each Category
        Selenium->>Selenium: Navigate & Extract Counts
        Selenium-->>Metadata: Return Stats
    end
    
    Metadata->>Storage: Save metadata.csv
    
    Orchestrator->>Orchestrator: Create ThreadPool(4)
    
    par Thread 1
        Orchestrator->>Worker: scrap_unit_category(cat=1)
        Worker->>Storage: Check Progress
        Storage-->>Worker: Last Page = 5
        Worker->>Selenium: Connect & Navigate
        loop Until Last Page
            Selenium->>Selenium: Scrape Current Page
            Selenium-->>Worker: Return Data
            Worker->>Storage: Save Chunk (cat_1_page_6.pkl)
            Worker->>Storage: Update Progress
        end
    and Thread 2
        Orchestrator->>Worker: scrap_unit_category(cat=2)
    and Thread 3
        Orchestrator->>Worker: scrap_unit_category(cat=3)
    and Thread 4
        Orchestrator->>Worker: scrap_unit_category(cat=4)
    end
    
    Worker-->>Orchestrator: All Complete
    Orchestrator->>Storage: join_chunks()
    Storage->>Storage: Consolidate to catalog.pkl
    Orchestrator-->>CLI: Success
```

### Key Features

1. **Resumability**: Progress is tracked per-category in `scrap_progress.csv`
2. **Fault Tolerance**: Each category runs in isolation; failure doesn't crash others
3. **Checkpointing**: Every page is saved as a chunk (`category_id_page_num.pkl`)
4. **Deduplication**: Final consolidation removes duplicates by `expediente` field
5. **Validation**: Compares local catalog against remote metadata for consistency

---

## Orchestration Strategy

### Dual Execution Model

The project supports two execution paradigms:

```mermaid
flowchart TD
    A[Execution Entry Point] --> B{Mode?}
    
    B -->|CLI| C[Typer CLI]
    B -->|Orchestrated| D[Dagster]
    
    C --> E[Direct Python Module]
    E --> F[drugslm.scraper.anvisa.catalog]
    F --> G[Standalone Execution]
    
    D --> H[Dagster Asset]
    H --> I[dagster.scraper.anvisa.pipelines]
    I --> J[Managed Execution]
    J --> K[Dependency Graph]
    K --> L[Lineage Tracking]
    
    style C fill:#ffc107
    style D fill:#0d6efd
```

#### 1. CLI Mode (Typer)

**Use Case**: Development, testing, ad-hoc execution

```bash
# Standalone execution
uv run python -m drugslm.scraper.anvisa.catalog run --threads 4
```

**Advantages**:
- Fast iteration during development
- Direct control over parameters
- No orchestrator dependency
- Ideal for debugging

#### 2. Dagster Mode (Planned)

**Use Case**: Production pipelines, dependency management, monitoring

```python
# dagster/scraper/anvisa/pipelines.py (planned structure)
from dagster import asset, AssetExecutionContext
from drugslm.scraper.anvisa.catalog import scrap_categories

@asset
def anvisa_catalog(context: AssetExecutionContext) -> pd.DataFrame:
    """Scrapes ANVISA drug catalog with full metadata."""
    scrap_categories(n_threads=4, force=False)
    return get_catalog()

@asset(deps=[anvisa_catalog])
def anvisa_leaflets(context: AssetExecutionContext):
    """Downloads PDFs for all cataloged drugs."""
    # Implementation pending
    pass
```

**Advantages**:
- Automatic dependency resolution
- Built-in retry and alerting
- Data lineage visualization
- Centralized logging

---

## Storage Layer

### File-Based Storage (Current)

```
data/
├── raw/anvisa/index/
│   ├── metadata.csv              # Category stats (fetched from ANVISA)
│   ├── scrap_progress.csv        # Execution checkpoints
│   ├── catalog.pkl               # Consolidated drug catalog
│   ├── catalog.csv               # Human-readable export
│   └── chunks/
│       ├── 1_1.pkl              # Category 1, Page 1
│       ├── 1_2.pkl              # Category 1, Page 2
│       └── ...
```

**Rationale**:
- Pickle for fast I/O with pandas DataFrames
- CSV for human inspection and interoperability
- Chunked storage enables resumability

### Future: Hybrid Storage

```mermaid
flowchart LR
    A[Scrapers] --> B{Data Type}
    
    B -->|Metadata| C[(PostgreSQL)]
    B -->|Documents| D[File System]
    B -->|Vectors| E[(Chroma/Qdrant)]
    B -->|Graph| F[(Neo4j)]
    
    C --> G[Structured Queries]
    D --> H[Blob Storage]
    E --> I[Semantic Search]
    F --> J[Relationship Queries]
```

---

## Execution Modes

### Development Container

```mermaid
flowchart TB
    HOST[Host Machine] -->|Docker Compose| CONT[drugslm Container]
    
    CONT --> UV[UV Package Manager]
    UV --> VENV[.venv/]
    VENV --> CODE[drugslm/]
    
    CONT --> HUB[Selenium Hub<br/>External]
    HUB --> FIREFOX[Firefox Node]
    
    CONT --> PORT1[":8000 MkDocs"]
    CONT --> PORT2[":3000 Dagster"]
    
    style CONT fill:#0d6efd
```

**Key Features**:
- Unified `Dockerfile` with dev/prod stages
- Entrypoint script with file locking for parallel containers
- Auto-activation of venv in `.bashrc`
- Mounted volumes for hot-reload

### Makefile Shortcuts

The `Makefile` provides a unified interface for all common tasks:

```makefile
# Environment
make install      # Install uv toolchain
make dev          # Setup full dev environment
make clean        # Remove Python artifacts

# Services
make dagster up   # Start Dagster (localhost:3000)
make docs up      # Start MkDocs with live reload (localhost:8000)

# Code Quality
make lint         # Ruff check
make format       # Auto-format
make test         # Pytest
```

---

## Design Decisions

### 1. Why UV Instead of Poetry/PDM?

- **Speed**: 10-100x faster dependency resolution
- **PEP 723**: Native support for inline script metadata
- **Zero Config**: Works out-of-box without `pyproject.toml` modifications
- **Lockfile**: `uv.lock` is portable and deterministic

### 2. Why Pickle for Intermediate Storage?

- **Performance**: Faster serialization than JSON/CSV for pandas DataFrames
- **Type Preservation**: Maintains dtypes without schema definitions
- **Simplicity**: No database setup needed for MVP phase
- **Trade-off**: Not human-readable (CSV exports provided for inspection)

### 3. Why ThreadPoolExecutor Instead of Multiprocessing?

- **GIL Release**: Selenium I/O operations release the GIL
- **Simplicity**: Shared memory for progress tracking
- **Resource Efficiency**: Lower overhead than process spawning
- **Sufficient**: Network I/O is the bottleneck, not CPU

### 4. Why Separate `drugslm/` and `dagster/` Directories?

- **Separation of Concerns**: Core logic independent of orchestrator
- **Testability**: Unit test modules without Dagster dependency
- **Flexibility**: CLI execution doesn't require Dagster installation
- **Clarity**: Clear distinction between "what" (drugslm) and "how" (dagster)

### 5. Why Remote Selenium Hub?

- **Parallelism**: Multiple browser instances across workers
- **Resource Isolation**: Browsers run on dedicated infrastructure
- **Flexibility**: Easy to scale horizontally
- **Development**: Local debugging with Docker Selenium

### 6. Why MkDocs Instead of Sphinx?

- **Markdown Native**: Easier for non-Python contributors
- **Material Theme**: Professional appearance out-of-box
- **Live Reload**: Faster iteration during writing
- **Integration**: Built-in API doc generation with `mkdocstrings`

---

## Future Enhancements

### Planned Improvements

1. **Database Integration**
   - PostgreSQL for structured metadata
   - Neo4j for drug-drug interactions graph

2. **Distributed Execution**
   - Dagster cloud deployment
   - Ray for distributed training

3. **Monitoring**
   - Prometheus metrics
   - Grafana dashboards
   - Error tracking (Sentry)

4. **Data Quality**
   - Great Expectations for validation
   - DVC for data versioning

---

**Next**: See [Infrastructure](infrastructure.md) for deployment and hardware specifications.