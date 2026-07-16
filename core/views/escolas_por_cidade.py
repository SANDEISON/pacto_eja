from django.http import JsonResponse
from django.views.decorators.http import require_GET

from ..models import Cidade, Escola


@require_GET
def escolas_por_cidade(request):
    cidade_id = request.GET.get("cidade", "")
    cidade = (
        Cidade.objects.select_related("estado").filter(pk=cidade_id).first()
        if cidade_id.isdigit()
        else None
    )
    if cidade is None or not cidade.codigo_ibge:
        return JsonResponse({"results": []})

    busca = request.GET.get("q", "").strip()[:100]
    escolas = Escola.objects.filter(
        id_municipio=cidade.codigo_ibge,
        sigla_uf=cidade.estado.sigla,
    )
    if busca:
        escolas = escolas.filter(nome__icontains=busca)
    results = list(escolas.order_by("nome").values("id_escola", "nome")[:100])
    return JsonResponse({"results": results})
