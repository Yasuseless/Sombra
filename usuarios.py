import hashlib
import hmac
import os
import secrets
import time

from armazenamento import definir, obter

EM_VERCEL = bool(os.environ.get("VERCEL"))

NOME_DEMO = "Analista Demonstração"
NOME_SUPERVISOR = "Supervisor Demonstração"

ITERACOES = 120_000
DURACAO_SESSAO = 8 * 3600
MAX_FALHAS = 5
JANELA_BLOQUEIO = 300
TAMANHO_MINIMO_SENHA = 8

_PADROES_LOCAIS = {
    "SOMBRA_ANALISTA_EMAIL": "matrix@webhelpbr.com.br",
    "SOMBRA_ANALISTA_SENHA": "Neo@2026",
    "SOMBRA_SUPERVISOR_EMAIL": "supervisor@webhelpbr.com.br",
    "SOMBRA_SUPERVISOR_SENHA": "Supervisor@2026",
}

_SAL_FALSO = secrets.token_bytes(16)


class CredenciaisInvalidas(Exception):
    pass


class BloqueioTemporario(Exception):
    pass


def _variavel(nome):
    valor = (os.environ.get(nome) or "").strip()
    if valor:
        return valor
    return None if EM_VERCEL else _PADROES_LOCAIS[nome]


def _hash(senha: str, sal: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), sal, ITERACOES)


USUARIOS = {}


def _registrar(var_email, var_senha, nome, papel):
    email = _variavel(var_email)
    senha = _variavel(var_senha)
    if not email or not senha or len(senha) < TAMANHO_MINIMO_SENHA:
        return False
    sal = secrets.token_bytes(16)
    USUARIOS[email.lower()] = {"nome": nome, "papel": papel, "sal": sal, "hash": _hash(senha, sal)}
    return True


ANALISTA_CONFIGURADO = _registrar("SOMBRA_ANALISTA_EMAIL", "SOMBRA_ANALISTA_SENHA", NOME_DEMO, "analista")
SUPERVISOR_CONFIGURADO = _registrar("SOMBRA_SUPERVISOR_EMAIL", "SOMBRA_SUPERVISOR_SENHA", NOME_SUPERVISOR, "supervisor")


def _carregar_sessoes():
    return obter("sessoes", {})


def _salvar_sessoes(sessoes):
    definir("sessoes", sessoes)


def _carregar_falhas():
    return obter("falhas_login", {})


def _salvar_falhas(falhas):
    definir("falhas_login", falhas)


def autenticar(email: str, senha: str) -> str:
    email = str(email or "").strip().lower()[:120]
    senha = str(senha or "")[:200]
    agora = time.time()

    falhas = _carregar_falhas()
    recentes = [t for t in falhas.get(email, []) if agora - t < JANELA_BLOQUEIO]
    falhas[email] = recentes
    if len(recentes) >= MAX_FALHAS:
        _salvar_falhas(falhas)
        raise BloqueioTemporario()

    usuario = USUARIOS.get(email)
    calculado = _hash(senha, usuario["sal"] if usuario else _SAL_FALSO)
    if usuario is None or not hmac.compare_digest(calculado, usuario["hash"]):
        falhas.setdefault(email, []).append(agora)
        _salvar_falhas(falhas)
        raise CredenciaisInvalidas()

    falhas.pop(email, None)
    _salvar_falhas(falhas)

    token = secrets.token_urlsafe(32)
    sessoes = _carregar_sessoes()
    sessoes = {t: s for t, s in sessoes.items() if s.get("expira", 0) >= agora}
    sessoes[token] = {"email": email, "nome": usuario["nome"], "papel": usuario["papel"],
                      "expira": agora + DURACAO_SESSAO}
    _salvar_sessoes(sessoes)
    return token


def obter_sessao(token):
    if not token:
        return None
    sessoes = _carregar_sessoes()
    sessao = sessoes.get(token)
    if sessao and sessao["expira"] < time.time():
        sessoes.pop(token, None)
        _salvar_sessoes(sessoes)
        return None
    return dict(sessao) if sessao else None


def encerrar_sessao(token):
    if not token:
        return
    sessoes = _carregar_sessoes()
    if token in sessoes:
        sessoes.pop(token, None)
        _salvar_sessoes(sessoes)
