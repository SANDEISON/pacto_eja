from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def dashboard(request):
    context = {
        "year": date.today().year,
        "stats": [
            {"value": 806, "label": "Educadores em formação", "icon": "bi-people-fill", "color": "info"},
            {"value": 7, "label": "Formações em andamento", "icon": "bi-mortarboard-fill", "color": "success"},
            {"value": 11441, "label": "Participações registradas", "icon": "bi-journal-check", "color": "danger"},
        ],
    }
    return render(request, "index.html", context)
