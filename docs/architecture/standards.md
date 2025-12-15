# MermaidJS Flowchart Modeling Standards

The definitions below outline the semantic rules for interaction flows, execution states, and data artifact taxonomy used throughout this documentation.

## Data Artifact Taxonomy

Given the attempt at a data-centric nature of this research, distinguishing between data types and their maturity levels is crucial. We employ a specific shape taxonomy to categorize artifacts, following a modified "Medallion Architecture" (Bronze, Silver, Gold) adapted for LLM pipelines. This taxonomy visually separates raw inputs, intermediate in-memory structures, consolidated corpora, persistent storage, and model weights (both internal and external), ensuring that the state of any data asset is instantly recognizable.

```mermaid
flowchart LR

    Data(Generic Data)
    Raw[Raw / Bronze]
    Interim@{ shape: lin-rect, label: "Intermediate / Silver" }

    Processed[[Processed / Gold]]

    DB[(Database)]
    DB@{ shape: disk, label: "Disk storage" }

    IModel@{ shape: stored-data, label: "IA Model Storage" }

    API{{API / External Data}}
    Params@{ shape: flag, label: "Hyperparams / Config" }
    Reports@{ shape: docs, label: "Human-Readable Reports" }

    ManualEntry@{ shape: doc, label: "Manual / Expert Data" }
    Metrics@{ shape: processes, label: "Raw Experiment Metrics" }
    UserData@{ shape: manual-input, label: "User Logs & Feedback" }

    TTV@{ shape: win-pane, label: "Train-Test-Valitation Set" }
    Thesis@{ shape: curv-trap, label: "Thesis/External Artefacts" }
    UML@{ shape: odd, label: "UML Diagram" }

    Data ~~~ Raw ~~~ Interim
    Processed ~~~ DB ~~~ IModel
    API ~~~ Params ~~~ Reports
    ManualEntry  ~~~  Metrics ~~~ UserData
    TTV ~~~ UML ~~~ Thesis

```

### Table of Data Artifact Taxonomy

> Note: To use custom shapes the New Syntax is `Node@{ shape: shape-name, label: "Text"}`

---

| Shape Name & Usual Meaning | Mermaid Syntax | Project Meaning |
| :--- | :---: | :--- |
| **Rounded Rectangle**</br>Event | `id(Text)`</br>`rounded` | **Generic Data:** Auxiliar, generic, or unclassified data. |
| **Rectangle**</br>Process | `id[Text]`</br>`rect` | **Bronze:** Immutable raw source files (PDFs, HTML dumps). |
| **Lined Rectangle**</br>Lined/Shaded Process | `lin-rect` | **Silver:** Intermediate, transient, or in-memory data (e.g., extracted JSON). |
| **Framed Rectangle**</br>Subprocess | `id[[Text]]`</br>`subproc` | **Gold:** Processed, structured, and consolidated corpus. |
| **Cylinder**</br>Database | `id[(Text)]`</br>`disk` | **Persistent Store:** Indexed Databases (Vector DB, Graph DB). |
| **Bow Tie Rectangle**</br>Stored Data | `stored-data` | **IA Model Storage:** Base models/weights downloaded (e.g., Llama 3.1 Base). |
| **Hexagon**</br>Prepare Conditional | `id{{Text}}`</br>`hex` | **API/External:** External services or data sources accessed via network (e.g., Oracle). |
| **Flag**</br>Paper Tape | `flag` | **Params:** Configuration files, hyperparameters, single text assets. |
| **Stacked Document**</br>Multi-Document | `docs` | **Reports:** Human-readable documents (PDF, Markdown, Latex) generated from experiments. |
| **Document**</br>Document | `doc` | **Manual Entry:** Hand-crafted data, expert QA pairs, or manually inserted datasets (Ground Truth). |
| **Stacked Rectangle**</br>Multi-Process | `processes` | **Metrics:** Raw internal data, metrics, logs, and experiment states (source for reports). |
| **Sloped Rectangle**</br>Manual Input | `manual-input` | **User Data:** Logs, chat history, feedback, and personal info provided by users. |
| **Window Pane**</br>Internal Storage | `win-pane` | **TTV Set:** Train, Validation, and Test splits. |
| **Asymmetric Shape**</br>Odd | `id>Text]`</br>`odd` | **Link/Ref:** Reference to another UML Diagram or Documentation Section. |
| **Curved Trapezoid**</br>Display | `curv-trap` | **External Artefact:** The document generated based on the general roadmap/flowchart. |

## Process Artifact Taxonomy

During the creation of this document, it was noticed that not everything is easily understandable using a data-driven approach. Therefore, this taxonomy defines **process artifacts**: the execution units, orchestration boundaries, and transformation logic used across pipelines. These shapes **represent executing components** (functions, subsystems, auxiliary processes, and external/parallel flows). They do not represent data state.

```mermaid
flowchart LR

    Mod@{ shape: div-rect, label: "Package != Module" }
    Fun([Function / Method])
    If{Filter / Logic}
    Join((Merge / Join))
    End(((CI/CD)))

    Human[\Human Task/]
    AI[/AI Agent\]
    Note@{ shape: braces, label: "Comment / Note" }

    Mod ~~~ Fun ~~~ If ~~~ Join 
    End ~~~ Human ~~~ AI ~~~ Note

```

### Table of Process Artifact Taxonomy

> Note: To use custom shapes the New Syntax is `Node@{ shape: shape-name, label: "Text"}`

---

| Shape Name & Usual Meaning | Mermaid Syntax | Project Meaning |
| :--- | :---: | :--- |
| **Divided Rectangle**</br>Divided Process | `div-rect` | **Module:** A self-contained code package (e.g., `drugslm.scraper`). Represents a "Black Box" system. |
| **Stadium**</br>Terminal Point | `id([Text])`</br>`stadium` | **Function/Method:** A specific logic block, class, or script that is crucial for understanding the flow. |
| **Diamond**</br>Decision | `id{Text}`</br>`diamond` | **Filter / Logic Gate:** Conditional branching OR a "Many-to-One" filter (e.g., discarding invalid data). |
| **Circle**</br>Start | `id((Text))`</br>`circle` | **Merge / Join:** The sophisticated unification of structured data streams. Not just a mix, but a join. |
| **Double Circle**</br>Stop | `id(((T)))`</br>`double-circle` | **CI/CD:** A stable final state or completion of a major process flow and your continuous integration (CI) and continuous delivery (CD). |
| **Trapezoid Top**</br>Manual Operation | `id[\Text/]`</br>`manual` | **Human Task:** Manual annotation, expert validation, creation of protocols, or ground truth sampling. |
| **Trapezoid Bottom**</br>Priority Action | `id[/Text\]`</br>`priority` | **AI Task:** Automated intelligent processing (e.g., LLM-based labeling, synthetic data generation). |
| **Braces**</br>Comment | `braces` | **Annotation:** Contextual notes, explanations, or "nice-to-know" info attached to nodes. |

## Execution Status Lifecycle

To facilitate project tracking and roadmap visualization, a semantic color palette is applied to diagram nodes based on their current development state. This color-coding allows for an immediate assessment of the project's progress, clearly distinguishing between completed assets, currently active tasks, mandatory milestones, and planned future features (backlog), as well as identifying deprecated or aborted approaches.

```mermaid
flowchart LR

    classDef done fill:#a5eea0,stroke:#5dc460,stroke-width:2px,color:#212529;
    classDef active fill:#ffe6a7,stroke:#c9a655,stroke-width:3px,color:#212529;
    classDef todo fill:#90caf9,stroke:#1565c0,stroke-width:2px,stroke-dasharray: 5 5,color:#000;
    classDef must fill:#f8bbd0,stroke:#c2185b,stroke-width:2px,color:#212529;
    classDef drop fill:#eeeeee,stroke:#bdbdbd,stroke-width:2px,stroke-dasharray: 5 5,color:#9e9e9e;

    
    L1[Done]:::done
    L2[Active]:::active
    L3[Must]:::must
    L4[Todo]:::todo
    L5[Drop]:::drop

    L1 ~~~ L2 ~~~ L3 ~~~ L4 ~~~L5

```

### Table of Status Lifecycle

---

| Class | Style Preview | Meaning |
| :--- | :--- | :--- |
| `:::done` | Green (Solid) | **Done:** Completed artifacts or processes. |
| `:::active`| Yellow (Bold) | **Active:** Currently work-in-progress. |
| `:::must` | Pink (Solid) | **Must:** Mandatory milestones. High priority. |
| `:::todo` | Blue (Dashed) | **Todo:** Planned future tasks (Backlog). |
| `:::dropped`| **Gray (Faded)**| **Aborted:** Features or paths that were discarded or de-prioritized. |

## Interaction Flows & Dependencies

The edges connecting nodes in our diagrams represent the nature of the relationship and the priority of the data flow. We distinguish between the Critical Path (essential steps for the project's Minimum Viable Product), standard data transformations, and optional or experimental branches. Additionally, specific line styles indicate static dependencies (read-only context) and iterative feedback loops, providing a clear map of how data and control propagate through the system.

```mermaid
flowchart 

    Config[Global Config]
    Raw[Raw Data]
    Clean[Data Cleaning]
    Split[Train/Test Split]
    BaseTrain[Baseline Model]
    Tuner[Hyperparam Tuner]
    NewArch[Experimental Model]
    Eval[Evaluation Metrics]
    Report[Final Report]
    Logs[System Logs]

    Config ---|Static Context| Clean

    Raw ==>|Critical Path| Clean ==>|MVP Flow| Split ==>|MVP Flow| BaseTrain ==>|MVP Flow| Eval ==>|MVP Flow| Report

    BaseTrain <-->|Feedback Loop| Tuner

    Split -.->|Optional Branch| NewArch -.->|Experimental Flow| Eval

    Eval -->|Standard Flow| Logs

    ModelConfig[Model Configs]

    BaseTrain ---|Static Context| ModelConfig ---|Static Context| NewArch
```

### Table of Paths and Flows

---

| Syntax | Line Style | Project Meaning |
| :--- | :--- | :--- |
| `A ===> B` | **Thick Solid** | **Critical Path (MVP):** The core pipeline. Essential steps for thesis completion ("Rice and Beans"). |
| `A --> B` | **Solid Arrow** | **Standard Flow:** Normal data transformation flow or sub-steps within a major process. |
| `A -.-> B` | **Dotted Arrow** | **Experimental/Optional:** Secondary paths, "Nice-to-have" features, or exploratory branches ("The Dessert"). |
| `A --- B` | **Solid Line** | **Context/Read-Only:** Static dependency. Data is accessed/read but not consumed/transformed (e.g., Configs). |
| `A <--> B` | **Double Arrow** | **Feedback Loop:** Iterative process, optimization cycles, or bidirectional data exchange. |

---

> **What is next?:** See how this standards are used acessing [Data Roadmap](roadmap/index.md).
