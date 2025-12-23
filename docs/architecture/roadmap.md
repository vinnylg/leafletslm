# Experimental Process Roadmap

The diagram below illustrates the complete data acquisition and processing roadmap for this project, organized as a data-centric asset chart, showing progress across all assets. Each node also has a link to the main module responsible for acquiring the respective data, whether completed or in progress.

## 1 Data Acquisition and Preparation

This phase establishes the empirical foundation of the entire system. Data must be **collected**, **curated**, **cleaned**, **filtered**, **normalized**, and **structured** to support the intended behavior of the model. For large language models, this includes **deduplication**, **domain balancing**, **safety filtering**, and the creation of well-defined **training**, **validation**, and **test splits**. The quality and representativeness of the data directly determine the reliability and limits of the downstream model.

## 2 Modeling and System Design

With the data prepared, the next step is to design the computational solution. In the context of LLMs, this may involve selecting an existing **pretrained model** or defining an architecture to be trained from scratch. It also includes choosing the adaptation strategy: **retrieval-augmented generation (RAG)**, **parameter-efficient fine-tuning (PEFT/LoRA)**, **full fine-tuning**, or **reinforcement learning from human feedback (RLHF/RLAIF)**. The decisions made here define both the model’s capabilities and its operational constraints.

## 3 Training and Optimization

During training, model parameters are optimized to approximate the target function. For LLMs, this encompasses **pre-training**, **supervised fine-tuning (SFT)**, and iterative post-training methods such as **RLHF** or **RLAIF**. Optimization involves careful selection of **learning rates**, **batch sizes**, **loss functions**, and **regularization strategies**. Stability, convergence, and computational efficiency are central concerns at this stage.

## 4 Evaluation and Validation

The model must be evaluated rigorously across quantitative and qualitative dimensions. In traditional ML, this involves metrics such as **accuracy**, **F1 score**, or **perplexity**. For LLMs, the evaluation expands to include **reasoning benchmarks**, **domain-specific test suites**, **human preference assessments**, and **safety analyses**. Robust validation ensures the model not only performs well on held-out data but also behaves consistently and safely in real-world scenarios.

## 5 Optimization and Knowledge Augmentation

This phase focuses on the technical refinement of the **Small Language Model (SLM)** to ensure pharmacological safety and computational efficiency under hardware constraints. Optimization involves applying **quantization** and distillation techniques to reduce the computational footprint without compromising informational fidelity. The core of this stage is **Knowledge Augmentation (KA)**, where the model is integrated with a **Knowledge Graph** to ground responses in official sources, mitigating hallucinations. The objective is to validate how the synergy between neural weights and symbolic structures enables a reduced-parameter model to maintain the diagnostic and informative integrity required in the healthcare domain.

## 6 Qualitative Assessment and Reporting

The final phase closes the research cycle through qualitative validation and the consolidation of experimental results. Instead of large-scale production monitoring, the focus shifts to **expert assessment** and collecting qualified feedback to verify the thesis hypotheses. This stage involves the statistical synthesis of collected metrics, comparative analysis between the different tested architectures, and documentation of observed limitations. The data generated here directly informs the writing of the conclusion, transforming interaction logs and benchmark results into scientific evidence that supports the feasibility of using SLMs in the pharmaceutical domain.

---

## 🛡️ Critical Research & Design Reflections

### 1. SLM & Knowledge Graph Synergy (Phase 5)
The integration of a **Small Language Model (SLM)** with a **Knowledge Graph (KG)** via **Graph-Augmented Generation (GAG)** presents a significant technical bottleneck. 
* **Context Constraints**: SLMs have limited attention windows; injecting large sub-graphs or complex triplets may lead to context saturation or loss of reasoning capabilities.
* **Grounding Priority**: Establishing a hierarchy where the model prioritizes KG-derived facts over its internal weights (parametric memory) is essential to eliminate pharmaceutical hallucinations.

### 2. Optimization Strategy: RLHF vs. DPO (Phase 3)
While the current architecture mentions **Reinforcement Learning from Human Feedback (RLHF)**, the practical constraints of a Master’s thesis suggest a pivot.
* **Resource Efficiency**: RLHF requires training a separate reward model and extensive human-labeled preference data. 
* **Alternative**: **Direct Preference Optimization (DPO)** is recommended as it achieves similar alignment with lower computational overhead and a more streamlined pipeline for SLMs.

### 3. Data Integrity in PDF Extraction (Phase 1)
The project's empirical foundation relies on **ANVISA PDF** package inserts.
* **Extraction Noise**: PDFs often contain complex layouts (tables, multi-columns) that, if incorrectly parsed, will propagate errors into the **Simple Structured Corpus** and the **Knowledge Graph**.
* **Mitigation**: A rigorous schema validation layer in the `Datasets` module is required to ensure data lineage remains untainted before training.

### 4. Quantifying "Simplicity" (Phases 4 & 6)
One of the project's core visions is democratizing complex pharmacological information. Standard metrics like Perplexity or F1 are insufficient for this purpose.
* **Readability Framework**: Implementation of the **Flesch Reading Ease (FRE)** index, adapted for the target language, to provide a mathematical proxy for accessibility.
  $$FRE = 206.835 - 1.015 \left( \frac{\text{total words}}{\text{total sentences}} \right) - 84.6 \left( \frac{\text{total syllables}}{\text{total words}} \right)$$
* **Semantic Preservation**: Using **BERTScore** to ensure that simplification does not result in the loss of critical pharmacological nuances or instructions.
* **Human-in-the-loop Validation**: Phase 6 must incorporate a qualitative protocol (e.g., Likert scales) to measure **Understandability** and **Actionability** with lay users, complementing the expert pharmaceutical validation.

### 5. Architectural Decoupling (Phase 7)
The `Core` module currently bundles low-level utilities like Selenium drivers with high-level logging.
* **Maintenance Risk**: Changes in external pharmacological portals (ANVISA) could lead to breaking changes in the core infrastructure.
* **Best Practice**: Scraping logic should be isolated from shared services to ensure that model training and evaluation remain decoupled from data acquisition instabilities.
