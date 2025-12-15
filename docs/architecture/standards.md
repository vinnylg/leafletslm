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
    DB@{ shape: disk, label: "Database Storage" }

    IModel@{ shape: stored-data, label: "Model Weigths" }

    API{{API / External Data}}
    Params@{ shape: flag, label: "Hyperparams / Configs" }
    Reports@{ shape: docs, label: "Human-Readable Reports" }

    ManualEntry@{ shape: doc, label: "Manual / Expert Data" }
    Results@{ shape: processes, label: "Experiment Results" }
    UserData@{ shape: manual-input, label: "User Data & Feedback" }

    TTV@{ shape: win-pane, label: "Train-Test-Valitation" }
    Thesis@{ shape: odd, label: "Thesis Section" }
    UML@{ shape: delay, label: "Another UML Diagram" }

    Data ~~~ Raw ~~~ Interim
    Processed ~~~ DB ~~~ IModel
    API ~~~ Params ~~~ Reports
    ManualEntry  ~~~  Results ~~~ UserData
    TTV ~~~ UML ~~~ Thesis

```

### Table of Data Artifact Taxonomy

| Shape Name & Usual Meaning | Mermaid Syntax | Project Meaning |
| :--- | :---: | :--- |
| **Rounded Rectangle**</br>Event | `id(Text)`</br>`rounded` | **Generic Data**</br>Auxiliar, generic, or unclassified data. |
| **Rectangle**</br>Process | `id[Text]`</br>`rect` | **Raw / Bronze**</br>Immutable raw source files (PDFs, HTML dumps). |
| **Lined Rectangle**</br>Lined/Shaded Process | `lin-rect` | **Intermediate / Silver**</br>Intermediate, transient, or in-memory data (e.g., extracted JSON). |
| **Framed Rectangle**</br>Subprocess | `id[[Text]]`</br>`subproc` | **Processed / Gold**</br>Processed, structured, and consolidated corpus. |
| **Cylinder**</br>Database | `id[(Text)]`</br>`disk` | **Database Storage**</br>Indexed Databases (Vector DB, Graph DB). |
| **Bow Tie Rectangle**</br>Stored Data | `stored-data` | **Model Weigths:**</br>Base models/weights downloaded (e.g., Llama 3.1 Base). |
| **Hexagon**</br>Prepare Conditional | `id{{Text}}`</br>`hex` | **API/External Data**</br>External services or data sources accessed via network (e.g., Oracle). |
| **Flag**</br>Paper Tape | `flag` | **Hyperparams / Configs**</br>Configuration files, hyperparameters, single text assets. |
| **Stacked Document**</br>Multi-Document | `docs` | **Human-Readable Reports**</br>Human-readable documents (PDF, Markdown, Latex) generated from experiments. |
| **Document**</br>Document | `doc` | **Manual / Expert Data**</br>Hand-crafted data, expert QA pairs, or manually inserted datasets (Ground Truth). |
| **Stacked Rectangle**</br>Multi-Process | `processes` | **Experiment Results**</br>Raw internal data, metrics, logs, and experiment states (source for reports). |
| **Sloped Rectangle**</br>Manual Input | `manual-input` | **User Data & Feedback**</br>Logs, chat history, feedback, and personal info provided by users. |
| **Window Pane**</br>Internal Storage | `win-pane` | **Train-Test-Valitation**</br>Train, Validation, and Test splits for each type of dataset (QA, Ground-True,etc). |
| **Half-Rounded Rectangle**</br>Delay | `delay` | **Another UML Diagram**</br>Reference to another UML Diagram or Documentation Section. |
| **Asymmetric Shape**</br>Odd | `id>Text]`</br>`odd` | **Thesis Section**</br>The Section of Thesis generated based on these experiments. |

---

> Note: To use custom shapes the New Syntax is `Node@{ shape: shape-name, label: "Text"}`

## Process Artifact Taxonomy

During the creation of this document, it was noticed that not everything is easily understandable using a data-driven approach. Therefore, this taxonomy defines **process artifacts**: the execution units, orchestration boundaries, and transformation logic used across pipelines. These shapes **represent executing components** (functions, subsystems, auxiliary processes, and external/parallel flows). They do not represent data state.

```mermaid
flowchart LR

    Mod@{ shape: div-rect, label: "Package/Module" }
    Fun([Function])
    If{Filter}
    IHC@{ shape: curv-trap, label: "Interface"}

    Merge((Merge))
    Join(((Join)))
    Human[\Human Task/]
    AI[/AI Task\]

    Mod ~~~ Fun ~~~ IHC ~~~ Human
    If ~~~ Merge ~~~ Join ~~~ AI 

```

### Table of Process Artifact Taxonomy

| Shape Name & Usual Meaning | Mermaid Syntax | Project Meaning |
| :--- | :---: | :--- |
| **Divided Rectangle**</br>Divided Process | `div-rect` | **Package/Module**</br>A self-contained code package (e.g., `drugslm.sources`, `drugslm.sources.anvisa`) or module (e.g., `drugslm.sources.anvisa.catalog`). Redirect to respective reference page. |
| **Stadium**</br>Terminal Point | `id([Text])`</br>`stadium` | **Function**</br>A specific logic block, class, or script that is crucial for understanding the flow. |
| **Curved Trapezoid**</br>Display | `curv-trap` | **Interface**</br>Refers to any UI/UX compoment used or created. |
| **Trapezoid Top**</br>Manual Operation | `id[\Text/]`</br>`manual` | **Human Task**</br>Manual annotation, expert validation, creation of protocols, or ground truth sampling. |
| **Diamond**</br>Decision | `id{Text}`</br>`diamond` | **Filter**</br>Conditional branching OR a "Many-to-One" filter (e.g., discarding invalid data). |
| **Circle**</br>Start | `id((Text))`</br>`circle` | **Merge**</br>Implies combining several files or tables that have the same structure. |
| **Double Circle**</br>Stop | `id(((T)))`</br>`double-circle` | **Join**</br>The sophisticated unification of structured data streams with different structures. |
| **Trapezoid Bottom**</br>Priority Action | `id[/Text\]`</br>`priority` | **AI Task**</br>Automated intelligent processing (e.g., LLM-based labeling, synthetic data generation). |

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

---

> Note: To use custom shapes the New Syntax is `Node@{ shape: shape-name, label: "Text"}`

### Table of Status Lifecycle

---

| Class | Style Preview | Meaning |
| :--- | :--- | :--- |
| `:::done` | Green (Solid) | **Done**</br>Completed artifacts or processes. |
| `:::active`| Yellow (Bold) | **Active**</br>Currently work-in-progress. |
| `:::must` | Pink (Solid) | **Must**</br>Mandatory milestones. High priority. |
| `:::todo` | Blue (Dashed) | **Todo**</br>Planned future tasks (Backlog). |
| `:::dropped`| **Gray (Faded)**| **Aborted**</br>Features or paths that were discarded or de-prioritized. |

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
| `A ===> B` | **Thick Solid** | **Critical Path (MVP)**</br>The core pipeline. Essential steps for thesis completion ("Rice and Beans"). |
| `A --> B` | **Solid Arrow** | **Standard Flow**</br>Normal data transformation flow or sub-steps within a major process. |
| `A -.-> B` | **Dotted Arrow** | **Experimental/Optional**</br>Secondary paths, "Nice-to-have" features, or exploratory branches ("The Dessert"). |
| `A --- B` | **Solid Line** | **Context/Read-Only**</br>Static dependency. Data is accessed/read but not consumed/transformed (e.g., Configs). |
| `A <--> B` | **Double Arrow** | **Feedback Loop**</br>Iterative process, optimization cycles, or bidirectional data exchange. |

---

> **What is next?:** See how this standards are used acessing [Data Roadmap](roadmap/index.md).
