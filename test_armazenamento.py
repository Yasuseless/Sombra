import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import armazenamento

TOKEN_SECRETO = "SEGREDO-NAO-VAZAR-123"


class _Manipulador(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _enviar(self, codigo, texto):
        corpo = texto.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _falha_injetada(self):
        modo = self.server.modo
        if modo == "erro500":
            self._enviar(500, json.dumps({"error": "falha interna simulada"}))
            return True
        if modo == "json_invalido":
            self._enviar(200, "isto nao e json")
            return True
        return False

    def do_GET(self):
        if self._falha_injetada():
            return
        if self.path.startswith("/get/"):
            chave = self.path[len("/get/"):]
            self._enviar(200, json.dumps({"result": self.server.banco.get(chave)}))
        else:
            self._enviar(404, json.dumps({"error": "rota"}))

    def do_POST(self):
        tamanho = int(self.headers.get("Content-Length", "0"))
        corpo = self.rfile.read(tamanho).decode("utf-8")
        if self._falha_injetada():
            return
        if self.path.startswith("/set/"):
            self.server.banco[self.path[len("/set/"):]] = corpo
            self._enviar(200, json.dumps({"result": "OK"}))
            return
        self._enviar(400, json.dumps({"error": "comando desconhecido"}))

    def log_message(self, *args):
        pass


class _ServidorFake(ThreadingHTTPServer):
    request_queue_size = 64
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self):
        super().__init__(("127.0.0.1", 0), _Manipulador)
        self.banco = {}
        self.modo = "normal"
        threading.Thread(target=self.serve_forever, daemon=True).start()

    @property
    def url(self):
        return "http://127.0.0.1:%d" % self.server_address[1]

    def parar(self):
        self.shutdown()
        self.server_close()


class _Base(unittest.TestCase):
    def setUp(self):
        self._orig = (armazenamento._URL, armazenamento._TOKEN,
                      armazenamento.EM_VERCEL, armazenamento._ARQUIVO_LOCAL)

    def tearDown(self):
        (armazenamento._URL, armazenamento._TOKEN,
         armazenamento.EM_VERCEL, armazenamento._ARQUIVO_LOCAL) = self._orig


class TestArmazenamentoLocal(_Base):
    def setUp(self):
        super().setUp()
        self.pasta = tempfile.TemporaryDirectory()
        armazenamento._URL = None
        armazenamento._TOKEN = None
        armazenamento.EM_VERCEL = False
        armazenamento._ARQUIVO_LOCAL = os.path.join(self.pasta.name, "estado.json")

    def tearDown(self):
        self.pasta.cleanup()
        super().tearDown()

    def test_modo_arquivo_local(self):
        self.assertEqual(armazenamento.modo(), "arquivo-local")

    def test_obter_e_definir(self):
        self.assertEqual(armazenamento.obter("a", "padrao"), "padrao")
        armazenamento.definir("a", {"x": 1, "acentuação": "ç"})
        self.assertEqual(armazenamento.obter("a"), {"x": 1, "acentuação": "ç"})


class TestProducaoSemConfiguracao(_Base):
    def test_vercel_sem_upstash_falha_explicitamente(self):
        armazenamento._URL = None
        armazenamento._TOKEN = None
        armazenamento.EM_VERCEL = True
        self.assertEqual(armazenamento.modo(), "nao-configurado")
        with self.assertRaises(armazenamento.ArmazenamentoNaoConfigurado):
            armazenamento.obter("x")
        with self.assertRaises(armazenamento.ArmazenamentoNaoConfigurado):
            armazenamento.definir("x", 1)

    def test_vercel_com_configuracao_incompleta_falha(self):
        armazenamento._URL = "http://127.0.0.1:1"
        armazenamento._TOKEN = None
        armazenamento.EM_VERCEL = True
        with self.assertRaises(armazenamento.ArmazenamentoNaoConfigurado):
            armazenamento.obter("x")

    def test_nomes_alternativos_das_variaveis_do_upstash(self):
        codigo = "import armazenamento; print(armazenamento.modo())"
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("KV_", "UPSTASH_", "VERCEL"))}
        env["UPSTASH_REDIS_REST_URL"] = "http://127.0.0.1:1"
        env["UPSTASH_REDIS_REST_TOKEN"] = "t"
        saida = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, env=env,
                               capture_output=True, text=True, timeout=30)
        self.assertEqual(saida.stdout.strip(), "upstash", saida.stderr)


class TestUpstashSimulado(_Base):
    def setUp(self):
        super().setUp()
        self.servidor = _ServidorFake()
        armazenamento._URL = self.servidor.url
        armazenamento._TOKEN = TOKEN_SECRETO
        armazenamento.EM_VERCEL = True

    def tearDown(self):
        self.servidor.parar()
        super().tearDown()

    def test_modo_upstash(self):
        self.assertEqual(armazenamento.modo(), "upstash")

    def test_obter_e_definir(self):
        armazenamento.definir("k", {"a": [1, 2]})
        self.assertEqual(armazenamento.obter("k"), {"a": [1, 2]})
        self.assertEqual(armazenamento.obter("inexistente", "p"), "p")

    def test_chave_com_caracteres_especiais_e_codificada(self):
        armazenamento.definir("chave com espaço/x", 1)
        self.assertEqual(list(self.servidor.banco), ["chave%20com%20espa%C3%A7o%2Fx"])
        self.assertEqual(armazenamento.obter("chave com espaço/x"), 1)

    def test_http_500_vira_erro_de_armazenamento_sem_vazar_token(self):
        self.servidor.modo = "erro500"
        with self.assertRaises(armazenamento.ErroArmazenamento) as ctx:
            armazenamento.obter("k")
        self.assertNotIn(TOKEN_SECRETO, str(ctx.exception))

    def test_resposta_que_nao_e_json_vira_erro_de_armazenamento(self):
        self.servidor.modo = "json_invalido"
        with self.assertRaises(armazenamento.ErroArmazenamento):
            armazenamento.obter("k")

    def test_valor_armazenado_corrompido_vira_erro_de_armazenamento(self):
        self.servidor.banco["k"] = "isto nao e json"
        with self.assertRaises(armazenamento.ErroArmazenamento):
            armazenamento.obter("k")

    def test_servidor_inalcancavel_vira_erro_sem_vazar_token(self):
        armazenamento._URL = "http://127.0.0.1:1"
        with self.assertRaises(armazenamento.ErroArmazenamento) as ctx:
            armazenamento.obter("k")
        self.assertNotIn(TOKEN_SECRETO, str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
