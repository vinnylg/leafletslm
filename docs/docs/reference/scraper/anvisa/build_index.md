# Build Index Module

## Index Construction Pipeline

The main script (`build_index.py`) operates following the flow below:

```plantuml
@startuml
!theme vibrant
title Pipeline: Build Drug Index (Anvisa)
autonumber

actor "User" as User
participant "CLI (Typer)" as CLI
participant "Fetch Module" as Fetch
participant "Orchestrator" as Orch
participant "Scraper Core" as Core
database "Filesystem" as FS

User -> CLI: run(threads, only_fetch, skip_fetch)
activate CLI

' === STAGE 1: METADATA ===
group Stage 1: Metadata Fetching
    alt skip_fetch == False
        CLI -> Fetch: execute_fetch()
        activate Fetch
        Fetch -> Fetch: managed_webdriver()

        loop For each Category
            Fetch -> Fetch: fetch_category_page()
            note right: Accesses 1st and Last page\nto estimate volume
        end

        Fetch -> FS: Saves 'fetched_categories.csv'
        Fetch --> CLI: Returns DataFrame
        deactivate Fetch
    else skip_fetch == True
        CLI -> CLI: Log "Skipping Fetch Step"
    end
end

' === STAGE 2: PROCESSING ===
group Stage 2: Data Processing
    alt only_fetch == True
        CLI -> User: Terminates Execution Successfully
    else Proceed to Scraping
        CLI -> Orch: process_categories(n_threads)
        activate Orch
        note right: ThreadPoolExecutor

        loop Parallel (per Category)
            Orch -> Orch: process_category(id)
            activate Orch

            Orch -> FS: Reads 'fetched_categories.csv'

            alt Size == 0 or Not Found
                Orch -> Orch: Skip Category
            else Size > 0
                Orch -> Orch: managed_webdriver()
                Orch -> Core: scrap_pages(driver, id)
                activate Core

                loop While pages exist
                    Core -> Core: find_table()
                    Core -> Core: table2data()

                    alt Valid Data
                        Core -> FS: save_data() [Pickle]
                        Core -> FS: save_category_pages() [CSV Log]
                    end

                    Core -> Core: Navigation (Scroll, Highlight, Click)
                    Core -> Core: Stall Validation (Page stuck)
                end

                Core --> Orch: Returns (pages, size)
                deactivate Core
            end
            deactivate Orch
        end

        Orch --> CLI: Finalizes Threads
        deactivate Orch

        CLI -> FS: join_category_pages()
        note right: Consolidates all Pickles\ninto a single file
    end
end

CLI --> User: Pipeline Finished
deactivate CLI
@enduml
```

## API

The core scraper logic responsible for navigating the ANVISA portal, handling pagination, and extracting tabular data.
This data contains the real url for each drugs in ANVISA webpage.

::: drugslm.scraper.anvisa.build_index
    options:
        show_source: true
