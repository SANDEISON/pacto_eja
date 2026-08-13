from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from ..models import Educador, FuncaoEducador
from ..validators import validate_cpf


@require_GET
def cpf_lookup(request):
    cpf = "".join(character for character in request.GET.get("cpf", "") if character.isdigit())
    if len(cpf) != 11:
        return JsonResponse({"valid": False, "exists": False, "message": "Informe um CPF válido."}, status=400)
    try:
        validate_cpf(cpf)
    except ValidationError:
        return JsonResponse({"valid": False, "exists": False, "message": "Informe um CPF válido."}, status=400)

    educador = Educador.objects.select_related("usuario").filter(cpf=cpf).first()
    if educador is None:
        return JsonResponse({"valid": True, "exists": False, "registered": False})

    usuario = educador.usuario
    return JsonResponse(
        {
            "valid": True,
            "exists": True,
            "registered": FuncaoEducador.objects.filter(educador=educador).exists(),
            "nome_completo": educador.nome_completo or usuario.get_full_name() or usuario.first_name or usuario.username,
            "email": usuario.email,
        }
    )
