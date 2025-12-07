# DrugsLM - Small Language Model for Drug Information

> **Master's Thesis Project** | Federal University of Paraná (UFPR) | Computer Science Department

DrugsLM is a specialized Small Language Model (SLM) trained on drug package inserts and medical databases, designed to understand and generate accurate pharmaceutical information in Portuguese and English.

---

## 🎓 Academic Context

This project is part of a Master's thesis in Computer Science at the **Federal University of Paraná (UFPR)**, Curitiba, Brazil. The research focuses on:

- Domain-specific language model development
- Efficient training strategies for Small Language Models
- Medical information extraction and structuring
- Multilingual pharmaceutical knowledge representation

**Researcher**: Vinícius de Lima Gonçalves  
**Institution**: Department of Computer Science, UFPR

---

## 📋 Project Roadmap

The diagram below illustrates the complete data acquisition and processing roadmap for this project, organized as a data-centric asset graph showing what has been completed, what's in progress, and what's planned.

```mermaid
flowchart TD
    classDef done fill:#198754,stroke:#146c43,stroke-width:2px,color:white;
    classDef active fill:#ffc107,stroke:#ba8b00,stroke-width:4px,color:black;
    classDef mvp fill:#dc3545,stroke:#a71d2a,stroke-width:2px,color:white;
    classDef future fill:#e9ecef,stroke:#ced4da,stroke-width:1px,color:#1e40af;
    classDef dead fill:#e9ecef,stroke:#ced4da,stroke-width:1px,color:#adb5bd;
        
    Begin([Start Data Acquisition]):::done
    
    Catalog[ANVISA Catalog Scraper]:::done
    AnvisaPage[ANVISA Drug Pages]:::active
    PDF[Package Insert PDFs]:::mvp 
    
    WikiAPI[Wikipedia API]:::future
    Wiki[Wikipedia Drug Categories]:::future
    WikiPage[Wikipedia Drug Articles]:::future
    
    Drugs[Drugs.com site Exploration]:::future
    DrugsCat[Drugs.com Catalog Scraper]:::future
    DrugsPage[Drugs.com Drug Pages]:::future
    
    SST[Simple Structured Text]:::mvp
    NER[Named Entity Recognition]:::future
    RST[Related Structured Text]:::future
    GST[Graph Structured Text]:::future
    
    VDB[(Vector Database)]:::mvp
    GDB[(Graph Database)]:::future

    Begin ==> Catalog ==> AnvisaPage ==> PDF ==> SST
    Begin -.-> WikiAPI -.-> Wiki -.-> WikiPage -.-> SST
    Begin -.-> Drugs -.-> DrugsCat -.-> DrugsPage -.-> SST
            
    SST =====> VDB
    SST -.-> NER -.-> RST -.-> GST -.-> GDB
    
    class Drugs dead
    class DrugsCat dead
    class DrugsPage dead

    click Catalog "reference/scraper/anvisa/catalog/" "See Catalog Activity Diagram"
```

**Legend**: 🟢 Complete | 🟡 In Progress | 🔴 MVP Phase | ⚪ Planned | ⚫ Dropped

---

## 🚀 Quick Start

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin: 2rem 0;">
  <div style="border: 1px solid #ddd; border-radius: 8px; padding: 1.5rem;">
    <h3>📖 Getting Started</h3>
    <p>Environment setup, Docker guide, and first scraper execution</p>
    <a href="getting-started/">Installation Guide →</a>
  </div>
  
  <div style="border: 1px solid #ddd; border-radius: 8px; padding: 1.5rem;">
    <h3>🏗️ Architecture</h3>
    <p>Technical decisions, data flows, and design patterns</p>
    <a href="architecture/">System Design →</a>
  </div>
  
  <div style="border: 1px solid #ddd; border-radius: 8px; padding: 1.5rem;">
    <h3>🛠️ Infrastructure</h3>
    <p>Container setup, Selenium Grid, and hardware specs</p>
    <a href="infrastructure/">Deployment Info →</a>
  </div>
  
  <div style="border: 1px solid #ddd; border-radius: 8px; padding: 1.5rem;">
    <h3>📚 API Reference</h3>
    <p>Module documentation, scrapers, and code examples</p>
    <a href="reference/">Browse API Docs →</a>
  </div>
</div>

---

**Next Steps**: [Set up your development environment →](getting-started.md)

<!--
## 🎯 Project Vision

Traditional large language models often struggle with domain-specific medical information, particularly in non-English languages. DrugsLM addresses this by:

- **Specialized Training**: Focused exclusively on pharmaceutical data from regulatory agencies
- **Multilingual Support**: Primary focus on Portuguese (ANVISA) with English expansion (Wikipedia, Drugs.com)
- **Accuracy First**: Built from verified, authoritative sources rather than general web data
- **Efficient Design**: Small Language Model approach for faster inference and lower computational costs

TODO: Refine this section with a more academic tone or move to a different location
-->

## 🤝 Contributing

This is an active research project. If you're interested in collaborating or have suggestions, feel free to open an issue or reach out.

---

## 📄 License

This project is licensed under the BSD License. See [LICENSE](https://github.com/yourusername/drugslm/blob/main/LICENSE) for details.
