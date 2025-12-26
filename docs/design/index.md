# Design Reference

<!-- TODO(!documentation): Complete design documentation structure
     Mirror the API Reference structure with visual diagrams and workflows.
     Each module should have corresponding design docs explaining the "why".
     labels: documentation -->

This section contains the **visual and logical design documentation** for DrugSLM. While the [API Reference](../reference/index.md) documents *what* the code does, the Design Reference explains *how* and *why* systems are structured.

## 📐 Purpose

Design documentation serves to:

- **Visualize workflows** through sequence diagrams and flowcharts
- **Document decisions** and architectural trade-offs
- **Guide implementation** before writing code
- **Facilitate onboarding** for new contributors

## 📂 Modules

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin: 2rem 0;">

  <div style="border: 1px solid #ddd; border-radius: 8px; padding: 1.5rem;">
    <h3>📊 Datasets</h3>
    <p>Data acquisition, transformation, and feature engineering workflows.</p>
    <a href="datasets/"><strong>View Datasets Design →</strong></a>
  </div>

  <div style="border: 1px solid #ddd; border-radius: 8px; padding: 1.5rem;">
    <h3>🧠 Models</h3>
    <p>Architecture definitions, adapter strategies, and RAG integration.</p>
    <em>Coming soon</em>
  </div>

  <div style="border: 1px solid #ddd; border-radius: 8px; padding: 1.5rem;">
    <h3>⚡ Training</h3>
    <p>Training loops, objectives, and optimization workflows.</p>
    <em>Coming soon</em>
  </div>

  <div style="border: 1px solid #ddd; border-radius: 8px; padding: 1.5rem;">
    <h3>📈 Evaluation</h3>
    <p>Metrics calculation and benchmark execution flows.</p>
    <em>Coming soon</em>
  </div>

  <div style="border: 1px solid #ddd; border-radius: 8px; padding: 1.5rem;">
    <h3>🖥️ Interface</h3>
    <p>Chat UI, telemetry collection, and deployment pipelines.</p>
    <em>Coming soon</em>
  </div>

  <div style="border: 1px solid #ddd; border-radius: 8px; padding: 1.5rem;">
    <h3>🧪 Experiments</h3>
    <p>Tracking, visualization, and reporting workflows.</p>
    <em>Coming soon</em>
  </div>

</div>

---

> **Diagram Standards:** All diagrams follow the conventions defined in [Architecture Standards](../architecture/standards.md).
