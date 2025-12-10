# Architecture

This document describes the technical architecture, design decisions, and data flows of the DrugsLM project.

```

flowchart TD

    %% --- ESTILOS ---
    classDef done fill:#a8d5ba,stroke:#6da382,stroke-width:2px,color:#212529;
    classDef active fill:#ffe6a7,stroke:#c9a655,stroke-width:3px,color:#212529;
    classDef must fill:#f4b6c2,stroke:#c07c88,stroke-width:2px,color:#212529;
    classDef could fill:#add8e6,stroke:#7daab6,stroke-width:1px,stroke-dasharray: 5 5,color:#212529;
    classDef drop fill:#e9ecef,stroke:#b0b0b0,stroke-width:1px,stroke-dasharray: 2 2,color:#6c757d;
    classDef hidden fill:none,stroke:none,color:none,width:0px,height:0px;

    %% --- FASE 1: INGESTÃO E PARSING ---
    subgraph Pipeline [Data Acquisition & Parsing]
        direction TB
        sep1[ ]:::hidden

        %% Fontes
        AnvisaPDF[Package Inserts PDF]:::must
        WikiPage[Wiki Articles HTML]:::could
        
        %% Parsers Unificados (Extração + Limpeza + Padronização)
        AParser[ANVISA Parser]:::must
        WParser[Wiki Parser]:::could

        %% O Corpus Bruto
        SSC[SSC: Simple Structured Corpus]:::must

        %% Conexões
        sep1 ~~~ AnvisaPDF
        AnvisaPDF ==> AParser ==> SSC
        WikiPage -.-> WParser -.-> SSC
    end

    %% --- FASE 2: REFINAMENTO E ESTRUTURAÇÃO (Smart Dedup) ---
    subgraph Refinement [Semantic Refinement & Structure]
        direction TB
        sep2[ ]:::hidden

        %% Inteligência sobre o dado
        NER[NER: Entity Extraction]:::must
        EntRes[Entity Resolution<br/>(Smart Deduplication)]:::must
        
        %% O Corpus Refinado (Sem duplicatas, com metadados)
        CleanCorpus[Refined Corpus]:::must
        
        %% Geração de Dados de Treino/Teste
        QAGen[Synthetic Q&A Generation<br/>(Train/Val Sets)]:::must

        %% Estruturação para Bancos
        RelExt[Relation Extraction]:::could
        Embed[Embedding Model]:::must

        %% Conexões
        sep2 ~~~ NER
        SSC ==> NER ==> EntRes ==> CleanCorpus
        EntRes ==> RelExt
        CleanCorpus ==> Embed
        CleanCorpus -.-> QAGen
    end

    %% --- FASE 3: ARMAZENAMENTO ---
    subgraph Storage [Persistent Storage]
        direction TB
        sep3[ ]:::hidden

        VDB[(Vector Database)]:::must
        GDB[(Knowledge Graph)]:::could
        EvalSet[(Q&A Dataset)]:::must

        %% Conexões
        sep3 ~~~ VDB
        Embed ==> VDB
        RelExt -.-> GDB
        QAGen -.-> EvalSet
    end

    %% --- FASE 4: MODELAGEM E INFERÊNCIA ---
    subgraph Modeling [Modeling Strategies Comparison]
        direction TB
        sep4[ ]:::hidden
        
        UserQuery[User Query]:::active

        %% Modelo 1: Apenas Pesos (Fine-Tuning)
        ModelA[DrugsLM - Standalone<br/>(Fine-Tuned Knowledge)]:::must
        
        %% Modelo 2: RAG Clássico
        ModelB[DrugsLM + RAG<br/>(Vector Retrieval)]:::must
        
        %% Modelo 3: Graph RAG
        ModelC[DrugsLM + GraphRAG<br/>(Relational Retrieval)]:::could

        %% Conexões de Inferência
        sep4 ~~~ UserQuery
        
        %% Caminho A
        UserQuery --> ModelA
        CleanCorpus -.-> ModelA

        %% Caminho B
        UserQuery --> VDB --> ModelB

        %% Caminho C
        UserQuery --> GDB --> ModelC
    end

```