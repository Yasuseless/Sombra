"""
Gera os assuntos de cada atendimento a partir do texto do resumo.

Aqui usamos palavras-chave só para a demonstração. Na versão real, esta função
poderia chamar um modelo de IA para ler as anotações do ticket e devolver o
resumo e as tags (desde que a política interna de dados permita).
"""

ASSUNTOS = {
    "ITBI": ["itbi"],
    "Documentos": ["documento", "certidão"],
    "Cartório": ["cartório"],
    "Repasse": ["repasse"],
    "Minuta": ["minuta"],
    "Escritura": ["escritura"],
    "Vistoria": ["vistoria"],
    "Laudo": ["laudo"],
    "Agenda": ["horário", "agendad"],
    "Prazos": ["prazo", "dias úteis", "previsão"],
}


def extrair_assuntos(resumo: str) -> list[str]:
    texto = resumo.lower()
    return [nome for nome, palavras in ASSUNTOS.items() if any(p in texto for p in palavras)]
