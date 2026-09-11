# Pacto EJA

Sistema web do Programa de Formação de Educadores do Pacto EJA. A aplicação reúne cadastro de educadores, perfil acadêmico e profissional, vínculos com escolas, atividades/eventos, inscrições e submissão de trabalhos em PDF.

O projeto é uma aplicação Django renderizada no servidor. O PostgreSQL armazena os dados, o Django AdminLTE fornece a interface autenticada e o WhiteNoise entrega os arquivos estáticos em produção.

## Funcionalidades

- cadastro público de educadores com consulta de CPF;
- endereço, formações acadêmicas e múltiplos vínculos com escolas;
- autenticação por CPF usando o sistema de usuários do Django;
- painel do educador com atividades disponíveis e inscrições realizadas;
- inscrição em eventos, palestras e cursos;
- submissão de um trabalho em PDF, com coautores cadastrados na plataforma;
- gestão de atividades, inscrições, educadores e catálogos auxiliares;
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
templates/      páginas e componentes HTML
```

Os models são separados por assunto e exportados por `core.models`. O mesmo padrão é usado em `core.forms` e `core.views`, permitindo imports curtos sem concentrar toda a implementação em um único arquivo.

### Fluxos principais

1. O cadastro público cria uma conta cujo `username` é o CPF sem máscara e cria o perfil `Educador` associado.
2. O usuário entra por `/conta/entrar/` e acessa o painel em `/painel/`.
3. Uma atividade ativa aparece quando o período de inscrição está aberto ou quando o usuário já está inscrito.
4. A inscrição atualiza os dados pessoais e cria uma única relação entre usuário e atividade.
5. Quando permitido, o usuário envia um PDF de até 10 MB e seleciona coautores que já tenham conta ativa.
6. Usuários da equipe acessam as telas de gestão conforme as permissões atribuídas pelo Django.

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

A primeira migração também carrega estados, cidades e a base de escolas; por isso ela pode demorar mais que as demais.

Endereços úteis:

- cadastro público: <http://127.0.0.1:8000/>;
- login: <http://127.0.0.1:8000/conta/entrar/>;
- painel: <http://127.0.0.1:8000/painel/>;
- administração nativa: <http://127.0.0.1:8000/admin/>.

## Qualidade e testes

Antes de enviar uma alteração, execute:

```powershell
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

Os testes usam o mecanismo padrão do Django e criam um banco PostgreSQL temporário. O usuário configurado no `.env` precisa ter permissão para criar bancos de teste.

Convenções adotadas no código:

- nomes do domínio em português e nomes técnicos do framework preservados;
- regras de entrada nos formulários e regras de integridade também nos models/banco;
- views pequenas, com consultas relacionadas carregadas explicitamente;
- docstrings explicam intenção, contrato ou decisão não evidente;
- comentários são reservados para regras e restrições que o código sozinho não comunica.

## Permissões administrativas

O menu é montado a partir das permissões do usuário. Marcar alguém como `is_staff` não concede automaticamente acesso a todos os módulos: associe o usuário a grupos ou conceda permissões como `view_atividade`, `change_atividade` e `view_educador` pelo Django Admin. Superusuários possuem acesso completo.

## Arquivos estáticos e uploads

- arquivos autorais ficam em `static/`;
- `collectstatic` copia os ativos para `staticfiles/`, que é conteúdo gerado;
- trabalhos enviados ficam em `media/trabalhos/` e não são versionados;
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
