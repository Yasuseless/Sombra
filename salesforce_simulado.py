import copy
import re
import threading

LIMITE_ALTERNATIVOS = 3

LIMITES_POR_PAPEL = {"corretor": 1}
PAPEIS_QUALIFICADOS = ("comprador", "vendedor", "corretor")

def limite_alternativos(papel: str) -> int:
    return LIMITES_POR_PAPEL.get(papel, LIMITE_ALTERNATIVOS)
_TRAVA = threading.Lock()

class ErroContato(Exception):

    def __init__(self, mensagem: str, status: int = 400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status

def _cpf_ficticio(base9: str) -> str:

    n = [int(c) for c in base9]
    for _ in range(2):
        soma = sum(d * p for d, p in zip(n, range(len(n) + 1, 1, -1)))
        n.append((soma * 10) % 11 % 10)
    return "".join(map(str, n))

OFFERS = {
    "Db0ZHelOoxLY3Inr3ZCU": {
        "imovel": "Apartamento 2 quartos · Pinheiros, São Paulo",
        "id_imovel": "890250358",
        "contatos": [
            {"id": "c1", "papel": "comprador", "nome": "Marina Alves",
             "telefone": "+55 11 98765-4321", "email": "marina.alves@exemplo.com", "cpf": _cpf_ficticio("529982247"),
             "atendimentos": [
                 {"data": "2026-09-15", "ticket": "TK-485240", "tema": "Dúvidas gerais", "analista": "Analista 4", "canal": "Chat",
                  "resumo": "Perguntou sobre documentos para o cartório. Confirmado que falta só a certidão de estado civil atualizada; a cliente enviará até sexta."},
                 {"data": "2026-09-08", "ticket": "TK-482913", "tema": "Prazos", "analista": "Analista 1", "canal": "Telefone",
                  "resumo": "Dúvida sobre o prazo do ITBI. Orientada a pagar a guia em até 5 dias úteis após a emissão. Passo a passo enviado por e-mail."},

                 {"data": "2026-09-18", "hora": "10:42", "ticket": "", "tema": "Dúvidas gerais", "analista": "Analista 3", "canal": "Telefone",
                  "origem": "dashboard",
                  "resumo": "Cliente ligou para confirmar o recebimento da guia do ITBI. Confirmado o envio por e-mail; sem novas pendências."},
             ]},
            {"id": "c2", "papel": "vendedor", "nome": "Carlos Menezes",
             "telefone": "+55 11 97654-3210", "email": "carlos.menezes@exemplo.com", "cpf": _cpf_ficticio("111444777"),
             "atendimentos": [
                 {"data": "2026-09-10", "ticket": "TK-483677", "tema": "Prazos", "analista": "Analista 1", "canal": "Telefone",
                  "resumo": "Questionou a data de repasse do valor da venda. Explicado que o repasse ocorre após o registro da escritura; previsão informada de 10 dias úteis."},
             ]},
            {"id": "c3", "papel": "corretor", "nome": "Bruno Tavares",
             "telefone": "+55 11 96543-2109", "email": "bruno.tavares@exemplo.com", "cpf": _cpf_ficticio("390533447"),
             "atendimentos": [
                 {"data": "2026-09-12", "ticket": "TK-486210", "tema": "Troca de PP", "analista": "Analista 6", "canal": "Telefone",
                  "resumo": "Corretora pediu para trocar a proposta de pagamento (PP) registrada, incluindo um novo sinal combinado com o comprador."},
             ]},

            {"id": "alt1", "papel": "alternativo", "pai": "c1", "nome": "Fernanda Lima", "classificacao": "",
             "telefone": "+55 11 94321-0987", "email": "fernanda.lima@exemplo.com", "cpf": _cpf_ficticio("168995350"),
             "atendimentos": [
                 {"data": "2026-09-16", "ticket": "TK-485902", "tema": "Dúvidas gerais", "analista": "Analista 4", "canal": "E-mail",
                  "resumo": "Solicitou a minuta da escritura para revisão. Minuta enviada; retorno esperado em 2 dias úteis."},
             ]},
        ],
    },
    "hCiupweww8k9bKuOo6MV": {
        "imovel": "Casa 3 quartos · Batel, Curitiba",
        "id_imovel": "897505739",
        "contatos": [
            {"id": "c1", "papel": "comprador", "nome": "Ricardo Souza",
             "telefone": "+55 11 98888-4321", "email": "ricardo.souza@exemplo.com", "cpf": _cpf_ficticio("987654320"),
             "atendimentos": [
                 {"data": "2026-09-12", "ticket": "TK-484410", "tema": "Dúvidas gerais", "analista": "Analista 7", "canal": "Chat",
                  "resumo": "Quis saber o que é avaliado na vistoria. Explicado o escopo (estrutura, elétrica, hidráulica) e que o laudo sai em até 3 dias úteis."},
             ]},
            {"id": "c2", "papel": "vendedor", "nome": "Patrícia Nogueira",
             "telefone": "+55 41 97777-2222", "email": "patricia.nogueira@exemplo.com", "cpf": _cpf_ficticio("246813570"),
             "atendimentos": [
                 {"data": "2026-09-18", "ticket": "TK-486455", "tema": "Distratos", "analista": "Analista 9", "canal": "E-mail",
                  "resumo": "Vendedora questionou o procedimento de distrato, caso o comprador desista da compra antes da vistoria."},
             ]},
            {"id": "c3", "papel": "corretor", "nome": "Aline Barros",
             "telefone": "+55 41 96666-3333", "email": "aline.barros@exemplo.com", "cpf": _cpf_ficticio("135792460"),
             "atendimentos": [
                 {"data": "2026-09-14", "ticket": "TK-484955", "tema": "Envio de NF", "analista": "Analista 5", "canal": "Telefone",
                  "resumo": "Solicitou o envio da nota fiscal da comissão. NF encaminhada por e-mail e recebimento confirmado pela corretora."},
             ]},
        ],
    },
    "6wJ4Le7vxV25IHKPoc1T": {
        "imovel": "Apartamento 3 quartos · Savassi, Belo Horizonte",
        "id_imovel": "891929954",
        "contatos": [
            {"id": "c1", "papel": "comprador", "nome": "Renata Cordeiro",
             "telefone": "+55 31 99825-1686", "email": "renata@exemplomail.com", "cpf": "96792908169",
             "atendimentos": [
                 {"data": "2026-09-23", "ticket": "TK-488080", "tema": "Dúvidas sobre locação", "analista": "Analista 3", "canal": "E-mail", "resumo": "Atendimento de demonstração sobre a documentação pendente."},
                 {"data": "2026-09-11", "ticket": "TK-486385", "tema": "Dúvidas gerais", "analista": "Analista 5", "canal": "Telefone", "resumo": "Atendimento de demonstração sobre o andamento do processo."},
             ]},
            {"id": "c2", "papel": "vendedor", "nome": "Vinícius Lacerda",
             "telefone": "+55 31 94116-4963", "email": "vinicius@exemplo.com", "cpf": "90757938396",
             "atendimentos": [
                 {"data": "2026-09-14", "ticket": "TK-486702", "tema": "Estorno de pagamento", "analista": "Analista 10", "canal": "Telefone",
                  "resumo": "Vendedor solicitou o estorno de uma taxa cobrada em duplicidade durante o processo de venda."},
             ]},
            {"id": "c3", "papel": "corretor", "nome": "Tábata Freire",
             "telefone": "+55 31 94762-9403", "email": "tabata@exemplomail.com", "cpf": "40191614610",
             "atendimentos": [
                 {"data": "2026-09-05", "ticket": "TK-488713", "tema": "Envio de CCV", "analista": "Analista 8", "canal": "E-mail", "resumo": "Atendimento de demonstração sobre a documentação pendente."},
                 {"data": "2026-09-21", "ticket": "TK-488257", "tema": "Envio de CCV", "analista": "Analista 12", "canal": "Chat", "resumo": "Atendimento de demonstração sobre a documentação pendente."},
             ]},
        ],
    },
    "tDui4mlmzJPKzC05ZgD1": {
        "imovel": "Casa 4 quartos · Moinhos de Vento, Porto Alegre",
        "id_imovel": "896506401",
        "contatos": [
            {"id": "c1", "papel": "comprador", "nome": "Otávio Barreto",
             "telefone": "+55 51 97511-7877", "email": "otavio@exemplo.com", "cpf": "19345145001",
             "atendimentos": [
                 {"data": "2026-09-05", "ticket": "TK-486874", "tema": "Dúvidas sobre locação", "analista": "Analista 1", "canal": "Chat", "resumo": "Atendimento de demonstração sobre a documentação pendente."},
             ]},
            {"id": "c2", "papel": "vendedor", "nome": "Beatriz Homem",
             "telefone": "+55 51 93205-5036", "email": "beatriz@exemplomail.com", "cpf": "10077283708",
             "atendimentos": [
                 {"data": "2026-09-20", "ticket": "TK-486918", "tema": "Pedido de retorno do analista", "analista": "Analista 11", "canal": "Chat",
                  "resumo": "Cliente pediu para o analista retornar assim que tivesse novidades sobre a liberação do financiamento."},
             ]},
            {"id": "c3", "papel": "corretor", "nome": "André Bittencourt",
             "telefone": "+55 51 94487-1007", "email": "andre@exemplo.com", "cpf": "49403269936",
             "atendimentos": [
                 {"data": "2026-09-21", "ticket": "TK-488636", "tema": "Envio de NF", "analista": "Analista 2", "canal": "Chat", "resumo": "Atendimento de demonstração sobre a documentação pendente."},
             ]},
        ],
    },
    "BO5J2YceznSvPubv47cA": {
        "imovel": "Apartamento 1 quarto · Boa Viagem, Recife",
        "id_imovel": "890632503",
        "contatos": [
            {"id": "c1", "papel": "comprador", "nome": "Camila Duarte",
             "telefone": "+55 81 96389-5854", "email": "camila@exemplo.com", "cpf": "61113930900",
             "atendimentos": [
                 {"data": "2026-09-11", "ticket": "TK-486873", "tema": "Dúvidas gerais", "analista": "Analista 5", "canal": "Telefone", "resumo": "Atendimento de demonstração sobre o próximo passo combinado com o cliente."},
             ]},
            {"id": "c2", "papel": "vendedor", "nome": "Gustavo Peixoto",
             "telefone": "+55 81 97325-3995", "email": "gustavo@exemplomail.com", "cpf": "24393328361",
             "atendimentos": [
                 {"data": "2026-09-23", "ticket": "TK-486521", "tema": "Dúvidas gerais", "analista": "Analista Demonstração", "canal": "E-mail", "resumo": "Atendimento de demonstração sobre o andamento do processo."},
             ]},
            {"id": "c3", "papel": "corretor", "nome": "Priscila Nascimento",
             "telefone": "+55 81 99044-5807", "email": "priscila@exemplomail.com", "cpf": "82123789933",
             "atendimentos": [
                 {"data": "2026-09-09", "ticket": "TK-487726", "tema": "Dúvidas sobre anúncio", "analista": "Analista 2", "canal": "Telefone", "resumo": "Atendimento de demonstração sobre o andamento do processo."},
                 {"data": "2026-09-17", "ticket": "TK-486976", "tema": "Envio de NF", "analista": "Analista 5", "canal": "Chat", "resumo": "Atendimento de demonstração sobre o próximo passo combinado com o cliente."},
             ]},
        ],
    },
    "6g8XZVLI5cfQmytAhZad": {
        "imovel": "Cobertura 3 quartos · Asa Sul, Brasília",
        "id_imovel": "891847098",
        "contatos": [
            {"id": "c1", "papel": "comprador", "nome": "Felipe Andrade",
             "telefone": "+55 61 95410-7740", "email": "felipe@exemplo.com", "cpf": "73002458970",
             "atendimentos": [
                 {"data": "2026-09-13", "ticket": "TK-489757", "tema": "Dúvidas sobre locação", "analista": "Analista 12", "canal": "Telefone", "resumo": "Atendimento de demonstração sobre o andamento do processo."},
             ]},
            {"id": "c2", "papel": "vendedor", "nome": "Larissa Vieira",
             "telefone": "+55 61 96933-3267", "email": "larissa@exemplo.com", "cpf": "75892900762",
             "atendimentos": [
                 {"data": "2026-09-16", "ticket": "TK-487033", "tema": "Pagamentos", "analista": "Analista 2", "canal": "Telefone",
                  "resumo": "Vendedora perguntou sobre a forma de pagamento da comissão da corretora após o registro da escritura."},
             ]},
            {"id": "c3", "papel": "corretor", "nome": "Rodrigo Camargo",
             "telefone": "+55 61 96096-6224", "email": "rodrigo@exemplomail.com", "cpf": "21178502511",
             "atendimentos": [
                 {"data": "2026-09-05", "ticket": "TK-486087", "tema": "Envio de CCV", "analista": "Analista 8", "canal": "Telefone", "resumo": "Atendimento de demonstração sobre o próximo passo combinado com o cliente."},
             ]},
        ],
    },
    "txAWWSYWGH0jq3eyH223": {
        "imovel": "Apartamento 2 quartos · Vila Madalena, São Paulo",
        "id_imovel": "892818427",
        "contatos": [
            {"id": "c1", "papel": "comprador", "nome": "Luana Pires",
             "telefone": "+55 11 99190-1238", "email": "luana@exemplomail.com", "cpf": "96690911101",
             "atendimentos": [
                 {"data": "2026-09-23", "ticket": "TK-489689", "tema": "Envio de CCV", "analista": "Analista Demonstração", "canal": "Chat", "resumo": "Atendimento de demonstração sobre o andamento do processo."},
             ]},
            {"id": "c2", "papel": "vendedor", "nome": "Marcelo Quintão",
             "telefone": "+55 11 98499-8217", "email": "marcelo@exemplo.com", "cpf": "78188049190",
             "atendimentos": [
                 {"data": "2026-09-21", "ticket": "TK-488982", "tema": "Aditivos", "analista": "Analista 7", "canal": "E-mail", "resumo": "Atendimento de demonstração sobre o próximo passo combinado com o cliente."},
             ]},
            {"id": "c3", "papel": "corretor", "nome": "Cecília Matoso",
             "telefone": "+55 11 94771-2849", "email": "cecilia@exemplomail.com", "cpf": "79740542980",
             "atendimentos": []},
        ],
    },
    "fdbTPlX31iIGXwjsVFj3": {
        "imovel": "Casa 3 quartos · Jardim Botânico, Rio de Janeiro",
        "id_imovel": "895673254",
        "contatos": [
            {"id": "c1", "papel": "comprador", "nome": "Diego Salgado",
             "telefone": "+55 21 97631-5105", "email": "diego@exemplo.com", "cpf": "36336395359",
             "atendimentos": [
                 {"data": "2026-09-19", "ticket": "TK-488703", "tema": "Dúvidas gerais", "analista": "Analista 8", "canal": "Telefone", "resumo": "Atendimento de demonstração sobre a documentação pendente."},
             ]},
            {"id": "c2", "papel": "vendedor", "nome": "Yasmin Rocha",
             "telefone": "+55 21 93771-2848", "email": "yasmin@exemplo.com", "cpf": "77436687549",
             "atendimentos": [
                 {"data": "2026-09-23", "ticket": "TK-487436", "tema": "Dúvidas sobre anúncio", "analista": "Analista 12", "canal": "Telefone", "resumo": "Atendimento de demonstração sobre a documentação pendente."},
             ]},
            {"id": "c3", "papel": "corretor", "nome": "Igor Pellegrini",
             "telefone": "+55 21 95605-6803", "email": "igor@exemplomail.com", "cpf": "49026730454",
             "atendimentos": [
                 {"data": "2026-09-09", "ticket": "TK-489394", "tema": "Dúvidas sobre anúncio", "analista": "Analista 5", "canal": "E-mail", "resumo": "Atendimento de demonstração sobre o andamento do processo."},
             ]},
        ],
    },}

def buscar_offer(offer: str):

    with _TRAVA:
        dados = OFFERS.get(offer)
        return copy.deepcopy(dados) if dados else None

def _digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto or "")

def adicionar_alternativo(offer: str, pai_id: str, novo: dict) -> str:

    with _TRAVA:
        dados = OFFERS.get(offer)
        if dados is None:
            raise ErroContato("Offer não encontrada.", 404)
        contatos = dados["contatos"]

        pai = next((c for c in contatos if c["id"] == pai_id), None)
        if pai is None or pai["papel"] not in PAPEIS_QUALIFICADOS:
            raise ErroContato("Contato qualificado não encontrado neste processo.", 404)

        limite = limite_alternativos(pai["papel"])
        if sum(1 for c in contatos if c.get("pai") == pai_id) >= limite:
            raise ErroContato(
                f"Limite de {limite} contatos alternativos atingido para {pai['nome']}.", 409)

        for c in contatos:
            if novo["cpf"] and _digitos(c.get("cpf")) == novo["cpf"]:
                raise ErroContato(f"Este CPF já está cadastrado neste processo ({c['nome']}).", 409)
            if novo["email"] and (c.get("email") or "").lower() == novo["email"]:
                raise ErroContato(f"Este e-mail já está cadastrado neste processo ({c['nome']}).", 409)
            if novo["telefone"] and _digitos(c.get("telefone"))[-11:] == novo["telefone"][-11:]:
                raise ErroContato(f"Este telefone já está cadastrado neste processo ({c['nome']}).", 409)

        proximo = 1 + max([int(c["id"][3:]) for c in contatos if c["id"].startswith("alt")] or [0])
        contato = {"id": f"alt{proximo}", "papel": "alternativo", "pai": pai_id, "nome": novo["nome"], "classificacao": "",
                   "telefone": novo["telefone"], "email": novo["email"], "cpf": novo["cpf"],
                   "atendimentos": []}
        contatos.append(contato)
        return contato["id"]

MAX_ATENDIMENTOS_POR_CONTATO = 200

def adicionar_atendimento(offer: str, contato_id: str, registro: dict) -> None:

    with _TRAVA:
        dados = OFFERS.get(offer)
        if dados is None:
            raise ErroContato("Offer não encontrada.", 404)
        contato = next((c for c in dados["contatos"] if c["id"] == contato_id), None)
        if contato is None:
            raise ErroContato("Contato não encontrado neste processo.", 404)
        if len(contato["atendimentos"]) >= MAX_ATENDIMENTOS_POR_CONTATO:
            raise ErroContato("Limite de registros atingido para este contato.", 409)
        contato["atendimentos"].append(registro)

def classificar_alternativo(offer: str, contato_id: str, classificacao: str) -> None:

    with _TRAVA:
        dados = OFFERS.get(offer)
        if dados is None:
            raise ErroContato("Offer não encontrada.", 404)
        contato = next((c for c in dados["contatos"] if c["id"] == contato_id), None)
        if contato is None:
            raise ErroContato("Contato não encontrado neste processo.", 404)
        if contato["papel"] != "alternativo":
            raise ErroContato("Somente contatos alternativos podem ser reclassificados.", 400)
        contato["classificacao"] = classificacao

def todos_atendimentos():
    resultado = []
    with _TRAVA:
        for offer, dados in OFFERS.items():
            for contato in dados["contatos"]:
                for atendimento in contato["atendimentos"]:
                    resultado.append({
                        "offer": offer,
                        "imovel": dados["imovel"],
                        "contato": contato["nome"],
                        "contato_papel": contato["papel"],
                        "data": atendimento["data"],
                        "hora": atendimento.get("hora", ""),
                        "canal": atendimento["canal"],
                        "tema": atendimento.get("tema", ""),
                        "ticket": atendimento.get("ticket", ""),
                        "analista": atendimento["analista"],
                        "origem": atendimento.get("origem", "salesforce"),
                        "resumo": atendimento["resumo"],
                    })
    return resultado
