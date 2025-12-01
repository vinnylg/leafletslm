from dagster import (
    AssetExecutionContext,
    AssetsDefinition,
    Definitions,
    DynamicOut,
    DynamicOutput,
    In,
    List,
    MaterializeResult,
    MetadataValue,
    OpExecutionContext,
    Out,
    asset,
    graph,
    op,
)
import pandas as pd
from selenium.webdriver.remote.webdriver import WebDriver

# --- IMPORTAÇÕES DO SEU SCRIPT (A Lógica Real) ---
from drugslm.scraper.anvisa.catalog import (
    METADATA,
    CATALOG,
    CATEGORIES,
    fetch_metadata,  # Função simples
    fetch_category_metadata,  # Função auxiliar para planejar
    scrap_pages,  # Função worker
    join_chunks,  # Função join
)

# Recurso do Selenium
from drugslm.scraper.selenium import webdriver_resource

# ==============================================================================
# 1. ASSET SIMPLES: METADADOS
# ==============================================================================


@asset(
    group_name="anvisa_bronze",
    description="Gera o arquivo metadata.csv.",
    compute_kind="python",
)
def anvisa_metadata(context: AssetExecutionContext) -> MaterializeResult:
    """
    Este asset roda sequencialmente para garantir que temos a base.
    """
    context.log.info("Executando fetch_metadata do script catalog.py...")
    fetch_metadata()

    # Retorno apenas para a UI do Dagster ficar bonita
    df = pd.read_csv(METADATA)
    return MaterializeResult(
        metadata={
            "path": str(METADATA),
            "total_items": int(df["num_items"].sum()),
            "preview": MetadataValue.md(df.head().to_markdown()),
        }
    )


# ==============================================================================
# 2. OPERAÇÕES (OPS) PARA O GRAFO DO CATÁLOGO
# (Estas são as peças internas para montar o Asset complexo)
# ==============================================================================


@op(
    out=DynamicOut(),
    description="Lê o metadata e cria uma 'filial' do pipeline para cada categoria.",
)
def plan_scraping_op(context: OpExecutionContext):
    # Dependência implícita: assume que metadata.csv já existe (garantido pelo grafo)
    df = pd.read_csv(METADATA)

    for _, row in df.iterrows():
        cat_id = int(row["category_id"])
        num_items = int(row["num_items"])

        if num_items > 0:
            context.log.info(f"Categoria {cat_id}: {num_items} itens. Agendando...")
            # Cria um ramo dinâmico no Dagster
            yield DynamicOutput(value=cat_id, mapping_key=f"cat_{cat_id}")


@op(
    required_resource_keys={"selenium"},  # Pede o Selenium aqui
    ins={"category_id": In(int)},
    out=Out(str),
    description="Worker que recebe o Driver e processa uma categoria.",
)
def scrape_category_op(context: OpExecutionContext, category_id: int):
    # O Dagster injeta o driver vindo do resource
    driver: WebDriver = context.resources.selenium

    # Chama sua função blindada 'scrap_pages' passando o driver
    # Force=False para usar sua lógica de Resume
    current_page, saved = scrap_pages(driver, category_id, force=False)

    return f"Categoria {category_id} finalizada."


@op(
    ins={"results": In(List[str])},  # Espera uma lista de resultados (sinal que todos acabaram)
    out=Out(pd.DataFrame),
    description="Junta tudo e retorna o DF final.",
)
def consolidate_catalog_op(context: OpExecutionContext, results: list):
    context.log.info("Todas as categorias terminaram. Consolidando...")

    join_chunks(force=False)

    if CATALOG.exists():
        return pd.read_pickle(CATALOG)
    else:
        raise FileNotFoundError("Catalog não encontrado.")


# ==============================================================================
# 3. O GRAFO (CONECTANDO AS PEÇAS)
# ==============================================================================


@graph
def make_catalog_graph():
    # 1. Planejamento: Gera N saídas
    category_ids = plan_scraping_op()

    # 2. Execução: Roda N vezes em paralelo
    # .map() distribui, .collect() aguarda todos
    scrape_results = category_ids.map(scrape_category_op).collect()

    # 3. Consolidação: Roda 1 vez no final
    return consolidate_catalog_op(scrape_results)


# ==============================================================================
# 4. ASSET COMPLEXO (GRAPH-BACKED ASSET)
# ==============================================================================

# Aqui transformamos aquele grafo acima em um Asset oficial
anvisa_catalog = AssetsDefinition.from_graph(
    make_catalog_graph,
    # Esta linha cria a dependência mágica:
    # "Este grafo só roda depois que o asset 'anvisa_metadata' estiver pronto"
    keys_by_input_name={},
    # Se quiser forçar dependência de dados, usaria keys_by_input_name={"entrada": anvisa_metadata.key}
    # Mas como lemos o arquivo do disco no 'plan_scraping_op', vamos definir via 'deps'
)

# Precisamos dizer explicitamente que esse asset depende do metadata
# (workaround comum quando o grafo lê arquivo do disco e não recebe input direto da memória)
anvisa_catalog = anvisa_catalog.to_asset_definition().with_attributes(
    deps=[anvisa_metadata],
    group_name="anvisa_bronze",
    description="Catálogo consolidado (Scraping Paralelo Dinâmico).",
)
