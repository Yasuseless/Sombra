import re

from busca import cpf_valido

class ContatoInvalido(Exception):

    def __init__(self, mensagem: str, campo: str):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.campo = campo

def validar_novo_contato(corpo: dict) -> dict:

    nome = " ".join(str(corpo.get("nome", "")).split())
    if not nome:
        raise ContatoInvalido("Informe o nome do contato.", "nome")
    if len(nome) < 2 or len(nome) > 100:
        raise ContatoInvalido("O nome deve ter entre 2 e 100 caracteres.", "nome")
    if re.search(r"[\d<>{}\[\]\\/;=@]", nome):
        raise ContatoInvalido("Use apenas letras no nome.", "nome")

    cpf = str(corpo.get("cpf", "")).strip()
    if cpf:
        if not cpf_valido(cpf):
            raise ContatoInvalido("CPF inválido. Confira os números digitados.", "cpf")
        cpf = re.sub(r"\D", "", cpf)

    email = str(corpo.get("email", "")).strip().lower()
    if email and (len(email) > 120 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)):
        raise ContatoInvalido("E-mail inválido. Confira o endereço digitado.", "email")

    telefone = str(corpo.get("telefone", "")).strip()
    if telefone:
        digitos = re.sub(r"\D", "", telefone)
        if not 10 <= len(digitos) <= 13 or (len(digitos) >= 12 and not digitos.startswith("55")):
            raise ContatoInvalido("Telefone inválido. Informe com DDD, por exemplo (11) 98765-4321.", "telefone")
        telefone = digitos if len(digitos) >= 12 else "55" + digitos

    return {"nome": nome, "cpf": cpf, "email": email, "telefone": telefone}

def validar_classificacao(corpo: dict) -> str:

    texto = " ".join(str(corpo.get("classificacao", "")).split())
    if not texto:
        return ""
    if len(texto) < 2 or len(texto) > 40:
        raise ContatoInvalido("A classificação deve ter entre 2 e 40 caracteres.", "classificacao")
    if re.search(r"[\d<>{}\[\]\\;=@_]", texto):
        raise ContatoInvalido("Use apenas letras e espaços na classificação.", "classificacao")
    return texto[0].upper() + texto[1:]
