# Experimental Assets Lineage ( Data Roadmap )

The diagram below illustrates the complete data acquisition and processing roadmap for this project, organized as a data-centric asset chart, showing progress across all assets. Each node also has a link to the main module responsible for acquiring the respective data, whether completed or in progress.

## Step 1 - Data Acquisition

Abrange desde a Extração, Processamento e Carregamento dos dados em bancos de dados e em formatos que podem ser utilizados nos próximos passos


```mermaid
flowchart TD
    classDef done fill:#a5eea0,stroke:#5dc460,stroke-width:2px,color:#212529;
    classDef active fill:#ffe6a7,stroke:#c9a655,stroke-width:3px,color:#212529;
    classDef todo fill:#e3f2fd,stroke:#90caf9,stroke-width:1px,stroke-dasharray: 5 5,color:#212529;
    classDef must fill:#f8bbd0,stroke:#c2185b,stroke-width:2px,color:#212529;

    AnvisaCat[ANVISA Catalog]:::done
    AnvisaPage[Drug HTML Pages]:::active
    AnvisaPDF[Package Insert PDFs]:::must
    AExt[PDF Text Extraction]:::must
    AProc[ANVISA Processor]:::must

    %% Track Wikipedia
    WikiA[Wiki Categories]:::could
    Wiki[Wiki Categories]:::could
    WikiPage[Wiki Articles]:::could
    WExt[HTML Extraction]:::could
    WProc[Wiki Processor]:::could

    %% Track Drugs.com
    DrugsA[Drugs.com Catalog]:::drop
    Drugs[Drugs.com Catalog]:::drop
    DrugsPage[Drugs.com Pages]:::drop
    DExt[HTML Extraction]:::drop
    DProc[Drugs Processor]:::drop

    %% Convergence Point
    SSC[Simple Structured Corpus]:::must

    %% Fluxos
    AnvisaCat ==> AnvisaPage ==> AnvisaPDF ==> AExt ==> AProc ==> SSC
    WikiA -.-> Wiki -.->WikiPage --> WExt --> WProc --> SSC
    DrugsA -.-> Drugs -.-> DrugsPage -.-> DExt -.-> DProc -.-> SSC

```

---

## Step 2 - Model
## Step 3 - Evaluate





# OLD

```mermaid
flowchart TD

    %% Definição de Estilos
    classDef done fill:#a8d5ba,stroke:#6da382,stroke-width:2px,color:#212529;
    classDef active fill:#ffe6a7,stroke:#c9a655,stroke-width:3px,color:#212529;
    classDef must fill:#f4b6c2,stroke:#c07c88,stroke-width:2px,color:#212529;
    classDef could fill:#add8e6,stroke:#7daab6,stroke-width:1px,stroke-dasharray: 5 5,color:#212529;
    classDef drop fill:#e9ecef,stroke:#b0b0b0,stroke-width:1px,stroke-dasharray: 2 2,color:#6c757d;

    %% Subgrafo Unificado: Ingestão e Processamento
    subgraph Pipeline [Data Ingestion & Processing Pipeline]
        
        %% Track ANVISA
        AnvisaCat[ANVISA Catalog]:::done
        AnvisaPage[Drug HTML Pages]:::active
        AnvisaPDF[Package Insert PDFs]:::must
        AExt[PDF Text Extraction]:::must
        AProc[ANVISA Processor]:::must

        %% Track Wikipedia
        WikiA[Wiki Categories]:::could
        Wiki[Wiki Categories]:::could
        WikiPage[Wiki Articles]:::could
        WExt[HTML Extraction]:::could
        WProc[Wiki Processor]:::could

        %% Track Drugs.com
        DrugsA[Drugs.com Catalog]:::drop
        Drugs[Drugs.com Catalog]:::drop
        DrugsPage[Drugs.com Pages]:::drop
        DExt[HTML Extraction]:::drop
        DProc[Drugs Processor]:::drop

        %% Convergence Point
        SST[SST: Simple Structured Text]:::must

        %% Fluxos
        AnvisaCat ==> AnvisaPage ==> AnvisaPDF ==> AExt ==> AProc ==> SST
        WikiA -.-> Wiki -.->WikiPage --> WExt --> WProc --> SST
        DrugsA -.-> Drugs -.-> DrugsPage -.-> DExt -.-> DProc -.-> SST
    end

    %% Subgrafo: Enriquecimento Semântico (NLP)
    subgraph Enrichment [Knowledge Extraction & Structuring]
        
        %% Caminho Vetorial
        Embed[Embedding Model]:::must
        
        %% Caminho do Grafo
        NER[NER: Entity Extraction]:::must
        EntRes[Entity Resolution]:::must
        RelExt[Relation Extraction]:::could
        KGConst[Knowledge Graph Construction]:::could

        %% Conexões Lógicas
        SST ==> Embed
        SST ==> NER ==> EntRes ==> RelExt ==> KGConst
    end
    
    %% Subgrafo: Armazenamento
    subgraph Storage [Persistent Storage]
        VDB[(Vector Database)]:::must
        GDB[(Graph Database)]:::could

        Embed ==> VDB
        KGConst --> GDB
    end

    click AnvisaCat "reference/scraper/anvisa/catalog/" "See Anvisa Catalog Module"
```





