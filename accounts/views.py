import logging
import secrets
import string
from hashlib import sha256

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.views import LoginView, LogoutView
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import CPFAuthenticationForm, PasswordRecoveryForm, SignUpForm


logger = logging.getLogger(__name__)
User = get_user_model()
CARACTERES_SENHA_TEMPORARIA = string.ascii_letters + string.digits + "!@#$%&*"
INTERVALO_RECUPERACAO_SEGUNDOS = 5 * 60
MENSAGEM_RECUPERACAO_SOLICITADA = (
    "Se o CPF estiver vinculado a uma conta com e-mail, a senha temporária será enviada. "
    "Caso não receba a mensagem, verifique a caixa de spam e aguarde 5 minutos antes de "
    "solicitar novamente."
)


def gerar_senha_temporaria(tamanho=14):
    """Gera uma senha aleatória contendo letras, número e caractere especial."""
    caracteres_obrigatorios = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%&*"),
    ]
    caracteres_aleatorios = [
        secrets.choice(CARACTERES_SENHA_TEMPORARIA)
        for _ in range(tamanho - len(caracteres_obrigatorios))
    ]
    senha = caracteres_obrigatorios + caracteres_aleatorios
    secrets.SystemRandom().shuffle(senha)
    return "".join(senha)


def chave_limite_recuperacao(cpf):
    """Cria uma chave de cache sem armazenar o CPF em texto legível."""
    identificador = sha256(cpf.encode("utf-8")).hexdigest()
    return f"recuperacao-senha:{identificador}"


class SignInView(LoginView):
    """Exibe o login por CPF e evita uma segunda autenticação na mesma sessão."""
    template_name = "accounts/signin.html"
    authentication_form = CPFAuthenticationForm
    redirect_authenticated_user = True


class SignOutView(LogoutView):
    """Encerra a sessão somente por POST para evitar logout acidental por links."""
    http_method_names = ["post", "options"]
    next_page = reverse_lazy("accounts:signin")


def recover_password(request):
    """Envia uma senha temporária ao e-mail da conta identificada pelo CPF."""
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = PasswordRecoveryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        chave_limite = chave_limite_recuperacao(form.cleaned_data["cpf"])
        primeira_tentativa = cache.add(
            chave_limite,
            True,
            timeout=INTERVALO_RECUPERACAO_SEGUNDOS,
        )
        if not primeira_tentativa:
            messages.success(request, MENSAGEM_RECUPERACAO_SOLICITADA)
            return redirect("accounts:signin")

        usuario = User.objects.filter(
            username=form.cleaned_data["cpf"],
            is_active=True,
        ).first()

        if usuario and usuario.email:
            senha_temporaria = gerar_senha_temporaria()
            try:
                # A transação desfaz a troca da senha quando o servidor de e-mail falha.
                with transaction.atomic():
                    usuario.set_password(senha_temporaria)
                    usuario.save(update_fields=("password",))
                    send_mail(
                        subject="Senha temporária de acesso — Pacto EJA",
                        message=(
                            f"Olá, {usuario.get_full_name() or 'participante'}!\n\n"
                            "Recebemos uma solicitação de recuperação de senha para sua conta "
                            "no Pacto EJA.\n\n"
                            f"Sua senha temporária é: {senha_temporaria}\n\n"
                            "Entre na plataforma e altere a senha em seu perfil. Se você não "
                            "solicitou esta recuperação, entre em contato com a coordenação."
                        ),
                        from_email=None,
                        recipient_list=[usuario.email],
                        fail_silently=False,
                    )
            except Exception:
                cache.delete(chave_limite)
                logger.exception("Falha ao enviar e-mail de recuperação de senha")
                messages.error(
                    request,
                    "Não foi possível enviar o e-mail agora. Tente novamente mais tarde.",
                )
                return render(request, "accounts/password_recovery.html", {"form": form})

        messages.success(request, MENSAGEM_RECUPERACAO_SOLICITADA)
        return redirect("accounts:signin")

    return render(request, "accounts/password_recovery.html", {"form": form})


def signup(request):
    """Cadastra uma conta pública e inicia a sessão do novo usuário."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Sua conta foi criada. Boas-vindas ao Pacto EJA!")
        return redirect("dashboard")
    return render(request, "accounts/signup.html", {"form": form})
