import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request

EM_VERCEL = bool(os.environ.get("VERCEL"))

_URL = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
_TOKEN = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")
_ARQUIVO_LOCAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "estado_local.json")
_TRAVA = threading.Lock()


class ErroArmazenamento(Exception):
    pass


class ArmazenamentoNaoConfigurado(ErroArmazenamento):
    pass


def _usa_upstash():
    return bool(_URL and _TOKEN)


def modo():
    if _usa_upstash():
        return "upstash"
    if EM_VERCEL:
        return "nao-configurado"
    return "arquivo-local"


def _exigir_configuracao():
    if EM_VERCEL and not _usa_upstash():
        raise ArmazenamentoNaoConfigurado(
            "Credenciais do Upstash ausentes neste ambiente."
        )


def _requisitar(caminho, corpo=None):
    url = _URL.rstrip("/") + caminho
    dados = None
    metodo = "GET"
    if corpo is not None:
        dados = corpo.encode("utf-8")
        metodo = "POST"
    req = urllib.request.Request(
        url, data=dados, method=metodo,
        headers={"Authorization": "Bearer " + _TOKEN},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as erro:
        raise ErroArmazenamento("Falha HTTP " + str(erro.code) + " ao acessar o armazenamento.")
    except urllib.error.URLError:
        raise ErroArmazenamento("Não foi possível conectar ao armazenamento externo.")
    except (TimeoutError, ConnectionError):
        raise ErroArmazenamento("Tempo esgotado ao acessar o armazenamento externo.")
    except ValueError:
        raise ErroArmazenamento("Resposta inesperada do armazenamento externo.")


def _ler_arquivo_local():
    if not os.path.exists(_ARQUIVO_LOCAL):
        return {}
    with open(_ARQUIVO_LOCAL, "r", encoding="utf-8") as f:
        conteudo = f.read().strip()
        return json.loads(conteudo) if conteudo else {}


def obter(chave, padrao=None):
    _exigir_configuracao()
    if _usa_upstash():
        resultado = _requisitar("/get/" + urllib.parse.quote(chave, safe=""))
        if not isinstance(resultado, dict):
            raise ErroArmazenamento("Resposta inesperada do armazenamento externo.")
        valor = resultado.get("result")
        if valor is None:
            return padrao
        try:
            return json.loads(valor)
        except (TypeError, ValueError):
            raise ErroArmazenamento("Valor armazenado inválido.")
    with _TRAVA:
        tudo = _ler_arquivo_local()
        return tudo.get(chave, padrao)


def definir(chave, valor):
    _exigir_configuracao()
    if _usa_upstash():
        _requisitar("/set/" + urllib.parse.quote(chave, safe=""),
                    corpo=json.dumps(valor, ensure_ascii=False))
        return
    with _TRAVA:
        tudo = _ler_arquivo_local()
        tudo[chave] = valor
        with open(_ARQUIVO_LOCAL, "w", encoding="utf-8") as f:
            json.dump(tudo, f, ensure_ascii=False)
