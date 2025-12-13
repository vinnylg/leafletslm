# Phase 1 Internals Diagrams Detailed

To prevent Overview from becoming polluted, data and processes were grouped into modules. Here are the modules related to Phase 1 — Data Acquisition and Preparation (ETL).

> **Note:** If you are looking for completed roadmap, please refer to the [Experimental Assets Lineage](index.md).

## PDF Extraction Diagram

```mermaid
flowchart TD

    PDF[PDF Files]
    Layout[\LayoutLM/] -.- DLN{{DocLayNet}}
    EPDF[Structred PDF Files]

    PDF ~~~ DLN  ~~~ PExt

    PExt>Raw Extraction]
    PNorm>Primary Normalization]
    PCorr>Structural Cleanup]
    PRep>Repair]
    POut@{ shape: lin-rect, label: "Data With Syntax Repaired" }

    PDF -.-> Layout -.-> EPDF -.-> PExt
    PDF ==> PExt --> PNorm --> PCorr --> PRep --> POut

```

## HTML Extraction Diagram

```mermaid
flowchart TD

    HTML[HTML Files]
    DOM[/Layout DOM\] -.- DLD{{DOMLayoutData}}
    EHTML[Structred HTML Files]

    HTML ~~~ DLD  ~~~ HExt

    HExt>Raw Extraction]
    HNorm>Primary Normalization]
    HCorr>Structural Cleanup]
    HRep>Repair]
    HOut@{ shape: lin-rect, label: "Data With Syntax Repaired" }

    HTML -.-> DOM -.-> EHTML -.-> HExt
    HTML ==> HExt --> HNorm --> HCorr --> HRep --> HOut

```



## Semantic Model Diagram

```mermaid
flowchart TD
    
    Interm@{ shape: lin-rect, label: "Data With Syntax Repaired" }

    Segm([Semantic Segmentation])
    Conv([Intermediate Conversion])

    Interm --> Segm --> Conv

```

## Check Data Diagram

## Cross-Source Merge Diagram

## Corpus Integrity Validation Diagram