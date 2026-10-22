import re

from salesforce_simulado import OFFERS

class BuscaInvalida(Exception):
    pass

def _digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto)

def cpf_valido(cpf: str) -> bool:
    d = _digitos(cpf)
    if len(d) != 11 or len(set(d)) == 1:
        return False
    for tamanho in (9, 10):
        soma = sum(int(d[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10) % 11 % 10
        if digito != int(d[tamanho]):
            return False
    return True

_CPF_FORMATADO = re.compile(r"[\d*]{3}\.[\d*]{3}\.[\d*]{3}-[\d*]{2}")

def detectar_tipo(consulta: str) -> str:
    q = consulta.strip()
    if not q:
        raise BuscaInvalida("Informe a Offer, o ID do imóvel, o telefone, o e-mail ou o CPF do cliente.")
    if "@" in q:
        return "email"
    if re.fullmatch(r"89\d{7,11}", q):
        return "imovel"
    if re.fullmatch(r"[A-Za-z0-9]{20}", q):
        return "offer"
    if _CPF_FORMATADO.fullmatch(q):
        return "cpf"
    if re.fullmatch(r"\d{11}", q) and cpf_valido(q):
        return "cpf"
    if re.fullmatch(r"[0-9()+\-*.\s]+", q):
        return "telefone"
    if re.fullmatch(r"[A-Za-z0-9]{1,40}", q):
        return "offer"
    raise BuscaInvalida("Formato não reconhecido. Use a Offer, o ID do imóvel (9 dígitos, começa com 89), o telefone, o e-mail ou o CPF.")

def _casador_telefone(consulta: str):
    q = consulta.strip()
    if "*" in q:
        partes = re.split(r"\*+", q)
        if len(partes) != 2:
            raise BuscaInvalida("Telefone censurado deve seguir o formato +55219****3247.")
        inicio, fim = _digitos(partes[0]), _digitos(partes[1])
        if len(inicio) + len(fim) < 6:
            raise BuscaInvalida("Informe ao menos 6 dígitos visíveis do telefone, como em +55219****3247.")

        def casa(telefone: str) -> bool:
            d = _digitos(telefone)
            variantes = {d}
            if d.startswith("55") and len(d) >= 12:
                variantes.add(d[2:])
            return any(v.startswith(inicio) and v.endswith(fim) and len(v) > len(inicio) + len(fim)
                       for v in variantes)
        return casa
    digitos = _digitos(q)
    if len(digitos) < 8:
        raise BuscaInvalida("Informe o telefone completo (com DDD) ou censurado, como em +55219****3247.")
    return lambda tel: _digitos(tel).endswith(digitos)

def _casador_email(consulta: str):
    q = consulta.strip().lower()
    if "*" in q:
        m = re.fullmatch(r"([^*@\s]*)\*+([^*@\s]*)@([^@\s*]+)", q)
        if not m:
            raise BuscaInvalida("E-mail censurado deve seguir o formato marc****32@gmail.com.")
        inicio, fim, dominio = m.groups()
        if len(inicio) + len(fim) < 3:
            raise BuscaInvalida("Informe ao menos 3 caracteres visíveis antes do @, como em marc****32@gmail.com.")

        def casa(email: str) -> bool:
            usuario, _, dom = email.lower().partition("@")
            return (dom == dominio and usuario.startswith(inicio) and usuario.endswith(fim)
                    and len(usuario) > len(inicio) + len(fim))
        return casa
    if not re.fullmatch(r"[^@\s]+@[^@\s]+", q):
        raise BuscaInvalida("E-mail inválido. Confira o endereço digitado.")
    return lambda e: e.lower() == q

def _casador_cpf(consulta: str):
    q = consulta.strip()
    if "*" in q:
        if not _CPF_FORMATADO.fullmatch(q):
            raise BuscaInvalida("CPF censurado deve seguir o formato ***.456.789-**.")
        posicoes = re.sub(r"[.\-]", "", q)
        if sum(c.isdigit() for c in posicoes) < 4:
            raise BuscaInvalida("Informe ao menos 4 dígitos visíveis do CPF, como em ***.456.789-**.")
        return lambda cpf: len(_digitos(cpf)) == 11 and all(
            p == "*" or p == d for p, d in zip(posicoes, _digitos(cpf)))
    if not cpf_valido(q):
        raise BuscaInvalida("CPF inválido. Confira os números digitados.")
    return lambda cpf: _digitos(cpf) == _digitos(q)

_CASADORES = {
    "telefone": (_casador_telefone, "telefone"),
    "email": (_casador_email, "email"),
    "cpf": (_casador_cpf, "cpf"),
}

def _procurar(tipo: str, q: str):
    resultados = []
    for codigo, dados in OFFERS.items():
        base = {"offer": codigo, "imovel": dados["imovel"], "id_imovel": dados["id_imovel"],
                "contato_id": None, "contato": None}
        if tipo == "offer":
            if codigo == q:
                resultados.append(base)
        elif tipo == "imovel":
            if dados["id_imovel"] == q:
                resultados.append(base)
    if tipo in _CASADORES:
        criar, campo = _CASADORES[tipo]
        casa = criar(q)
        for codigo, dados in OFFERS.items():
            for contato in dados["contatos"]:
                if casa(contato.get(campo) or ""):
                    resultados.append({"offer": codigo, "imovel": dados["imovel"],
                                       "id_imovel": dados["id_imovel"],
                                       "contato_id": contato["id"], "contato": contato["nome"]})
                    break
    return resultados

def buscar(consulta: str):

    tipo = detectar_tipo(consulta)
    q = consulta.strip()
    resultados = _procurar(tipo, q)
    if not resultados and tipo == "cpf" and re.fullmatch(r"\d{11}", q):
        tipo = "telefone"
        resultados = _procurar(tipo, q)
    return tipo, resultados
