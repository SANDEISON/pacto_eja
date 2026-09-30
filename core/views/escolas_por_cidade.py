from django.db.models import Case, IntegerField, Value, When
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from ..models import Cidade, Escola


@require_GET
def escolas_por_cidade(request):
    """Pesquisa escolas da cidade escolhida para o componente de seleção."""
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
    # Mantém a opção Outra visível mesmo em municípios com mais de 100 escolas.
    prioridade_outra = Case(
        When(id_escola=9_000_000_000 + cidade.codigo_ibge, then=Value(0)),
        default=Value(1),
        output_field=IntegerField(),
    )
    results = list(escolas.order_by(prioridade_outra, "nome").values("id_escola", "nome")[:100])
    return JsonResponse({"results": results})
