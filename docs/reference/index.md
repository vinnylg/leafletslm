# API Reference - Overview

Welcome to the technical reference for the `drugslm` package. This documentation is organized logically to reflect the scientific workflow of the project, ranging from data acquisition to model deployment and experimental analysis.

Below is an overview of the high-level modules and their responsibilities.

---

## [Datasets](datasets/index.md)
**1. The Raw Material**

This module handles the data lifecycle. Unlike traditional ETL pipelines, the focus here is on the dataset as a scientific object of study—ensuring quality, lineage, and readiness for language modeling.

- **Sources**: Connectors and scrapers for external data ingestion (e.g., ANVISA).
- **Transform**: Pipelines for cleaning, normalization, augmentation, and tokenization logic.
- **Features**: Definitions of extracted attributes, embedding manipulations, and metadata engineering.
- **Loaders**: Efficient data loading strategies and iterators (e.g., PyTorch DataLoaders).

## 2. Models
**The Engine**

Contains the static architectural definitions and design strategies. This module defines *what- the model is before it begins learning.

- **Definitions**: Base classes and wrappers for Large Language Models (e.g., Llama, BERT).
- **Adapters**: Configuration for parameter-efficient adaptation strategies (PEFT, LoRA).
- **RAG**: Components for Retrieval-Augmented Generation systems.

## 3. Training
**The Process**

Encapsulates the dynamic optimization logic. This module defines *how- the model learns and adapts to the data.

- **Loops**: The training execution cycles (Pre-training, SFT).
- **Objectives**: Mathematical loss functions and optimization goals.
- **RLHF**: Implementation of Reinforcement Learning from Human Feedback loops.

## 4. Evaluation
**The Verification**

Focuses on rigorous quantitative validation to ensure model quality and safety.

- **Metrics**: Calculation of statistical performance (Accuracy, F1, Perplexity).
- **Benchmarks**: Standardized test suites, safety checks, and domain-specific challenges.

## 5. Interface
**The Application**

The human-facing component used for qualitative analysis, model serving, and feedback collection (Human-in-the-loop).

- **Chat**: UI logic and interaction handling (e.g., Chainlit integration).
- **Telemetry**: Capture of user feedback (thumbs up/down) and interaction logs.
- **Deploy**: Utilities for model serving and containerization.

## 6. Experiments
**The Conclusion**

Responsible for traceability, storytelling, and the consolidation of results. This module connects inputs (params) to outputs (metrics).

- **Tracking**: Wrappers for experiment trackers (e.g., MLFlow).
- **Visualization**: Generation of plots and visual artifacts for the thesis.
- **Storytelling**: Automated generation of reports summarizing experimental findings.

## 7. Core
**The Foundation**

The infrastructure layer containing agnostic utilities and shared services required by the modules above.

- **Config**: Configuration tree management (Hydra/OmegaConf).
- **Database**: Database connections and ORM definitions.
- **Utils**: Low-level helpers (Selenium drivers, logging, string manipulation).