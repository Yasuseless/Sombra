import json
import logging
import re
from datetime import date, datetime
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

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

PASTA = Path(__file__).parent

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")

def montar_resposta(offer: str):
    dados = buscar_offer(offer)
    if dados is None:
        return None
    hoje = date.today()
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

class Handler(BaseHTTPRequestHandler):

    def _enviar(self, status: int, corpo: bytes, tipo: str, cabecalhos=None):
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        for nome, valor in (cabecalhos or []):
            self.send_header(nome, valor)
        self.end_headers()
        self.wfile.write(corpo)

    def _json(self, status: int, dados: dict, cabecalhos=None):
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self._enviar(status, corpo, "application/json; charset=utf-8", cabecalhos)

    def log_message(self, formato, *args):

        linha = self.requestline.split("?")[0]
        logging.info('%s "%s" %s', self.address_string(), linha, args[1] if len(args) > 1 else "")

    def _token(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except CookieError:
            return None
        item = cookie.get("sessao")
        return item.value if item else None

    def _exigir_login(self):

        sessao = obter_sessao(self._token())
        if sessao is None:
            self._json(401, {"erro": "Sessão expirada. Entre novamente."})
        return sessao

    def _exigir_supervisor(self):
        sessao = self._exigir_login()
        if sessao is None:
            return None
        if sessao.get("papel") != "supervisor":
            self._json(403, {"erro": "Acesso restrito a supervisores."})
            return None
        return sessao

    def _origem_confiavel(self) -> bool:

        origem = self.headers.get("Origin")
        return origem is None or origem == "http://" + str(self.headers.get("Host", ""))

    def _ler_json(self):

        try:
            tamanho = int(self.headers.get("Content-Length", "0"))
            if not 0 < tamanho <= 8192:
                raise ValueError("tamanho inválido")
            corpo = json.loads(self.rfile.read(tamanho).decode("utf-8"))
            if not isinstance(corpo, dict):
                raise ValueError("corpo inválido")
            return corpo
        except (ValueError, UnicodeDecodeError):
            self._json(400, {"erro": "Requisição inválida."})
            return None

    def do_GET(self):
        caminho = unquote(urlsplit(self.path).path)

        if caminho in ("/", "/index.html"):
            arquivo = PASTA / "index.html"
            if not arquivo.exists():
                self._enviar(500, "Arquivo index.html não encontrado na pasta do app.py.".encode("utf-8"),
                             "text/plain; charset=utf-8")
                return
            self._enviar(200, arquivo.read_bytes(), "text/html; charset=utf-8")
            return

        if caminho == "/api/sessao":
            sessao = obter_sessao(self._token())
            if sessao:
                self._json(200, {"logado": True, "nome": sessao["nome"], "email": sessao["email"],
                                 "papel": sessao["papel"]})
            else:
                self._json(200, {"logado": False})
            return

        if caminho == "/api/meus-atendimentos":
            sessao = self._exigir_login()
            if sessao is None:
                return
            itens = atendimentos_do_analista(sessao["nome"])
            self._json(200, {"atendimentos": itens})
            return

        if caminho == "/api/supervisor/analistas":
            sessao = self._exigir_supervisor()
            if sessao is None:
                return
            self._json(200, {"analistas": resumo_por_analista()})
            return

        if caminho == "/api/supervisor/grafico":
            sessao = self._exigir_supervisor()
            if sessao is None:
                return
            parametros = parse_qs(urlsplit(self.path).query)
            tema = parametros.get("tema", [""])[0][:60]
            inicio = parametros.get("inicio", [""])[0][:10]
            fim = parametros.get("fim", [""])[0][:10]
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", inicio):
                inicio = None
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fim):
                fim = None
            self._json(200, volumetria(tema or None, inicio, fim))
            return

        if caminho == "/api/supervisor/atendimentos":
            sessao = self._exigir_supervisor()
            if sessao is None:
                return
            parametros = parse_qs(urlsplit(self.path).query)
            nome = parametros.get("analista", [""])[0][:60]
            self._json(200, {"analista": nome, "atendimentos": atendimentos_do_analista(nome)})
            return

        correspondencia = re.fullmatch(r"/api/offers/([A-Za-z0-9]{1,40})", caminho)
        if correspondencia:
            sessao = self._exigir_login()
            if sessao is None:
                return
            offer = correspondencia.group(1)
            dados = montar_resposta(offer)
            logging.info("AUDITORIA usuario=%s offer=%s encontrada=%s", sessao["email"], offer, dados is not None)
            if dados is None:
                self._json(404, {"erro": "Offer não encontrada"})
            else:
                self._json(200, dados)
            return

        self._json(404, {"erro": "Rota não encontrada"})

    def do_POST(self):
        caminho = urlsplit(self.path).path
        if not self._origem_confiavel():
            self._json(403, {"erro": "Origem não permitida."})
            return

        if caminho == "/api/login":
            corpo = self._ler_json()
            if corpo is None:
                return
            try:
                token = autenticar(corpo.get("email"), corpo.get("senha"))
            except BloqueioTemporario:
                logging.info("AUDITORIA login bloqueado por excesso de tentativas")
                self._json(429, {"erro": "Muitas tentativas. Aguarde alguns minutos e tente de novo."})
                return
            except CredenciaisInvalidas:
                logging.info("AUDITORIA login recusado")
                self._json(401, {"erro": "E-mail ou senha incorretos."})
                return
            sessao = obter_sessao(token)
            logging.info("AUDITORIA login usuario=%s", sessao["email"])
            cookie = f"sessao={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={DURACAO_SESSAO}"
            self._json(200, {"nome": sessao["nome"], "email": sessao["email"], "papel": sessao["papel"]},
                       [("Set-Cookie", cookie)])
            return

        if caminho == "/api/logout":
            token = self._token()
            sessao = obter_sessao(token)
            if sessao:
                logging.info("AUDITORIA logout usuario=%s", sessao["email"])
            encerrar_sessao(token)
            self._json(200, {"ok": True}, [("Set-Cookie", "sessao=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")])
            return

        sessao = self._exigir_login()
        if sessao is None:
            return

        if caminho == "/api/busca":
            corpo = self._ler_json()
            if corpo is None:
                return
            consulta = str(corpo.get("q", ""))[:80]
            try:
                tipo, resultados = buscar(consulta)
            except BuscaInvalida as erro:
                self._json(400, {"erro": str(erro)})
                return

            termo = consulta if tipo in ("offer", "imovel") else "[protegido]"
            logging.info("AUDITORIA usuario=%s busca=%s termo=%s resultados=%d",
                         sessao["email"], tipo, termo, len(resultados))
            self._json(200, {"tipo": tipo, "resultados": resultados})
            return

        alternativos = re.fullmatch(r"/api/offers/([A-Za-z0-9]{1,40})/alternativos", caminho)
        if alternativos:
            corpo = self._ler_json()
            if corpo is None:
                return
            offer = alternativos.group(1)
            pai_id = str(corpo.get("pai_id", ""))[:20]
            try:
                novo = validar_novo_contato(corpo)
                novo_id = adicionar_alternativo(offer, pai_id, novo)
            except ContatoInvalido as erro:
                self._json(400, {"erro": erro.mensagem, "campo": erro.campo})
                return
            except ErroContato as erro:
                self._json(erro.status, {"erro": erro.mensagem})
                return
            logging.info("AUDITORIA usuario=%s offer=%s acao=adicionar_contato_alternativo qualificado=%s novo=%s",
                         sessao["email"], offer, pai_id, novo_id)
            self._json(201, {"novo_id": novo_id, "dados": montar_resposta(offer)})
            return

        atendimentos = re.fullmatch(r"/api/offers/([A-Za-z0-9]{1,40})/atendimentos", caminho)
        if atendimentos:
            corpo = self._ler_json()
            if corpo is None:
                return
            offer = atendimentos.group(1)
            contato_id = str(corpo.get("contato_id", ""))[:20]
            try:
                registro = validar_registro(corpo)
                agora = datetime.now()
                registro.update({"data": agora.strftime("%Y-%m-%d"), "hora": agora.strftime("%H:%M"),
                                 "analista": sessao["nome"], "origem": "dashboard"})
                adicionar_atendimento(offer, contato_id, registro)
            except RegistroInvalido as erro:
                self._json(400, {"erro": erro.mensagem, "campo": erro.campo})
                return
            except ErroContato as erro:
                self._json(erro.status, {"erro": erro.mensagem})
                return

            logging.info("AUDITORIA usuario=%s offer=%s acao=registrar_atendimento contato=%s canal=%s",
                         sessao["email"], offer, contato_id, registro["canal"])
            self._json(201, {"contato_id": contato_id, "dados": montar_resposta(offer)})
            return

        classificacao = re.fullmatch(r"/api/offers/([A-Za-z0-9]{1,40})/contatos/(alt\d{1,4})/classificacao", caminho)
        if classificacao:
            corpo = self._ler_json()
            if corpo is None:
                return
            offer, contato_id = classificacao.groups()
            try:
                texto = validar_classificacao(corpo)
                classificar_alternativo(offer, contato_id, texto)
            except ContatoInvalido as erro:
                self._json(400, {"erro": erro.mensagem, "campo": erro.campo})
                return
            except ErroContato as erro:
                self._json(erro.status, {"erro": erro.mensagem})
                return
            logging.info("AUDITORIA usuario=%s offer=%s acao=reclassificar_contato contato=%s",
                         sessao["email"], offer, contato_id)
            self._json(200, {"dados": montar_resposta(offer)})
            return

        self._json(404, {"erro": "Rota não encontrada"})

if __name__ == "__main__":
    servidor = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    print("Dashboard rodando em http://127.0.0.1:8000  (Ctrl+C para encerrar)")
    servidor.serve_forever()
