import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Flask, Response, request
from werkzeug.exceptions import HTTPException

import armazenamento
import usuarios
from analistas import validar_analista
from busca import BuscaInvalida, buscar
from contatos_alternativos import ContatoInvalido, validar_classificacao, validar_novo_contato
from mascaramento import mascarar_cpf, mascarar_email, mascarar_telefone
from registros import TEMAS, RegistroInvalido, validar_registro
from salesforce_simulado import (ErroContato, adicionar_alternativo, adicionar_atendimento, buscar_offer,
                                 classificar_alternativo)
from supervisor import atendimentos_do_analista, resumo_por_analista, volumetria
from usuarios import (DURACAO_SESSAO, BloqueioTemporario, CredenciaisInvalidas, autenticar,
                      encerrar_sessao, obter_sessao)

PASTA = Path(__file__).resolve().parent
FUSO_BRASILIA = timezone(timedelta(hours=-3))

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024
application = app


def agora_br():
    return datetime.now(FUSO_BRASILIA)


def montar_resposta(offer: str):
    dados = buscar_offer(offer)
    if dados is None:
        return None
    hoje = agora_br().date()
    dados["temas"] = list(TEMAS)
    for contato in dados["contatos"]:

        contato["telefone"] = mascarar_telefone(contato["telefone"]) if contato.get("telefone") else ""
        contato["email"] = mascarar_email(contato["email"]) if contato.get("email") else ""
        contato["cpf"] = mascarar_cpf(contato["cpf"]) if contato.get("cpf") else ""
        for atendimento in contato["atendimentos"]:
            atendimento["analista"] = validar_analista(atendimento["analista"])

            if atendimento.get("tema") not in TEMAS:
                atendimento["tema"] = "Não classificado"
            atendimento.setdefault("origem", "salesforce")
        if contato["atendimentos"]:
            ultimo = max(datetime.strptime(a["data"], "%Y-%m-%d").date() for a in contato["atendimentos"])
            contato["ultimo_atendimento_dias"] = (hoje - ultimo).days
        else:
            contato["ultimo_atendimento_dias"] = None
    return dados


def _json(status, dados):
    resposta = Response(json.dumps(dados, ensure_ascii=False), status=status,
                        content_type="application/json; charset=utf-8")
    resposta.headers["Cache-Control"] = "no-store"
    return resposta


def _https():
    protocolo = request.headers.get("X-Forwarded-Proto", "").split(",")[0].strip().lower()
    return protocolo == "https" or request.is_secure


def _definir_cookie(resposta, token, duracao):
    resposta.set_cookie("sessao", token, max_age=duracao, httponly=True,
                        samesite="Strict", path="/", secure=_https())


def _origem_confiavel():
    origem = request.headers.get("Origin")
    if origem is None:
        return True
    host = request.headers.get("Host", "")
    return origem in ("http://" + host, "https://" + host)


def _ler_json():
    try:
        tamanho = request.content_length or 0
        if not 0 < tamanho <= 8192:
            return None
        corpo = json.loads(request.get_data(cache=False).decode("utf-8"))
        return corpo if isinstance(corpo, dict) else None
    except (ValueError, UnicodeDecodeError):
        return None


def _exigir_login():
    sessao = obter_sessao(request.cookies.get("sessao"))
    if sessao is None:
        return None, _json(401, {"erro": "Sessão expirada. Entre novamente."})
    return sessao, None


def _exigir_supervisor():
    sessao, erro = _exigir_login()
    if erro is not None:
        return None, erro
    if sessao.get("papel") != "supervisor":
        return None, _json(403, {"erro": "Acesso restrito a supervisores."})
    return sessao, None


def _data_valida(texto):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", texto or ""):
        return None
    try:
        datetime.strptime(texto, "%Y-%m-%d")
    except ValueError:
        return None
    return texto


def _saude():
    try:
        armazenamento.obter("saude")
        acessivel = True
    except armazenamento.ErroArmazenamento:
        acessivel = False
    dados = {
        "armazenamento": armazenamento.modo(),
        "armazenamento_acessivel": acessivel,
        "credenciais_analista_configuradas": usuarios.ANALISTA_CONFIGURADO,
        "credenciais_supervisor_configuradas": usuarios.SUPERVISOR_CONFIGURADO,
    }
    dados["ok"] = (acessivel and usuarios.ANALISTA_CONFIGURADO and usuarios.SUPERVISOR_CONFIGURADO)
    return _json(200, dados)


def _pagina_inicial():
    arquivo = PASTA / "index.html"
    if not arquivo.exists():
        return Response("Arquivo index.html não encontrado no servidor.", status=500,
                        content_type="text/plain; charset=utf-8")
    resposta = Response(arquivo.read_bytes(), status=200, content_type="text/html; charset=utf-8")
    resposta.headers["Cache-Control"] = "no-store"
    return resposta


def _tratar_get(caminho):
    if caminho in ("/", "/index.html"):
        return _pagina_inicial()

    if caminho == "/api/saude":
        return _saude()

    if caminho == "/api/sessao":
        sessao = obter_sessao(request.cookies.get("sessao"))
        if sessao:
            return _json(200, {"logado": True, "nome": sessao["nome"], "email": sessao["email"],
                               "papel": sessao["papel"]})
        return _json(200, {"logado": False})

    if caminho == "/api/meus-atendimentos":
        sessao, erro = _exigir_login()
        if erro is not None:
            return erro
        return _json(200, {"atendimentos": atendimentos_do_analista(sessao["nome"])})

    if caminho == "/api/supervisor/analistas":
        _, erro = _exigir_supervisor()
        if erro is not None:
            return erro
        return _json(200, {"analistas": resumo_por_analista()})

    if caminho == "/api/supervisor/grafico":
        _, erro = _exigir_supervisor()
        if erro is not None:
            return erro
        tema = request.args.get("tema", "")[:60]
        inicio = _data_valida(request.args.get("inicio", "")[:10])
        fim = _data_valida(request.args.get("fim", "")[:10])
        return _json(200, volumetria(tema or None, inicio, fim))

    if caminho == "/api/supervisor/atendimentos":
        _, erro = _exigir_supervisor()
        if erro is not None:
            return erro
        nome = request.args.get("analista", "")[:60]
        return _json(200, {"analista": nome, "atendimentos": atendimentos_do_analista(nome)})

    correspondencia = re.fullmatch(r"/api/offers/([A-Za-z0-9]{1,40})", caminho)
    if correspondencia:
        sessao, erro = _exigir_login()
        if erro is not None:
            return erro
        offer = correspondencia.group(1)
        dados = montar_resposta(offer)
        logging.info("AUDITORIA usuario=%s offer=%s encontrada=%s", sessao["email"], offer, dados is not None)
        if dados is None:
            return _json(404, {"erro": "Offer não encontrada"})
        return _json(200, dados)

    return _json(404, {"erro": "Rota não encontrada"})


def _tratar_post(caminho):
    if not _origem_confiavel():
        return _json(403, {"erro": "Origem não permitida."})

    if caminho == "/api/login":
        corpo = _ler_json()
        if corpo is None:
            return _json(400, {"erro": "Requisição inválida."})
        try:
            token = autenticar(corpo.get("email"), corpo.get("senha"))
        except BloqueioTemporario:
            logging.info("AUDITORIA login bloqueado por excesso de tentativas")
            return _json(429, {"erro": "Muitas tentativas. Aguarde alguns minutos e tente de novo."})
        except CredenciaisInvalidas:
            logging.info("AUDITORIA login recusado")
            return _json(401, {"erro": "E-mail ou senha incorretos."})
        sessao = obter_sessao(token)
        logging.info("AUDITORIA login usuario=%s", sessao["email"])
        resposta = _json(200, {"nome": sessao["nome"], "email": sessao["email"], "papel": sessao["papel"]})
        _definir_cookie(resposta, token, DURACAO_SESSAO)
        return resposta

    if caminho == "/api/logout":
        token = request.cookies.get("sessao")
        sessao = obter_sessao(token)
        if sessao:
            logging.info("AUDITORIA logout usuario=%s", sessao["email"])
        encerrar_sessao(token)
        resposta = _json(200, {"ok": True})
        _definir_cookie(resposta, "", 0)
        return resposta

    sessao, erro = _exigir_login()
    if erro is not None:
        return erro

    if caminho == "/api/busca":
        corpo = _ler_json()
        if corpo is None:
            return _json(400, {"erro": "Requisição inválida."})
        consulta = str(corpo.get("q", ""))[:80]
        try:
            tipo, resultados = buscar(consulta)
        except BuscaInvalida as erro_busca:
            return _json(400, {"erro": str(erro_busca)})
        termo = consulta if tipo in ("offer", "imovel") else "[protegido]"
        logging.info("AUDITORIA usuario=%s busca=%s termo=%s resultados=%d",
                     sessao["email"], tipo, termo, len(resultados))
        return _json(200, {"tipo": tipo, "resultados": resultados})

    alternativos = re.fullmatch(r"/api/offers/([A-Za-z0-9]{1,40})/alternativos", caminho)
    if alternativos:
        corpo = _ler_json()
        if corpo is None:
            return _json(400, {"erro": "Requisição inválida."})
        offer = alternativos.group(1)
        pai_id = str(corpo.get("pai_id", ""))[:20]
        try:
            novo = validar_novo_contato(corpo)
            novo_id = adicionar_alternativo(offer, pai_id, novo)
        except ContatoInvalido as erro_contato:
            return _json(400, {"erro": erro_contato.mensagem, "campo": erro_contato.campo})
        except ErroContato as erro_contato:
            return _json(erro_contato.status, {"erro": erro_contato.mensagem})
        logging.info("AUDITORIA usuario=%s offer=%s acao=adicionar_contato_alternativo qualificado=%s novo=%s",
                     sessao["email"], offer, pai_id, novo_id)
        return _json(201, {"novo_id": novo_id, "dados": montar_resposta(offer)})

    classificacao = re.fullmatch(r"/api/offers/([A-Za-z0-9]{1,40})/contatos/(alt\d{1,4})/classificacao", caminho)
    if classificacao:
        corpo = _ler_json()
        if corpo is None:
            return _json(400, {"erro": "Requisição inválida."})
        offer, contato_id = classificacao.groups()
        try:
            texto = validar_classificacao(corpo)
            classificar_alternativo(offer, contato_id, texto)
        except ContatoInvalido as erro_contato:
            return _json(400, {"erro": erro_contato.mensagem, "campo": erro_contato.campo})
        except ErroContato as erro_contato:
            return _json(erro_contato.status, {"erro": erro_contato.mensagem})
        logging.info("AUDITORIA usuario=%s offer=%s acao=classificar_contato_alternativo contato=%s",
                     sessao["email"], offer, contato_id)
        return _json(200, {"dados": montar_resposta(offer)})

    atendimentos = re.fullmatch(r"/api/offers/([A-Za-z0-9]{1,40})/atendimentos", caminho)
    if atendimentos:
        corpo = _ler_json()
        if corpo is None:
            return _json(400, {"erro": "Requisição inválida."})
        offer = atendimentos.group(1)
        contato_id = str(corpo.get("contato_id", ""))[:20]
        try:
            registro = validar_registro(corpo)
            agora = agora_br()
            registro.update({"data": agora.strftime("%Y-%m-%d"), "hora": agora.strftime("%H:%M"),
                             "analista": sessao["nome"], "origem": "dashboard"})
            adicionar_atendimento(offer, contato_id, registro)
        except RegistroInvalido as erro_registro:
            return _json(400, {"erro": erro_registro.mensagem, "campo": erro_registro.campo})
        except ErroContato as erro_contato:
            return _json(erro_contato.status, {"erro": erro_contato.mensagem})
        logging.info("AUDITORIA usuario=%s offer=%s acao=registrar_atendimento contato=%s canal=%s",
                     sessao["email"], offer, contato_id, registro["canal"])
        return _json(201, {"contato_id": contato_id, "dados": montar_resposta(offer)})

    return _json(404, {"erro": "Rota não encontrada"})


@app.route("/", defaults={"caminho": ""}, methods=["GET", "POST"])
@app.route("/<path:caminho>", methods=["GET", "POST"])
def despachar(caminho):
    caminho = "/" + caminho
    if request.method == "GET":
        return _tratar_get(caminho)
    return _tratar_post(caminho)


@app.after_request
def _cabecalhos_de_seguranca(resposta):
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["X-Frame-Options"] = "DENY"
    resposta.headers["Referrer-Policy"] = "same-origin"
    return resposta


@app.errorhandler(armazenamento.ArmazenamentoNaoConfigurado)
def _armazenamento_nao_configurado(erro):
    logging.error("Armazenamento não configurado neste ambiente.")
    return _json(503, {"erro": "O servidor ainda não foi configurado: armazenamento ausente."})


@app.errorhandler(armazenamento.ErroArmazenamento)
def _erro_de_armazenamento(erro):
    logging.error("Erro de armazenamento: %s", erro)
    return _json(503, {"erro": "Armazenamento temporariamente indisponível. Tente novamente em instantes."})


@app.errorhandler(HTTPException)
def _erro_http(erro):
    mensagens = {404: "Rota não encontrada", 405: "Método não permitido.", 413: "Requisição grande demais."}
    return _json(erro.code or 500, {"erro": mensagens.get(erro.code, "Requisição inválida.")})


@app.errorhandler(Exception)
def _erro_inesperado(erro):
    logging.exception("Erro inesperado")
    return _json(500, {"erro": "Erro interno do servidor."})


if __name__ == "__main__":
    print("Dashboard rodando em http://127.0.0.1:8000  (Ctrl+C para encerrar)")
    app.run(host="127.0.0.1", port=8000, debug=False)
