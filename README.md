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

Acesse `http://127.0.0.1:8000/`. O painel exige autenticação; o Django Admin está em `/admin/` e também utiliza o tema AdminLTE 4.

Variáveis opcionais: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` e `DJANGO_ALLOWED_HOSTS`.
