from drugslm.config import EXTERNAL

DADOS_ABERTOS_URL = "https://dados.anvisa.gov.br/dados/DADOS_ABERTOS_MEDICAMENTOS.csv"
DADOS_ABERTOS = EXTERNAL / "anvisa" / "dados_abertos.csv"

BULA_PROFISSIONAL = "produto.idBulaProfissionalProtegido"
BULA_PACIENTE = "produto.idBulaPacienteProtegido"


def get_more_info():
    pass


def download():
    pass
