# DrugSLM - Small Language Model for Drug Information

> **Master's Thesis Project** | Federal University of Paraná (UFPR) | Computer Science Department

DrugSLM is a specialized Small Language Model (SLM) trained on drug package inserts and other pharmacological databases, designed to understand and generate accurate and simple pharmaceutical information.

## 🎓 Academic Context

This project is part of a Master's thesis in Computer Science at the **Federal University of Paraná (UFPR)**, Curitiba, Brazil. The research focuses on:

- Democratizing access to complex pharmacological information
- Structuring unstructured data from official pharmaceutical documentation
- Domain-adaptation of Language Models for pharmacological information
- Resource-efficient fine-tuning strategies for Small Language Models (SLMs)
- Validation and reliability of Generative AI in healthcare contexts

**Researcher**: Vinícius de Lima Gonçalves  
**Advisor**: Professor Eduardo Todt, PhD  
**Institution**: Department of Computer Science, UFPR

## 🎯 Project Vision

High-quality outcomes likely depend on rigorously structured data rather than massive scale, favoring Small Language Models (SLMs). Leveraging Knowledge Graphs aims to provide precise context and granularity. Comparing architectures intends to demonstrate that data structure is key to resource-efficient, reliable pharmacological AI.

## 🧬 Project Lifecycle & Roadmap

The project follows a rigorous 6-phase data-centric methodology, ensuring reproducibility and reliability from data acquisition to model deployment.

```mermaid
flowchart LR

    classDef phase fill:#f0f4f8,stroke:#2c3e50,stroke-width:2px,color:#2c3e50;

    P1(1: Data Acquisition):::phase
    P2(Phase 2:<br/>Modeling):::phase
    P3(Phase 3:<br/>Training):::phase
    P4(Phase 4:<br/>Evaluation):::phase
    P5(Phase 5:<br/>Deployment):::phase
    P6(Phase 6:<br/>Monitoring):::phase

    P1 <==> P2 <==> P3 <==> P4 <==> P5 <==> P6

    click P1 "architecture/roadmap/#data-acquisition-and-preparation-etl" "Go to Phase 1: Acquisition"
    click P2 "architecture/roadmap/#modeling-and-system-design" "Go to Phase 2: Modeling"
    click P3 "architecture/roadmap/#training-and-optimization" "Go to Phase 3: Training"
    click P4 "architecture/roadmap/#evaluation-and-validation" "Go to Phase 4: Evaluation"
    click P5 "architecture/roadmap/#deployment" "Go to Phase 5: Deployment"
    click P6 "architecture/roadmap/#monitoring-and-continuous-improvement" "Go to Phase 6: Monitoring"


```

<p style="text-align: center; color: #5f6368; margin-bottom: 2rem; font-style: italic;">
  Explore the detailed lineage regarding extraction, transformation, training strategies, and validation metrics for each phase by clicking on the nodes below.
</p>

## 🚀 Quick Start

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin: 2rem 0;">
  
  <div style="border: 1px solid #ddd; border-radius: 8px; padding: 1.5rem;">
    <h3>📖 Getting Started</h3>
    <p>Environment setup, container orchestration, and full pipeline reproduction guide.</p>
    <a href="getting-started/">Installation Guide →</a>
  </div>
  
  <div style="border: 1px solid #ddd; border-radius: 8px; padding: 1.5rem;">
    <h3>🏗️ Architecture & Design</h3>
    <p>Visual standards, data lineage roadmaps, and logical system design hub.</p>
    <a href="architecture/">View Design Docs →</a>
  </div>
  
  <div style="border: 1px solid #ddd; border-radius: 8px; padding: 1.5rem;">
    <h3>🛠️ Infrastructure</h3>
    <p>Hardware specifications, GPU constraints, and containerized services setup.</p>
    <a href="architecture/infrastructure/">Hardware & Deployment →</a>
  </div>
  
  <div style="border: 1px solid #ddd; border-radius: 8px; padding: 1.5rem;">
    <h3>📚 API Reference</h3>
    <p>Comprehensive module documentation, pipeline interfaces, and internal tools.</p>
    <a href="reference/">Browse API Docs →</a>
  </div>
</div>

## 🤝 Contributing

This is an active research project. If you're interested in collaborating or have suggestions, feel free to open an issue or reach out.

<!-- ## 📄 License

This project is licensed under the BSD License. See [LICENSE](LICENSE) for details. -->
