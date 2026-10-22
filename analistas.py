import unicodedata

ANALISTAS_AUTORIZADOS = [
    "Analista 1",
    "Analista 2",
    "Analista 3",
    "Analista 4",
    "Analista 5",
    "Analista 6",
    "Analista 7",
    "Analista 8",
    "Analista 9",
    "Analista 10",
    "Analista 11",
    "Analista 12",
    "Analista 13",
    "Analista Demonstração",
]

def _normalizar(nome: str) -> str:

    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    return " ".join(sem_acento.casefold().split())

_POR_NOME = {_normalizar(n): n for n in ANALISTAS_AUTORIZADOS}

def validar_analista(nome: str) -> str:

    return _POR_NOME.get(_normalizar(nome or ""), "Analista não cadastrado")
