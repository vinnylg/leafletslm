from datetime import datetime

from drugslm.config import EXTERNAL_DATA_DIR, RAW_DATA_DIR

DADOS_ABERTOS_OUTPUT = EXTERNAL_DATA_DIR / "anvisa" / "dados_abertos.csv"
DADOS_ABERTOS_URL = "https://dados.anvisa.gov.br/dados/DADOS_ABERTOS_MEDICAMENTOS.csv"

BULA_PROFISSIONAL = "produto.idBulaProfissionalProtegido"
BULA_PACIENTE = "produto.idBulaPacienteProtegido"

# ANVISA_LOG_DIR = LOG_DIR / "scraper" / "anvisa"
# ANVISA_LOG_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DIR = RAW_DATA_DIR / "anvisa"
# OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EXECUTION_ID = datetime.now().strftime("%Y%m%d%H%M%S")
INDEX_DIR = OUTPUT_DIR / "index" / EXECUTION_ID
INDEX_DIR.mkdir(parents=True, exist_ok=True)

CATEGORIES_URL = "https://consultas.anvisa.gov.br/#/bulario/q/?categoriasRegulatorias=%s"

CATEGORIES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

SEARCH_COLUMNS = [
    "drugs",
    "url",
    "company",
    "code",
    "publication_date",
]
