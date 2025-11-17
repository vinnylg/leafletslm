from datetime import datetime
from pathlib import Path

from drugslm.config import EXTERNAL_DATA_DIR, LOG_DIR, RAW_DATA_DIR

DADOS_ABERTOS_OUTPUT = EXTERNAL_DATA_DIR / "DADOS_ABERTOS_MEDICAMENTOS.csv"
DADOS_ABERTOS_URL = "https://dados.anvisa.gov.br/dados/DADOS_ABERTOS_MEDICAMENTOS.csv"

BULA_PROFISSIONAL = "produto.idBulaProfissionalProtegido"
BULA_PACIENTE = "produto.idBulaPacienteProtegido"

ANVISA_LOG_DIR = LOG_DIR / "dataset" / "anvisa"
ANVISA_LOG_DIR.mkdir(exist_ok=True)

OUTPUT_DIR = RAW_DATA_DIR / "anvisa"
OUTPUT_DIR.mkdir(exist_ok=True)

CATEGORIES_URL = "https://consultas.anvisa.gov.br/#/bulario/q/?categoriasRegulatorias=%s"

CATEGORIAS = [1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12]

SEARCH_COLUMNS = [
    "Medicamento",
    "Link_Medicamento",
    "Empresa - CNPJ",
    "Expediente",
    "Data de Publicação",
]

ANVISA_LOG_DIR = LOG_DIR / "dataset" / "anvisa"


def get_anvisa_log_path(script_name: str) -> Path:
    """
    Generates a standardized, timestamped log file path for an ANVISA script.

    Args:
        script_name: The name of the script/process (e.g., "search", "download").

    Returns:
        A Path object for the log file.
        (e.g., .../logs/dataset/anvisa/search/20251117_143000.log)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    script_log_dir = ANVISA_LOG_DIR / script_name

    script_log_dir.mkdir(parents=True, exist_ok=True)

    return script_log_dir / f"{timestamp}.log"
