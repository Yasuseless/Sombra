from collections import defaultdict
from datetime import datetime, timedelta

from analistas import ANALISTAS_AUTORIZADOS, validar_analista
from registros import TEMAS
from salesforce_simulado import todos_atendimentos

TODOS_OS_TEMAS = "Todos os temas"

def _data_hora(a):
    return a["data"] + " " + (a.get("hora") or "00:00")

def resumo_por_analista():
    atendimentos = todos_atendimentos()
    agrupado = defaultdict(list)
    for a in atendimentos:
        nome = validar_analista(a["analista"])
        agrupado[nome].append(a)

    linhas = []
    for nome in ANALISTAS_AUTORIZADOS:
        itens = agrupado.get(nome, [])
        dashboard = sum(1 for a in itens if a["origem"] == "dashboard")
        salesforce = sum(1 for a in itens if a["origem"] != "dashboard")
        ultimo = max((a["data"] for a in itens), default=None)
        linhas.append({
            "analista": nome,
            "total": len(itens),
            "dashboard": dashboard,
            "salesforce": salesforce,
            "ultimo": ultimo,
        })
    linhas.sort(key=lambda l: l["total"], reverse=True)
    return linhas

def atendimentos_do_analista(nome):
    alvo = validar_analista(nome)
    itens = [a for a in todos_atendimentos() if validar_analista(a["analista"]) == alvo]
    itens.sort(key=_data_hora, reverse=True)
    return itens

def _chave_dia(data_iso):
    return data_iso

def _chave_semana(data_iso):
    return datetime.strptime(data_iso, "%Y-%m-%d").strftime("%G-S%V")

def _chave_mes(data_iso):
    return data_iso[:7]

def volumetria(tema=None, inicio=None, fim=None):
    atendimentos = todos_atendimentos()
    todas_datas = sorted({a["data"] for a in atendimentos})

    if not todas_datas:
        return {"baldes": [], "series": [], "granularidade": "dia", "min_data": None,
                "max_data": None, "inicio": None, "fim": None,
                "temas_disponiveis": list(TEMAS), "total": 0}

    minimo, maximo = todas_datas[0], todas_datas[-1]
    ini = inicio if inicio else minimo
    fim_ = fim if fim else maximo
    if ini > fim_:
        ini, fim_ = fim_, ini

    filtrados = [a for a in atendimentos if ini <= a["data"] <= fim_]
    tema_valido = tema if tema and tema in TEMAS else None
    if tema_valido:
        filtrados = [a for a in filtrados if a["tema"] == tema_valido]

    d_ini = datetime.strptime(ini, "%Y-%m-%d")
    d_fim = datetime.strptime(fim_, "%Y-%m-%d")
    dias_totais = (d_fim - d_ini).days + 1

    if dias_totais <= 31:
        granularidade, chave = "dia", _chave_dia
    elif dias_totais <= 180:
        granularidade, chave = "semana", _chave_semana
    else:
        granularidade, chave = "mes", _chave_mes

    baldes = []
    vistos = set()
    cursor = d_ini
    while cursor <= d_fim:
        b = chave(cursor.strftime("%Y-%m-%d"))
        if b not in vistos:
            vistos.add(b)
            baldes.append(b)
        cursor += timedelta(days=1)

    if tema_valido:
        temas_presentes = [tema_valido]
    else:
        temas_presentes = [t for t in TEMAS if any(a["tema"] == t for a in filtrados)]

    contagem = {t: {b: 0 for b in baldes} for t in temas_presentes}
    for a in filtrados:
        b = chave(a["data"])
        if a["tema"] in contagem and b in contagem[a["tema"]]:
            contagem[a["tema"]][b] += 1

    series = [{"tema": t, "valores": [contagem[t][b] for b in baldes]} for t in temas_presentes]

    return {"baldes": baldes, "series": series, "granularidade": granularidade,
            "min_data": minimo, "max_data": maximo, "inicio": ini, "fim": fim_,
            "temas_disponiveis": list(TEMAS), "total": len(filtrados)}
