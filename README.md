# Pacto EJA

Programa de Formação de Educadores construído com Django 6 e o tema oficial Django AdminLTE 4.

## Executar localmente

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Acesse `http://127.0.0.1:8000/` para abrir o cadastro público de educadores. O painel autenticado está em `/painel/` e o Django Admin está em `/admin/`.

As configurações locais são carregadas automaticamente do arquivo `.env`, que não é versionado. Para preparar outro computador, copie `.env.example` para `.env` e preencha a chave Django e a senha local do PostgreSQL.

## Configurar o banco de dados PostgreSQL

Instale o PostgreSQL e mantenha o serviço em execução. No Windows, o instalador oficial inclui o servidor e o `psql`; durante a instalação, defina uma senha para o usuário administrador `postgres`. No Debian/Ubuntu, instale e inicie o serviço com:

```bash
sudo apt update
sudo apt install -y postgresql
sudo systemctl enable --now postgresql
```

Crie o banco usado pela aplicação. No Windows, abra o **SQL Shell (psql)** e conecte-se com o usuário `postgres`. No Debian/Ubuntu, abra o console com `sudo -u postgres psql`. Em seguida, execute:

```sql
CREATE DATABASE db_pacto_eja;
```

Para sair do `psql`, use `\q`.

Na raiz do projeto, copie o arquivo de exemplo para `.env`:

```powershell
Copy-Item .env.example .env
```

No Linux, o comando equivalente é:

```bash
cp .env.example .env
```

Edite o `.env` e informe a senha definida para o PostgreSQL:

```dotenv
POSTGRES_DB=db_pacto_eja
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=sua-senha-do-postgresql
```

Não versione o `.env`, pois ele contém credenciais. Para conferir se o banco aceita a conexão, execute:

```powershell
psql -h 127.0.0.1 -p 5432 -U postgres -d db_pacto_eja
```

Por fim, com o ambiente virtual ativado e as dependências instaladas, crie as tabelas do projeto e, opcionalmente, um administrador:

```powershell
python manage.py migrate
python manage.py createsuperuser
```

Se o Django informar falha de autenticação, confira `POSTGRES_USER` e `POSTGRES_PASSWORD`. Se informar conexão recusada, confirme que o serviço PostgreSQL está iniciado e escutando na porta configurada em `POSTGRES_PORT`.

## Publicar na VM Debian

A aplicação de produção roda como o usuário sem privilégios `sandeison`, escuta na porta 8080 com Gunicorn e entrega seus próprios arquivos estáticos com WhiteNoise. O HTTPS e o endereço público são fornecidos pelo proxy reverso da STI.

### 1. Instalar os pacotes do sistema

O Django 6 requer Python 3.12 ou superior. Confirme com `python3 --version` antes de prosseguir.

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-dev build-essential libpq-dev postgresql git
```

### 2. Configurar o banco e o ambiente virtual

```bash
sudo -u postgres createuser --pwprompt pacto_eja
sudo -u postgres createdb --owner=pacto_eja db_pacto_eja
```

O projeto já deve estar em `/home/sandeison/pacto_eja`. Prepare o ambiente virtual:

```bash
cd /home/sandeison/pacto_eja
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 3. Configurar os segredos

```bash
sudo cp /home/sandeison/pacto_eja/deploy/pacto-eja.env.example /etc/pacto-eja.env
sudo chmod 600 /etc/pacto-eja.env
sudo editor /etc/pacto-eja.env
```

Troque `DJANGO_SECRET_KEY` e `POSTGRES_PASSWORD`. Para gerar uma chave Django:

```bash
/home/sandeison/pacto_eja/.venv/bin/python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

O arquivo já configura a URL pública como `https://www.ce.ufpb.br/catedraunescoeja/eventos`.

### 4. Preparar Django e iniciar o serviço

Instale primeiro a unidade do serviço:

```bash
sudo cp /home/sandeison/pacto_eja/deploy/pacto-eja.service /etc/systemd/system/
sudo systemctl daemon-reload
```

Use processos transitórios do systemd para que os comandos recebam as mesmas variáveis e o mesmo usuário do serviço:

```bash
sudo systemd-run --wait --pipe --collect --uid=sandeison --working-directory=/home/sandeison/pacto_eja --property=EnvironmentFile=/etc/pacto-eja.env /home/sandeison/pacto_eja/.venv/bin/python manage.py migrate
sudo systemd-run --wait --pipe --collect --uid=sandeison --working-directory=/home/sandeison/pacto_eja --property=EnvironmentFile=/etc/pacto-eja.env /home/sandeison/pacto_eja/.venv/bin/python manage.py collectstatic --noinput
sudo systemctl enable --now pacto-eja
sudo systemctl status pacto-eja
```

Crie o administrador, se necessário:

```bash
sudo systemd-run --pty --collect --uid=sandeison --working-directory=/home/sandeison/pacto_eja --property=EnvironmentFile=/etc/pacto-eja.env /home/sandeison/pacto_eja/.venv/bin/python manage.py createsuperuser
```

### 5. Testar na VM e pela VPN

Na própria VM:

```bash
curl -I http://127.0.0.1:8080/
sudo ss -ltnp | grep ':8080'
sudo journalctl -u pacto-eja -f
```

De uma máquina com acesso à rede da STI/VPN:

```bash
curl -I http://150.165.130.117:8080/
```

Não libere a porta 8080 para a internet. Se a VM usar UFW ou outro firewall local, autorize somente as redes/origens indicadas pela STI.

Depois que a STI ativar o proxy, acesse:

`https://www.ce.ufpb.br/catedraunescoeja/eventos/`

### Requisito do proxy da STI

Peça à STI que configure o mapeamento com remoção do prefixo:

```text
URL pública:   /catedraunescoeja/eventos/conta/...
URL no backend: http://150.165.130.117:8080/conta/...
```

O proxy também deve enviar `Host: www.ce.ufpb.br`, `X-Forwarded-Proto: https` e, idealmente, `X-Forwarded-For`. A barra final em `/eventos/` deve ser preservada; uma requisição a `/eventos` pode ser redirecionada para `/eventos/`.

### Atualizações futuras

Após atualizar o código em `/home/sandeison/pacto_eja`:

```bash
sudo -u sandeison /home/sandeison/pacto_eja/.venv/bin/pip install -r /home/sandeison/pacto_eja/requirements.txt
sudo systemd-run --wait --pipe --collect --uid=sandeison --working-directory=/home/sandeison/pacto_eja --property=EnvironmentFile=/etc/pacto-eja.env /home/sandeison/pacto_eja/.venv/bin/python manage.py migrate
sudo systemd-run --wait --pipe --collect --uid=sandeison --working-directory=/home/sandeison/pacto_eja --property=EnvironmentFile=/etc/pacto-eja.env /home/sandeison/pacto_eja/.venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart pacto-eja
```
