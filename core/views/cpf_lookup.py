from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from ..models import CadastroEducador, Pessoa
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

    pessoa = Pessoa.objects.select_related("usuario").filter(cpf=cpf).first()
    if pessoa is None:
        return JsonResponse({"valid": True, "exists": False, "registered": False})

    usuario = pessoa.usuario
    return JsonResponse(
        {
            "valid": True,
            "exists": True,
            "registered": CadastroEducador.objects.filter(id_pessoa=pessoa).exists(),
            "nome_completo": usuario.get_full_name() or usuario.first_name or usuario.username,
            "email": usuario.email or usuario.username,
        }
    )
