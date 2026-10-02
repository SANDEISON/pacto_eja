from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from ..models import Educador, EducadorEscola, Endereco, FuncaoEducador
from ..validators import somente_digitos, validate_cpf


@require_GET
def cpf_lookup(request):
    """Localiza o cadastro e carrega os dados quando a edição é solicitada."""
    cpf = somente_digitos(request.GET.get("cpf", ""))
    if len(cpf) != 11:
        return JsonResponse({"valid": False, "exists": False, "message": "Informe um CPF válido."}, status=400)
    try:
        validate_cpf(cpf)
    except ValidationError:
        return JsonResponse({"valid": False, "exists": False, "message": "Informe um CPF válido."}, status=400)

    educador = Educador.objects.select_related("usuario").filter(cpf=cpf).first()
    usuario = educador.usuario if educador else get_user_model().objects.filter(username=cpf).first()
    if educador is None:
        educador = Educador.objects.filter(usuario=usuario).first() if usuario else None

    registered = bool(educador and FuncaoEducador.objects.filter(educador=educador).exists())
    resultado = {"valid": True, "exists": usuario is not None, "registered": registered}
    editar = request.GET.get("editar") == "1"
    if usuario and (not registered or editar):
        dados = {
            "nome_completo": (educador.nome_completo if educador else "") or usuario.get_full_name(),
            "email": usuario.email,
            "data_nascimento": educador.data_nascimento.isoformat() if educador and educador.data_nascimento else "",
            "cor_raca": educador.cor_raca_id if educador else None,
            "genero": educador.genero_id if educador else None,
            "curso_certificado": list(educador.cursos_certificados.values_list("pk", flat=True)) if educador else [],
        }
        if dados["nome_completo"] == usuario.username:
            dados["nome_completo"] = usuario.get_full_name()
        endereco = Endereco.objects.select_related("cidade").filter(educador=educador).first() if educador else None
        if endereco:
            for campo in ("cep", "logradouro", "numero", "complemento", "bairro"):
                dados[f"endereco_{campo}"] = getattr(endereco, campo)
            dados["endereco_cidade"] = endereco.cidade_id
            dados["endereco_estado"] = endereco.cidade.estado_id if endereco.cidade_id else None
        resultado["dados"] = dados
        if registered and editar:
            dados["atuacoes"] = [
                {
                    "estado_id": v.cidade.estado_id,
                    "estado_nome": str(v.cidade.estado),
                    "cidade_id": v.cidade_id,
                    "cidade_nome": v.cidade.nome_cidade,
                    "escola_id": v.escola_id,
                    "escola_nome": v.escola.nome,
                    "funcao": v.funcao_id,
                    "funcao_nome": str(v.funcao) if v.funcao else "",
                    "funcao_caracterizacao_turmas": v.funcao_caracterizacao_turmas_id,
                    "funcao_caracterizacao_turmas_nome": str(v.funcao_caracterizacao_turmas),
                    "tempo_atuacao": v.tempo_atuacao,
                    "tempo_atuacao_nome": v.get_tempo_atuacao_display(),
                }
                for v in EducadorEscola.objects.filter(funcao_educador__educador=educador).select_related(
                    "cidade__estado", "escola", "funcao", "funcao_caracterizacao_turmas",
                )
            ]

    response = JsonResponse(resultado)
    response["Cache-Control"] = "no-store"
    return response
