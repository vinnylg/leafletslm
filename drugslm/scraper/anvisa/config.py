from drugslm.config import EXTERNAL_DATA_DIR, RAW_DATA_DIR

DADOS_ABERTOS_OUTPUT = EXTERNAL_DATA_DIR / "anvisa" / "dados_abertos.csv"
DADOS_ABERTOS_URL = "https://dados.anvisa.gov.br/dados/DADOS_ABERTOS_MEDICAMENTOS.csv"

BULA_PROFISSIONAL = "produto.idBulaProfissionalProtegido"
BULA_PACIENTE = "produto.idBulaPacienteProtegido"

ANVISA_DIR = RAW_DATA_DIR / "anvisa"

INDEX_DIR = ANVISA_DIR / "index"

CATEGORIES_URL = "https://consultas.anvisa.gov.br/#/bulario/q/?categoriasRegulatorias=%s"

CATEGORIES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

SEARCH_COLUMNS = [
    "category_id",
    "category_page",
    "medicamento",
    "link",
    "empresa",
    "expediente",
    "data_pub",
]

FETCH_COLUMNS = [
    "category_id",
    "page_size",
    "last_page",
    "num_items",
]

# PROGRESS_COLUMNS = [timestamp,category_id,current_page,last_page,saved_size]
