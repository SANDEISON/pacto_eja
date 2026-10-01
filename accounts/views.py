import logging
import secrets
import string
from datetime import timedelta
from hashlib import sha256

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.core import signing
from django.core.cache import cache
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from core.models import CadastroPendente

from .constants import SENHA_INICIAL
from .forms import CPFAuthenticationForm, FirstAccessPasswordForm, PasswordRecoveryForm, SignUpForm


logger = logging.getLogger(__name__)
User = get_user_model()
CARACTERES_SENHA_TEMPORARIA = string.ascii_letters + string.digits + "!@#$%&*"
INTERVALO_RECUPERACAO_SEGUNDOS = 5 * 60
MENSAGEM_RECUPERACAO_SOLICITADA = (
    "Se o CPF estiver vinculado a uma conta com e-mail, a senha temporária será enviada. "
    "Caso não receba a mensagem, verifique a caixa de spam e aguarde 5 minutos antes de "
    "solicitar novamente."
)
VALIDADE_CONFIRMACAO_SEGUNDOS = 24 * 60 * 60
SALT_CONFIRMACAO_CONTA = "cadastro-conta-email"


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

    def form_valid(self, form):
        if form.cleaned_data["password"] == SENHA_INICIAL:
            self.request.session["alteracao_senha_obrigatoria"] = True
            self.request.session["destino_apos_alterar_senha"] = self.get_redirect_url()
        else:
            self.request.session.pop("alteracao_senha_obrigatoria", None)
            self.request.session.pop("destino_apos_alterar_senha", None)
        return super().form_valid(form)

    def get_success_url(self):
        if self.request.session.get("alteracao_senha_obrigatoria"):
            return reverse("accounts:change_initial_password")
        return super().get_success_url()


class FirstAccessPasswordView(PasswordChangeView):
    template_name = "accounts/change_initial_password.html"
    form_class = FirstAccessPasswordForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.session.get("alteracao_senha_obrigatoria"):
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.session.pop("alteracao_senha_obrigatoria", None)
        self.request.session.pop("destino_apos_alterar_senha", None)
        messages.success(self.request, "Sua senha foi alterada com sucesso.")
        return response

    def get_success_url(self):
        destino = self.request.session.get("destino_apos_alterar_senha", "")
        if destino and url_has_allowed_host_and_scheme(
            destino, allowed_hosts={self.request.get_host()}, require_https=self.request.is_secure(),
        ) and destino != reverse("accounts:change_initial_password"):
            return destino
        return reverse("dashboard")


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
    """Cria a conta diretamente enquanto a confirmação por e-mail está suspensa."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        # Confirmação por e-mail suspensa temporariamente pelo limite do Gmail.
        try:
            with transaction.atomic():
                form.save()
        except ValidationError as error:
            form.add_error("cpf", error)
        except IntegrityError:
            form.add_error(None, "Não foi possível concluir o cadastro. Verifique se os dados já estão em uso.")
        else:
            mensagem = (
                "Sua senha foi definida e sua conta já pode ser acessada."
                if form.usuario_encontrado else "Sua conta foi criada e já pode ser acessada."
            )
            messages.success(request, mensagem)
            return redirect("accounts:signin")

        # Fluxo de confirmação preservado para reativação após resolver o limite.
        # CadastroPendente.objects.filter(
        #     tipo=CadastroPendente.Tipo.CONTA,
        #     criado_em__lt=timezone.now() - timedelta(seconds=VALIDADE_CONFIRMACAO_SEGUNDOS),
        # ).delete()
        # usuario_nao_salvo = form.save(commit=False)
        # pendente = CadastroPendente.objects.create(
        #     tipo=CadastroPendente.Tipo.CONTA,
        #     cpf=form.cleaned_data["cpf"],
        #     email=form.cleaned_data["email"],
        #     dados={"full_name": form.cleaned_data["full_name"].strip()},
        #     senha_hash=usuario_nao_salvo.password,
        # )
        # token = signing.dumps(
        #     {"cadastro_id": str(pendente.pk)},
        #     salt=SALT_CONFIRMACAO_CONTA,
        #     compress=True,
        # )
        # confirmacao_url = request.build_absolute_uri(
        #     f'{reverse("accounts:signup_confirm")}?token={token}'
        # )
        # try:
        #     send_mail(
        #         subject="Confirme sua conta — Pacto EJA",
        #         message=(
        #             f"Olá, {pendente.dados['full_name']}!\n\n"
        #             "Para confirmar seu e-mail e criar sua conta no Pacto EJA, "
        #             "acesse o link abaixo:\n\n"
        #             f"{confirmacao_url}\n\n"
        #             "O link é válido por 24 horas. Se você não solicitou esta conta, "
        #             "ignore esta mensagem."
        #         ),
        #         from_email=None,
        #         recipient_list=[pendente.email],
        #         fail_silently=False,
        #     )
        # except Exception:
        #     pendente.delete()
        #     logger.exception("Falha ao enviar e-mail de confirmação da conta")
        #     form.add_error(None, "Não foi possível enviar a confirmação por e-mail. O cadastro não foi concluído. Tente novamente mais tarde; se o problema persistir, entre em contato com a coordenação.")
        # else:
        #     return redirect("accounts:signup_confirmation_sent")
    return render(request, "accounts/signup.html", {"form": form})


def signup_confirmation_sent(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "accounts/signup_confirmation_sent.html")


def signup_confirm(request):
    """Cria a conta somente após a confirmação explícita do endereço de e-mail."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    token = request.GET.get("token") or request.POST.get("token", "")
    try:
        dados_token = signing.loads(
            token,
            salt=SALT_CONFIRMACAO_CONTA,
            max_age=VALIDADE_CONFIRMACAO_SEGUNDOS,
        )
        pendente = CadastroPendente.objects.get(
            pk=dados_token["cadastro_id"],
            tipo=CadastroPendente.Tipo.CONTA,
        )
    except (signing.BadSignature, signing.SignatureExpired, CadastroPendente.DoesNotExist, KeyError):
        return render(
            request,
            "accounts/signup_confirm.html",
            {"confirmacao_invalida": True},
            status=400,
        )

    if request.method == "POST":
        if (
            User.objects.filter(username=pendente.cpf).exists()
            or User.objects.filter(email__iexact=pendente.email).exists()
        ):
            pendente.delete()
            return render(
                request,
                "accounts/signup_confirm.html",
                {"confirmacao_invalida": True},
                status=409,
            )

        full_name = pendente.dados["full_name"].strip()
        first_name, _, last_name = full_name.partition(" ")
        try:
            with transaction.atomic():
                user = User(
                    username=pendente.cpf,
                    email=pendente.email,
                    first_name=first_name,
                    last_name=last_name,
                    password=pendente.senha_hash,
                )
                user.save()
                educador = user.educador
                educador.cpf = pendente.cpf
                educador.nome_completo = full_name
                educador.save(update_fields=("cpf", "nome_completo"))
                pendente.delete()
        except (IntegrityError, KeyError):
            return render(
                request,
                "accounts/signup_confirm.html",
                {"confirmacao_invalida": True},
                status=409,
            )

        messages.success(request, "E-mail confirmado. Sua conta foi criada e já pode ser acessada.")
        return redirect("accounts:signin")

    return render(
        request,
        "accounts/signup_confirm.html",
        {"token": token, "email": pendente.email},
    )
