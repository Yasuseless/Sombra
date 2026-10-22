import hashlib
import hmac
import secrets
import threading
import time

EMAIL_DEMO = "matrix@webhelpbr.com.br"
SENHA_DEMO = "Neo@2026"
NOME_DEMO = "Analista Demonstração"

EMAIL_SUPERVISOR = "supervisor@webhelpbr.com.br"
SENHA_SUPERVISOR = "Supervisor@2026"
NOME_SUPERVISOR = "Supervisor Demonstração"

ITERACOES = 120_000
DURACAO_SESSAO = 8 * 3600
MAX_FALHAS = 5
JANELA_BLOQUEIO = 300

_TRAVA = threading.Lock()
_SESSOES: dict = {}
_FALHAS: dict = {}
_SAL_FALSO = secrets.token_bytes(16)

class CredenciaisInvalidas(Exception):
    pass

class BloqueioTemporario(Exception):
    pass

def _hash(senha: str, sal: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), sal, ITERACOES)

_SAL_DEMO = secrets.token_bytes(16)
_SAL_SUPERVISOR = secrets.token_bytes(16)
USUARIOS = {
    EMAIL_DEMO: {"nome": NOME_DEMO, "papel": "analista", "sal": _SAL_DEMO, "hash": _hash(SENHA_DEMO, _SAL_DEMO)},
    EMAIL_SUPERVISOR: {"nome": NOME_SUPERVISOR, "papel": "supervisor", "sal": _SAL_SUPERVISOR,
                       "hash": _hash(SENHA_SUPERVISOR, _SAL_SUPERVISOR)},
}

def autenticar(email: str, senha: str) -> str:
    email = str(email or "").strip().lower()[:120]
    senha = str(senha or "")[:200]
    agora = time.time()

    with _TRAVA:
        recentes = [t for t in _FALHAS.get(email, []) if agora - t < JANELA_BLOQUEIO]
        _FALHAS[email] = recentes
        if len(recentes) >= MAX_FALHAS:
            raise BloqueioTemporario()

    usuario = USUARIOS.get(email)

    calculado = _hash(senha, usuario["sal"] if usuario else _SAL_FALSO)
    if usuario is None or not hmac.compare_digest(calculado, usuario["hash"]):
        with _TRAVA:
            _FALHAS.setdefault(email, []).append(agora)
        raise CredenciaisInvalidas()

    with _TRAVA:
        _FALHAS.pop(email, None)
        token = secrets.token_urlsafe(32)
        _SESSOES[token] = {"email": email, "nome": usuario["nome"], "papel": usuario["papel"],
                           "expira": agora + DURACAO_SESSAO}
    return token

def obter_sessao(token):
    if not token:
        return None
    with _TRAVA:
        sessao = _SESSOES.get(token)
        if sessao and sessao["expira"] < time.time():
            _SESSOES.pop(token, None)
            return None
        return dict(sessao) if sessao else None

def encerrar_sessao(token):
    with _TRAVA:
        _SESSOES.pop(token, None)
