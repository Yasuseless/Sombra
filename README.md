# Sombra

**Dashboard de consulta, gestão e acompanhamento de atendimentos.**

O Sombra é uma aplicação web desenvolvida para centralizar consultas de ofertas, informações de contato e registros de atendimento em uma interface única, com recursos de acompanhamento e supervisão.

O projeto simula um ambiente operacional de atendimento, permitindo explorar fluxos de consulta, registro e análise de informações.

> **Aviso:** O Sombra é um projeto de demonstração. Todos os dados utilizados são fictícios e não há integração com bases reais de clientes ou com o Salesforce.

---

## Funcionalidades

- **Consulta de ofertas:** pesquisa e visualização de ofertas simuladas.
- **Informações de contato:** consulta de contatos e alternativas de contato.
- **Registro de atendimentos:** inclusão e acompanhamento do histórico de interações.
- **Painel de supervisão:** visualização de indicadores e informações operacionais.
- **Controle de acesso:** autenticação com perfis de analista e supervisor.
- **Proteção de informações:** mascaramento de dados sensíveis, como CPF, telefone e e-mail.

## Tecnologias

| Tecnologia | Aplicação |
|---|---|
| Python | Linguagem principal |
| Flask | Aplicação web e rotas |
| Upstash Redis | Persistência de dados na Vercel |
| HTML | Interface da aplicação |
| unittest | Testes automatizados |

## Estrutura do projeto

```text
Sombra/
├── app.py
├── index.html
├── armazenamento.py
├── usuarios.py
├── salesforce_simulado.py
├── analistas.py
├── busca.py
├── contatos_alternativos.py
├── mascaramento.py
├── registros.py
├── supervisor.py
├── requirements.txt
└── testes/
```

## Execução local

**Requisitos:** Python 3.12 ou superior.

Clone o repositório:

```bash
git clone https://github.com/Yasuseless/Sombra.git
cd Sombra
```

Instale as dependências:

```bash
py -m pip install -r requirements.txt
```

Inicie a aplicação:

```bash
py app.py
```

Acesse:

```text
http://127.0.0.1:8000
```

Na execução local, os dados são armazenados em `estado_local.json`, arquivo gerado automaticamente e não versionado no Git.

## Configuração

Na Vercel, a aplicação utiliza variáveis de ambiente para autenticação e persistência.

| Variável | Finalidade |
|---|---|
| `SOMBRA_ANALISTA_EMAIL` | E-mail do perfil de analista |
| `SOMBRA_ANALISTA_SENHA` | Senha do perfil de analista |
| `SOMBRA_SUPERVISOR_EMAIL` | E-mail do perfil de supervisor |
| `SOMBRA_SUPERVISOR_SENHA` | Senha do perfil de supervisor |
| `KV_REST_API_URL` | Endereço do armazenamento Upstash |
| `KV_REST_API_TOKEN` | Token de acesso ao Upstash |

Também são aceitos os nomes alternativos `UPSTASH_REDIS_REST_URL` e `UPSTASH_REDIS_REST_TOKEN`.

As credenciais devem ser configuradas diretamente no painel da Vercel. Utilize senhas novas e exclusivas para a demonstração. Não armazene credenciais reais no repositório.

## Testes

O projeto possui uma suíte de testes automatizados utilizando `unittest`.

Para executar:

```bash
py -m unittest discover -s testes -t .
```

Os testes cobrem fluxos da aplicação, autenticação, permissões, consultas, registros, persistência e tratamento de falhas.

**Observação:** os testes locais utilizam armazenamento simulado e não substituem a validação da integração com um banco Upstash real ou de um deploy na Vercel.

## Deploy

A aplicação foi preparada para execução na Vercel, utilizando Flask como ponto de entrada.

O processo de publicação envolve:

1. Importar o repositório na Vercel.
2. Configurar o armazenamento Upstash Redis.
3. Cadastrar as variáveis de ambiente necessárias.
4. Configurar a branch `vercel` como branch de produção, conforme a estratégia de publicação do projeto.
5. Realizar o deploy e validar autenticação, persistência e funcionalidades principais.

Após a publicação, a aplicação pode ser acessada pelo domínio de produção configurado na Vercel.

## Limitações

O Sombra foi desenvolvido com foco em demonstração e validação de fluxos operacionais. Portanto, algumas limitações são conhecidas:

- Utiliza dados fictícios e uma integração simulada com o Salesforce.
- Possui contas de demonstração predefinidas, sem cadastro de usuários ou recuperação de senha.
- Foi projetado para utilização por um testador por vez; gravações simultâneas podem causar sobrescrita de dados.
- A identificação de informações sensíveis em textos depende de verificações simples e não substitui revisão humana.
- Os horários dos registros utilizam o fuso de Brasília (UTC-3).
- A integração real com Upstash e o comportamento em produção na Vercel ainda precisam de validação no ambiente publicado.

---

**Sombra** — Demonstração de uma experiência integrada de consulta, registro e acompanhamento operacional.
