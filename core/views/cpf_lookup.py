from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from ..models import Educador, FuncaoEducador
from ..validators import somente_digitos, validate_cpf


@require_GET
def cpf_lookup(request):
    """Consulta um CPF válido e devolve os dados reutilizáveis no cadastro."""
    cpf = somente_digitos(request.GET.get("cpf", ""))
    if len(cpf) != 11:
        return JsonResponse({"valid": False, "exists": False, "message": "Informe um CPF válido."}, status=400)
    try:
        validate_cpf(cpf)
    except ValidationError:
        return JsonResponse({"valid": False, "exists": False, "message": "Informe um CPF válido."}, status=400)

    educador = Educador.objects.select_related("usuario", "cor_raca", "genero").filter(cpf=cpf).first()
    if educador is None:
        return JsonResponse({"valid": True, "exists": False, "registered": False})

    return JsonResponse(
        {
            "valid": True,
            "exists": True,
            "registered": FuncaoEducador.objects.filter(educador=educador).exists(),
        }
    )
