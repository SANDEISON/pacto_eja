from django.http import JsonResponse
from django.views.decorators.http import require_GET

from ..models import Cidade


@require_GET
def cidades_por_estado(request):
    estado_id = request.GET.get("estado")
    cidades = (
        Cidade.objects.filter(estado_id=estado_id).values("id", "nome_cidade")
        if estado_id and estado_id.isdigit()
        else []
    )
    return JsonResponse({"results": list(cidades)})
