Sombra — dashboard de demonstração

Dashboard de consulta e registro de atendimentos (Offers, contatos, histórico) com painel de supervisão. Todos os dados são fictícios. Este projeto é uma demonstração para validação da ideia, não um sistema de produção.

Como o projeto está organizado
Arquivo	Para que serve
app.py	Servidor (Flask). É o ponto de entrada local e da Vercel
index.html	Tela do dashboard
armazenamento.py	Guarda os dados: Upstash (Redis) na Vercel, arquivo local no seu computador
usuarios.py	Login, sessões e bloqueio por tentativas
salesforce_simulado.py	Dados fictícios (simulam o Salesforce)
busca.py, registros.py, contatos_alternativos.py, analistas.py, supervisor.py, mascaramento.py	Regras de busca, validação e indicadores
requirements.txt	Dependências (apenas Flask)
testes/	Testes automatizados
Variáveis de ambiente
Variável	Obrigatória?	Descrição
SOMBRA_ANALISTA_EMAIL	Sim, na Vercel	E-mail da conta de analista da demonstração
SOMBRA_ANALISTA_SENHA	Sim, na Vercel	Senha dessa conta (mínimo de 8 caracteres)
SOMBRA_SUPERVISOR_EMAIL	Sim, na Vercel	E-mail da conta de supervisor
SOMBRA_SUPERVISOR_SENHA	Sim, na Vercel	Senha dessa conta (mínimo de 8 caracteres)
KV_REST_API_URL e KV_REST_API_TOKEN	Sim, na Vercel	Criadas automaticamente pela integração do Upstash. O app também aceita os nomes UPSTASH_REDIS_REST_URL e UPSTASH_REDIS_REST_TOKEN
VERCEL	Não configure	A própria Vercel define. É ela que faz o app exigir as variáveis acima

Regras importantes:

Use e-mails e senhas NOVOS. As credenciais de teste das versões anteriores passaram por conversas e por código e devem ser consideradas expostas.
Na Vercel, se alguma variável obrigatória faltar, o app não usa valores padrão: a conta correspondente fica desativada e /api/saude avisa.
No seu computador (sem VERCEL), o app usa contas de desenvolvimento definidas em usuarios.py. Elas só valem localmente.
O arquivo .env.example só lista os nomes. O app não lê arquivo .env: configure as variáveis no painel da Vercel.
Rodar no seu computador
Tenha o Python 3.12 ou mais novo instalado.
Na pasta do projeto: py -m pip install -r requirements.txt
Inicie: py app.py
Abra http://127.0.0.1:8000

Localmente os dados ficam no arquivo estado_local.json (não vai para o GitHub). Apague-o para voltar aos dados originais.

Testes

Na pasta do projeto: py -m unittest discover -s testes -t .

Rode no seu computador, sem a variável VERCEL definida. Os testes usam armazenamento local e um Upstash simulado; eles não provam que a integração com o seu Upstash real funciona. Para isso use o passo 6 abaixo.

Publicar na Vercel
Prepare a branch vercel com estes arquivos. Apague do repositório os arquivos da versão anterior: api/index.py, vercel.json e manipulador.py.
Importe o projeto: na Vercel, "Add New" → "Project" → escolha o repositório. A Vercel reconhece o Flask pelo requirements.txt e usa o app.py na raiz. Não precisa de vercel.json.
Torne a vercel a branch de produção (Settings → Git → Production Branch). Motivo: deploys de outras branches viram "Preview" e a Vercel, por padrão, exige login de um usuário da Vercel para abri-los. O domínio de produção é público. (O nome do menu pode variar um pouco; a ideia é a mesma.)
Conecte o Redis: no projeto, aba "Storage" (ou Marketplace) → "Upstash for Redis" → crie um banco (o plano gratuito basta) e conecte ao projeto para o ambiente Production. Em Settings → Environment Variables, confira os nomes criados (KV_REST_API_* ou UPSTASH_REDIS_REST_*).
Cadastre as 4 variáveis SOMBRA_* (Settings → Environment Variables, ambiente Production). Depois faça um novo deploy ("Redeploy"), porque variáveis novas só valem em deploys novos.
Valide em 2 minutos:
Abra https://SEU-DOMINIO/api/saude. Deve aparecer "ok": true, "armazenamento": "upstash" e "armazenamento_acessivel": true.
Abra https://SEU-DOMINIO/, entre como analista, abra uma Offer, registre um atendimento, saia e entre de novo: o registro deve continuar lá.
Entre como supervisor e abra o painel e o gráfico.
Envie ao coordenador o domínio de produção (o curto), não os endereços longos gerados a cada deploy.
Se algo não funcionar
Sintoma	Causa provável
/api/saude mostra "armazenamento": "nao-configurado"	O Redis não está conectado ao ambiente Production, ou falta novo deploy
/api/saude mostra credenciais false	Falta variável SOMBRA_*, ou a senha tem menos de 8 caracteres
Login responde "E-mail ou senha incorretos"	E-mail/senha diferentes dos cadastrados na Vercel
Pede login da Vercel ao abrir o link	Você está abrindo um deploy Preview ou o endereço longo; use o domínio de produção
Mensagem "Armazenamento temporariamente indisponível"	Falha de comunicação com o Upstash; veja os logs do deploy na Vercel
Limitações conhecidas
Dados fictícios e Salesforce simulado: nada aqui lê dados reais de clientes.
Pensado para um testador por vez. Se duas pessoas gravarem ao mesmo tempo, uma alteração pode sobrescrever a outra (o app lê e regrava os dados inteiros).
Dois logins fixos de demonstração; não há cadastro de usuários nem recuperação de senha.
Proteção contra CSRF baseada em cookie SameSite=Strict e na verificação de Origin; não há token CSRF dedicado.
A proteção contra CPF e números sensíveis no texto dos atendimentos é uma verificação simples e não substitui revisão humana.
Os horários dos registros usam o fuso de Brasília (UTC-3, fixo).
Não foi testado em um deploy real na Vercel nem contra um Upstash real por quem montou este pacote.
