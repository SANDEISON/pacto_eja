# Pacto EJA

Sistema web do Programa de Formação de Educadores do Pacto EJA. A aplicação reúne cadastro de educadores, perfil acadêmico e profissional, vínculos com escolas, atividades, inscrições, submissão de trabalhos e avaliação acadêmica.

O projeto é uma aplicação Django renderizada no servidor. O PostgreSQL armazena os dados, o Django AdminLTE fornece a interface autenticada e o WhiteNoise entrega os arquivos estáticos em produção.

## Funcionalidades

- cadastro público de educadores com consulta de CPF;
- endereço, formações acadêmicas e múltiplos vínculos com escolas;
- autenticação por CPF usando o sistema de usuários do Django;
- recuperação de acesso por CPF, com senha temporária enviada ao e-mail cadastrado;
- painel do educador com atividades disponíveis e inscrições realizadas;
- inscrição em eventos, palestras e cursos, com salvamento automático de rascunho;
- escolha de modalidade, programação de sala e refeições disponíveis;
- submissão de trabalho com PDF e coautores cadastrados na plataforma;
- modelos de submissão configuráveis por atividade: trabalho acadêmico (eixo, resumo e
  palavras-chave) ou relato de experiência (público, período, objetivos, metodologia,
  resultados, referências e evidências);
- aceite versionado dos termos de publicação, imagem e direitos autorais;
- chamadas públicas, seleção de avaliadores, distribuição de trabalhos e pareceres;
- gestão de atividades, salas, programações, refeições, inscrições, educadores e catálogos;
- controle de acesso pelas permissões nativas do Django.

## Tecnologias e requisitos

- Python 3.12 ou superior;
- Django 6;
- PostgreSQL;
- JavaScript e CSS sem etapa de compilação;
- Gunicorn e systemd na implantação Linux.

As versões exatas dos pacotes Python estão em `requirements.txt`.

## Como o projeto está organizado

```text
accounts/       login, logout e criação de contas
core/
  admin/        configuração do Django Admin
  forms/        formulários e validações de entrada
  migrations/   estrutura e carga inicial do banco
  models/       entidades do domínio
  views/        páginas, APIs internas e fluxos da aplicação
deploy/         arquivos de exemplo para systemd e produção
pacto_eja/      configurações, URLs raiz, ASGI e WSGI
static/         CSS, JavaScript e imagens autorais
  docs/         termos em PDF exibidos durante a submissão
templates/      páginas e componentes HTML
scripts/        utilitários executados manualmente por desenvolvedores
```

Os models são separados por assunto e exportados por `core.models`. O mesmo padrão é usado em `core.forms` e `core.views`, permitindo imports curtos sem concentrar toda a implementação em um único arquivo.

### Fluxos principais

1. O cadastro público cria uma conta cujo `username` é o CPF sem máscara e cria o perfil `Educador` associado.
2. O usuário entra por `/conta/entrar/` e acessa o painel em `/painel/`.
3. Uma atividade ativa aparece quando o período de inscrição está aberto ou quando o usuário já está inscrito.
4. Durante a inscrição, o usuário informa a modalidade, escolhe programações compatíveis e, quando presencial, as refeições desejadas. Um rascunho permite retomar o preenchimento.
5. A confirmação atualiza os dados pessoais e cria uma única inscrição por usuário e atividade.
6. Quando permitido, o usuário escolhe entre trabalho acadêmico e relato de experiência, aceita os termos vigentes e envia um PDF de até 10 MB. Relatos também registram municípios e até duas evidências em JPG ou PNG.
7. Em uma chamada de avaliadores, o usuário envia sua candidatura e a coordenação decide pela aprovação ou rejeição.
8. A coordenação distribui trabalhos somente a avaliadores aprovados. O avaliador pode salvar o parecer como rascunho e concluí-lo até o prazo definido.

### Relações principais do domínio

- `Atividade` concentra período, modalidade, vagas e configuração da submissão;
- `ProgramacaoSala` associa sala, temática, turno e modalidade; uma atividade oferece uma ou mais programações;
- `Inscricao` liga usuário e atividade e registra modalidade, programações e refeições escolhidas;
- `Trabalho` pertence a uma inscrição e reúne arquivo, autoria, metadados e aceite dos termos;
- `ChamadaAvaliadores` recebe candidaturas para uma atividade;
- `DesignacaoAvaliacao` libera um trabalho para um avaliador aprovado;
- `Avaliacao` guarda notas, recomendação e parecer da designação.

## Executar localmente

### 1. Criar o ambiente virtual

No Windows/PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

No Linux/macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Criar e configurar o PostgreSQL

Com o serviço PostgreSQL em execução, crie o banco:

```sql
CREATE DATABASE db_pacto_eja;
```

Copie o arquivo de configuração:

```powershell
Copy-Item .env.example .env
```

No Linux/macOS, use `cp .env.example .env`. Depois ajuste no `.env`, pelo menos, `POSTGRES_USER` e `POSTGRES_PASSWORD`.

| Variável | Finalidade | Exemplo local |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | assinatura criptográfica do Django | chave aleatória |
| `DJANGO_DEBUG` | ativa mensagens de depuração | `True` |
| `DJANGO_ALLOWED_HOSTS` | hosts aceitos, separados por vírgula | `localhost,127.0.0.1` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | origens HTTPS confiáveis | vazio em ambiente local |
| `DJANGO_FORCE_SCRIPT_NAME` | prefixo quando publicado em subcaminho | vazio em ambiente local |
| `DJANGO_EMAIL_BACKEND` | mecanismo de envio de e-mail | backend de console em desenvolvimento |
| `DJANGO_EMAIL_HOST` | servidor SMTP | `smtp.exemplo.br` |
| `DJANGO_EMAIL_PORT` | porta do servidor SMTP | `587` |
| `DJANGO_EMAIL_HOST_USER` | usuário do SMTP | fornecido pelo serviço de e-mail |
| `DJANGO_EMAIL_HOST_PASSWORD` | senha do SMTP | definida no ambiente |
| `DJANGO_EMAIL_USE_TLS` | ativa conexão SMTP com TLS | `True` em produção |
| `DJANGO_DEFAULT_FROM_EMAIL` | remetente das mensagens | `Pacto EJA <nao-responda@exemplo.br>` |
| `POSTGRES_DB` | nome do banco | `db_pacto_eja` |
| `POSTGRES_HOST` | servidor PostgreSQL | `127.0.0.1` |
| `POSTGRES_PORT` | porta PostgreSQL | `5432` |
| `POSTGRES_USER` | usuário do banco | `postgres` |
| `POSTGRES_PASSWORD` | senha do banco | definida localmente |

O `.env` contém credenciais e não deve ser versionado.

### 3. Preparar e iniciar a aplicação

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

As migrações iniciais também carregam estados, cidades, escolas e temáticas padrão; por isso a primeira execução pode demorar mais.

Endereços úteis:

- cadastro público: <http://127.0.0.1:8000/>;
- login: <http://127.0.0.1:8000/conta/entrar/>;
- painel: <http://127.0.0.1:8000/painel/>;
- administração nativa: <http://127.0.0.1:8000/admin/>.

O servidor de desenvolvimento recarrega o código automaticamente. CSS e JavaScript são servidos diretamente da pasta `static/`, sem `npm`, bundler ou etapa de compilação.

No ambiente local, os e-mails de recuperação são exibidos no terminal onde o `runserver` está em execução. Em produção, configure as variáveis SMTP no arquivo de ambiente; sem um servidor de e-mail válido, a senha da conta não será alterada. Para impedir redefinições sucessivas, o sistema aceita uma solicitação por CPF a cada cinco minutos.

## Qualidade e testes

Antes de enviar uma alteração, execute:

```powershell
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

Os testes usam o mecanismo padrão do Django e criam um banco PostgreSQL temporário. O usuário configurado no `.env` precisa ter permissão para criar bancos de teste.

Se uma execução anterior deixou o banco de testes criado, confirme a reutilização quando solicitado ou execute temporariamente com `python manage.py test --keepdb`.

Convenções adotadas no código:

- nomes do domínio em português e nomes técnicos do framework preservados;
- regras de entrada nos formulários e regras de integridade também nos models/banco;
- views pequenas, com consultas relacionadas carregadas explicitamente;
- docstrings explicam intenção, contrato ou decisão não evidente;
- comentários são reservados para regras e restrições que o código sozinho não comunica.

## Termos em PDF

Os PDFs usados no formulário ficam em `static/docs/` e devem ser versionados junto com o código. Para alterar o texto, edite `scripts/generate_terms_pdfs.py`, atualize `Trabalho.VERSAO_ATUAL_TERMOS` quando houver mudança jurídica relevante e regenere os arquivos:

```powershell
python scripts/generate_terms_pdfs.py
```

O script usa Arial quando executado no Windows e Helvetica nos demais sistemas. O aceite gravado no banco contém a versão e a data, portanto um termo já aceito não deve ser substituído silenciosamente sem revisar a estratégia de versionamento.

## Permissões administrativas

O menu é montado a partir das permissões do usuário. Marcar alguém como `is_staff` não concede automaticamente acesso a todos os módulos: associe o usuário a grupos ou conceda permissões como `view_atividade`, `change_atividade` e `view_educador` pelo Django Admin. Superusuários possuem acesso completo.

## Arquivos estáticos e uploads

- arquivos autorais ficam em `static/`;
- os termos de aceite ficam em `static/docs/` e fazem parte do repositório;
- `collectstatic` copia os ativos para `staticfiles/`, que é conteúdo gerado;
- trabalhos e suas evidências ficam em `media/trabalhos/` e não são versionados;
- o download de trabalho exige ser o autor da inscrição ou possuir `core.view_trabalho`.

Em produção, os arquivos estáticos são servidos pelo WhiteNoise. Os uploads em `media/` precisam de backup e de uma estratégia de entrega compatível com a infraestrutura; o WhiteNoise não serve mídia privada.

## Publicar na VM Debian

O exemplo atual considera o projeto em `/home/sandeison/pacto_eja`, o usuário de serviço `sandeison`, Gunicorn na porta 8080 e um proxy reverso externo publicando `/catedraunescoeja/eventos/`.

Instale os pacotes do sistema e prepare o ambiente:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-dev build-essential libpq-dev postgresql git
sudo -u postgres createuser --pwprompt pacto_eja
sudo -u postgres createdb --owner=pacto_eja db_pacto_eja
cd /home/sandeison/pacto_eja
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Instale a configuração, troque todos os segredos de exemplo e prepare o serviço:

```bash
sudo cp deploy/pacto-eja.env.example /etc/pacto-eja.env
sudo chmod 600 /etc/pacto-eja.env
sudo editor /etc/pacto-eja.env
sudo cp deploy/pacto-eja.service /etc/systemd/system/
sudo systemctl daemon-reload
```

Execute comandos Django com o mesmo usuário e ambiente do serviço:

```bash
sudo systemd-run --wait --pipe --collect --uid=sandeison --working-directory=/home/sandeison/pacto_eja --property=EnvironmentFile=/etc/pacto-eja.env /home/sandeison/pacto_eja/.venv/bin/python manage.py migrate
sudo systemd-run --wait --pipe --collect --uid=sandeison --working-directory=/home/sandeison/pacto_eja --property=EnvironmentFile=/etc/pacto-eja.env /home/sandeison/pacto_eja/.venv/bin/python manage.py collectstatic --noinput
sudo systemctl enable --now pacto-eja
sudo systemctl status pacto-eja
```

Para criar um administrador:

```bash
sudo systemd-run --pty --collect --uid=sandeison --working-directory=/home/sandeison/pacto_eja --property=EnvironmentFile=/etc/pacto-eja.env /home/sandeison/pacto_eja/.venv/bin/python manage.py createsuperuser
```

O proxy deve remover o prefixo público antes de encaminhar para `http://127.0.0.1:8080`, preservar a barra final e enviar `Host` e `X-Forwarded-Proto: https`. Não exponha a porta 8080 diretamente à internet.

Para acompanhar falhas:

```bash
sudo journalctl -u pacto-eja -f
```

### Atualizações

Após atualizar o código, instale eventuais dependências, aplique migrações, colete os estáticos e reinicie:

```bash
/home/sandeison/pacto_eja/.venv/bin/pip install -r /home/sandeison/pacto_eja/requirements.txt
sudo systemd-run --wait --pipe --collect --uid=sandeison --working-directory=/home/sandeison/pacto_eja --property=EnvironmentFile=/etc/pacto-eja.env /home/sandeison/pacto_eja/.venv/bin/python manage.py migrate
sudo systemd-run --wait --pipe --collect --uid=sandeison --working-directory=/home/sandeison/pacto_eja --property=EnvironmentFile=/etc/pacto-eja.env /home/sandeison/pacto_eja/.venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart pacto-eja
```
