import re

from busca import cpf_valido

CANAIS = ("Telefone", "Chat", "E-mail")

TEMAS = (
    "Troca de PP",
    "Aditivos",
    "Distratos",
    "Estorno de pagamento",
    "Envio de NF",
    "Pedido de retorno do analista",
    "Prazos",
    "Dúvidas gerais",
    "Dúvidas sobre anúncio",
    "Envio de CCV",
    "Pagamentos",
    "Dúvidas sobre locação",
)
MIN_RESUMO = 10
MAX_RESUMO = 1500

class RegistroInvalido(Exception):

    def __init__(self, mensagem: str, campo: str):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.campo = campo

def _tem_cpf_completo(texto: str) -> bool:
    for m in re.finditer(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)", texto):
        if cpf_valido(m.group()):
            return True
    return False

def validar_registro(corpo: dict) -> dict:
    canal = str(corpo.get("canal", "")).strip()
    if canal not in CANAIS:
        raise RegistroInvalido("Escolha o canal do atendimento.", "canal")

    tema = str(corpo.get("tema", "")).strip()
    if tema not in TEMAS:
        raise RegistroInvalido("Escolha o tema da conversa.", "tema")

    ticket = str(corpo.get("ticket", "")).strip()
    if ticket and not re.fullmatch(r"[A-Za-z0-9\-]{3,30}", ticket):
        raise RegistroInvalido("Ticket inválido. Use só letras, números e hífen.", "ticket")

    linhas = [" ".join(l.split()) for l in str(corpo.get("resumo", "")).strip().splitlines()]
    resumo = "\n".join(linhas)
    resumo = re.sub(r"\n{3,}", "\n\n", resumo)
    if len(resumo) < MIN_RESUMO:
        raise RegistroInvalido(f"Descreva o que foi conversado (mínimo de {MIN_RESUMO} caracteres).", "resumo")
    if len(resumo) > MAX_RESUMO:
        raise RegistroInvalido(f"O resumo passou de {MAX_RESUMO} caracteres. Resuma um pouco mais.", "resumo")
    if _tem_cpf_completo(resumo):
        raise RegistroInvalido("O resumo parece conter um CPF completo. Remova o número antes de salvar.", "resumo")
    if re.search(r"(?<!\d)(?:\d[ \-]?){13,19}(?!\d)", resumo):
        raise RegistroInvalido("O resumo parece conter um número de cartão ou de conta. Remova antes de salvar.", "resumo")

    return {"canal": canal, "tema": tema, "ticket": ticket, "resumo": resumo}
