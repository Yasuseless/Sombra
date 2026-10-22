import re

def mascarar_telefone(telefone: str) -> str:
    digitos = re.sub(r"\D", "", telefone)
    if len(digitos) < 10:
        return "***"
    prefixo = "+" if digitos.startswith("55") and len(digitos) >= 12 else ""
    return f"{prefixo}{digitos[:-8]}****{digitos[-4:]}"

def mascarar_email(email: str) -> str:
    usuario, _, dominio = email.partition("@")
    if not usuario or not dominio:
        return "***"
    if len(usuario) <= 6:
        return f"{usuario[0]}****@{dominio}"
    return f"{usuario[:4]}****{usuario[-2:]}@{dominio}"

def mascarar_cpf(cpf: str) -> str:
    digitos = re.sub(r"\D", "", cpf)
    if len(digitos) != 11:
        return "***"
    return f"***.{digitos[3:6]}.{digitos[6:9]}-**"
