import logging
from datetime import timedelta

from django.core import signing
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.http import QueryDict
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from ..forms import EducadorEscolaCadastroForm
from ..models import CadastroPendente


logger = logging.getLogger(__name__)
VALIDADE_CONFIRMACAO_SEGUNDOS = 24 * 60 * 60
SALT_CONFIRMACAO = "cadastro-educador-email"


def _serializar_post(post):
    """Preserva campos de seleção múltipla sem guardar o token CSRF."""
    return {
        chave: post.getlist(chave)
        for chave in post
        if chave != "csrfmiddlewaretoken"
    }


def _restaurar_post(dados):
    post = QueryDict("", mutable=True)
    for chave, valores in dados.items():
        post.setlist(chave, [str(valor) for valor in valores])
    return post


def _token_confirmacao(cadastro_pendente):
    return signing.dumps(
        {"cadastro_id": str(cadastro_pendente.pk)},
        salt=SALT_CONFIRMACAO,
        compress=True,
    )


def _carregar_cadastro_pendente(token):
    dados = signing.loads(
        token,
        salt=SALT_CONFIRMACAO,
        max_age=VALIDADE_CONFIRMACAO_SEGUNDOS,
    )
    return CadastroPendente.objects.get(pk=dados["cadastro_id"])


@require_http_methods(["GET", "POST"])
def cadastro_educador(request):
    """Valida o formulário e confirma o e-mail antes de criar uma nova conta."""
    form = EducadorEscolaCadastroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        # Perfis existentes continuam apenas adicionando vínculos; não há uma nova
        # conta ou um novo endereço de e-mail a confirmar nesse caso.
        if form.educador_encontrado is not None:
            try:
                form.save_cadastro()
            except IntegrityError:
                form.add_error(None, "Não foi possível concluir o cadastro. Verifique se os dados já estão em uso.")
            else:
                return redirect("cadastro_educador_success")
            return render(request, "cadastro_educadores/form.html", {"form": form})

        CadastroPendente.objects.filter(
            criado_em__lt=timezone.now() - timedelta(seconds=VALIDADE_CONFIRMACAO_SEGUNDOS)
        ).delete()
        pendente = CadastroPendente.objects.create(
            cpf=form.cleaned_data["cpf"],
            email=form.cleaned_data["email"],
            dados=_serializar_post(request.POST),
        )
        token = _token_confirmacao(pendente)
        confirmacao_url = request.build_absolute_uri(
            f'{reverse("cadastro_educador_confirmar_email")}?token={token}'
        )
        try:
            send_mail(
                subject="Confirme seu cadastro — Pacto EJA",
                message=(
                    f"Olá, {form.cleaned_data['nome_completo']}!\n\n"
                    "Recebemos uma solicitação de cadastro no Pacto EJA. "
                    "Para confirmar seu e-mail e concluir o cadastro, acesse o link abaixo:\n\n"
                    f"{confirmacao_url}\n\n"
                    "O link é válido por 24 horas. Se você não solicitou este cadastro, "
                    "ignore esta mensagem."
                ),
                from_email=None,
                recipient_list=[pendente.email],
                fail_silently=False,
            )
        except Exception:
            pendente.delete()
            logger.exception("Falha ao enviar e-mail de confirmação do cadastro")
            form.add_error("email", "Não foi possível enviar a confirmação. Confira o e-mail e tente novamente.")
        else:
            return redirect("cadastro_educador_confirmacao_enviada")
    return render(request, "cadastro_educadores/form.html", {"form": form})


@require_http_methods(["GET", "POST"])
def cadastro_educador_confirmar_email(request):
    """Confirma o endereço e só então grava o cadastro público pendente."""
    token = request.GET.get("token") or request.POST.get("token", "")
    try:
        pendente = _carregar_cadastro_pendente(token)
    except (signing.BadSignature, signing.SignatureExpired, CadastroPendente.DoesNotExist, KeyError):
        return render(
            request,
            "cadastro_educadores/confirm_email.html",
            {"confirmacao_invalida": True},
            status=400,
        )

    if request.method == "POST":
        form = EducadorEscolaCadastroForm(_restaurar_post(pendente.dados))
        if not form.is_valid() or form.educador_encontrado is not None:
            pendente.delete()
            return render(
                request,
                "cadastro_educadores/confirm_email.html",
                {"confirmacao_invalida": True},
                status=409,
            )
        try:
            with transaction.atomic():
                form.save_cadastro()
                pendente.delete()
        except IntegrityError:
            return render(
                request,
                "cadastro_educadores/confirm_email.html",
                {"confirmacao_invalida": True},
                status=409,
            )
        return redirect("cadastro_educador_success")

    return render(
        request,
        "cadastro_educadores/confirm_email.html",
        {"token": token, "email": pendente.email},
    )


@require_http_methods(["GET"])
def cadastro_educador_confirmacao_enviada(request):
    return render(request, "cadastro_educadores/confirmation_sent.html")
