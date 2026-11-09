from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Q, Value
from django.db.models.functions import Concat
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import get_script_prefix, reverse
from django.utils import timezone
from django.utils.text import slugify

from ..models import Atividade, Frequencia, Inscricao, ProgramacaoSala
from ..services.frequencia import cancelar_presenca, inscricoes_com_presencas, pode_operar, registrar_direto
from ..services.lista_inscritos import gerar_lista_inscritos
from ..services.frequencia_qr_pdf import gerar_frequencia_qr_pdf


@login_required
def frequencia_qr_pdf(request, pk, programacao_pk):
    atividade = get_object_or_404(Atividade, pk=pk)
    programacao = get_object_or_404(
        atividade.programacoes.select_related("sala", "tematica"),
        pk=programacao_pk, modalidade="presencial",
    )
    if not pode_operar(request.user, programacao):
        raise PermissionDenied
    token = signing.Signer(salt="frequencia.programacao").sign(f"{pk}:{programacao_pk}")
    caminho = reverse("frequencia_confirmar_presencial", args=[token]).removeprefix(get_script_prefix())
    url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/{caminho}"
    return FileResponse(
        gerar_frequencia_qr_pdf(atividade, programacao, url), as_attachment=True,
        filename=f"frequencia-qrcode-{slugify(str(programacao))}.pdf",
        content_type="application/pdf",
    )


@login_required
def frequencia_confirmar_presencial(request, token):
    try:
        identidade = signing.Signer(salt="frequencia.programacao").unsign(token)
        pk, programacao_pk = identidade.split(":")
        if not pk.isdecimal() or not programacao_pk.isdecimal():
            raise ValueError
    except (signing.BadSignature, ValueError):
        return render(request, "frequencia/confirmar_presencial.html",
                      {"erro": "QR Code inválido."}, status=400)
    atividade = get_object_or_404(Atividade, pk=pk)
    programacao = get_object_or_404(
        atividade.programacoes.select_related("sala", "tematica"),
        pk=programacao_pk, modalidade="presencial",
    )
    inscricao = Inscricao.objects.filter(
        atividade=atividade, programacoes=programacao,
        usuario=request.user, modalidade="presencial",
    ).first()
    contexto = {"atividade": atividade, "programacao": programacao}
    if inscricao is None:
        contexto["erro"] = "Você não possui inscrição presencial nesta programação. Entre com a conta utilizada na inscrição."
        return render(request, "frequencia/confirmar_presencial.html", contexto, status=403)
    contexto["confirmada"] = Frequencia.objects.filter(inscricao=inscricao, programacao=programacao).exists()
    # Validação de data desativada temporariamente para testes no servidor.
    # agora = timezone.now()
    if not contexto["confirmada"]:
        if not atividade.ativo:
            contexto["erro"] = "O evento está inativo."
        # elif timezone.localdate(agora) != programacao.data or not atividade.data_inicio <= agora <= atividade.data_fim:
        #     contexto["erro"] = "A confirmação está disponível somente na data da programação e durante o evento."
    if request.method == "POST" and not contexto.get("erro"):
        try:
            registrar_direto(inscricao, programacao, request.user, Frequencia.Metodo.QR_PROPRIO)
            return redirect("frequencia_confirmar_presencial", token=token)
        except ValidationError as erro:
            contexto["erro"] = " ".join(erro.messages)
    return render(request, "frequencia/confirmar_presencial.html", contexto)


@login_required
def frequencia_inscritos_pdf(request, pk, programacao_pk, modalidade):
    if modalidade not in Inscricao.Modalidade.values:
        raise Http404
    atividade = get_object_or_404(Atividade, pk=pk)
    programacao = get_object_or_404(
        atividade.programacoes.select_related("sala", "responsavel", "tematica"),
        pk=programacao_pk,
    )
    if not pode_operar(request.user, programacao):
        raise PermissionDenied
    filtro_modalidade = Q(modalidade=modalidade)
    if programacao.publica and programacao.modalidade == modalidade == Inscricao.Modalidade.ONLINE:
        filtro_modalidade |= Q(frequencias__programacao=programacao)
    inscricoes = Inscricao.objects.filter(
        filtro_modalidade, atividade=atividade, programacoes=programacao,
    ).select_related("usuario").distinct()
    return FileResponse(
        gerar_lista_inscritos(atividade, programacao, modalidade, inscricoes),
        as_attachment=True,
        filename=f"inscritos-{slugify(str(programacao))}.pdf",
        content_type="application/pdf",
    )


@login_required
def frequencia_index(request):
    programacoes = ProgramacaoSala.objects.select_related("sala", "responsavel", "tematica").prefetch_related("atividades").filter(atividades__isnull=False).annotate(_total_inscritos=Count("inscricoes", distinct=True)).distinct()
    if not request.user.has_perm("core.add_frequencia"):
        programacoes = programacoes.filter(responsavel=request.user)
    pares = [(atividade, p) for p in programacoes for atividade in p.atividades.all()]
    inscricoes = inscricoes_com_presencas(Inscricao.objects.filter(usuario=request.user))
    return render(request, "frequencia/index.html", {"pares": pares, "inscricoes": inscricoes})


@login_required
def frequencia_sala(request, pk, programacao_pk):
    atividade = get_object_or_404(Atividade, pk=pk)
    programacao = get_object_or_404(atividade.programacoes.select_related("sala", "responsavel"), pk=programacao_pk)
    if not pode_operar(request.user, programacao):
        raise PermissionDenied
    pode_acionar = atividade.ativo
    if request.method == "POST":
        try:
            if not atividade.ativo:
                raise ValidationError("O evento está inativo.")
            acao = request.POST.get("acao")
            if acao == "manual":
                inscricao = get_object_or_404(Inscricao, pk=request.POST.get("inscricao"), atividade=atividade, programacoes=programacao)
                _, criada = registrar_direto(inscricao, programacao, request.user, Frequencia.Metodo.MANUAL)
                messages.success(request, "Presença registrada." if criada else "Presença já registrada.")
            elif acao == "cancelar":
                inscricao = get_object_or_404(Inscricao, pk=request.POST.get("inscricao"), atividade=atividade, programacoes=programacao)
                cancelada = cancelar_presenca(inscricao, programacao, request.user)
                messages.success(request, "Confirmação de presença cancelada." if cancelada else "A presença já estava sem confirmação.")
        except ValidationError as erro:
            messages.error(request, " ".join(erro.messages))
        return redirect("frequencia_sala", pk=pk, programacao_pk=programacao_pk)
    inscricoes = Inscricao.objects.filter(atividade=atividade, programacoes=programacao).select_related("usuario").order_by("usuario__first_name", "usuario__username")
    if request.GET.get("q"):
        q = " ".join(request.GET["q"].split())
        if q:
            filtro = Q(_nome_completo__icontains=q) | Q(usuario__educador__nome_completo__icontains=q)
            cpf = "".join(c for c in q if c.isdecimal())
            if cpf and all(c.isdecimal() or c in ".- " for c in q):
                filtro |= Q(usuario__educador__cpf__icontains=cpf)
            inscricoes = inscricoes.annotate(
                _nome_completo=Concat("usuario__first_name", Value(" "), "usuario__last_name"),
            ).filter(filtro)
    registros = Frequencia.objects.filter(inscricao__atividade=atividade, programacao=programacao).select_related("inscricao__usuario", "registrada_por")
    presentes = set(registros.values_list("inscricao_id", flat=True))
    return render(request, "frequencia/sala.html", {"atividade": atividade, "programacao": programacao, "pode_acionar": pode_acionar, "participantes": [(i, i.pk in presentes) for i in inscricoes], "registros": registros})


@login_required
def frequencia_validar(request, token):
    try:
        pk = signing.Signer(salt="frequencia.inscricao").unsign(token)
        if not pk.isdecimal():
            raise signing.BadSignature
    except signing.BadSignature:
        return render(request, "frequencia/validar.html", {"erro": "QR Code inválido."}, status=400)
    inscricao = get_object_or_404(Inscricao.objects.select_related("usuario", "atividade"), pk=pk)
    programacoes = [p for p in inscricao.programacoes.select_related("sala").filter(modalidade="presencial")
                    if inscricao.atividade.ativo and pode_operar(request.user, p)]
    if not programacoes:
        raise PermissionDenied("Nenhuma sala presencial sob sua responsabilidade para esta inscrição.")
    if request.method == "POST":
        programacao = next((p for p in programacoes if str(p.pk) == request.POST.get("programacao")), None)
        if programacao is None:
            raise PermissionDenied
        try:
            _, criada = registrar_direto(inscricao, programacao, request.user, Frequencia.Metodo.QR)
            messages.success(request, "Presença registrada." if criada else "Presença já registrada.")
        except ValidationError as erro:
            messages.error(request, " ".join(erro.messages))
        return redirect("frequencia_sala", pk=inscricao.atividade_id, programacao_pk=programacao.pk)
    return render(request, "frequencia/validar.html", {"inscricao": inscricao, "programacoes": programacoes})


@login_required
def frequencia_online(request, pk, programacao_pk):
    inscricao = get_object_or_404(Inscricao, atividade_id=pk, usuario=request.user, modalidade="online", programacoes__pk=programacao_pk)
    programacao = get_object_or_404(inscricao.atividade.programacoes, pk=programacao_pk, modalidade="online")
    erro = ""
    acesso_liberado = programacao.acesso_online_liberado(timezone.now())
    if request.method == "POST":
        if not acesso_liberado:
            raise PermissionDenied
        try:
            _, criada = registrar_direto(inscricao, programacao, request.user, Frequencia.Metodo.ONLINE)
            return render(request, "frequencia/online.html", {
                "inscricao": inscricao, "programacao": programacao,
                "confirmada": True,
                "link_evento": programacao.link or inscricao.atividade.link,
            })
        except ValidationError as exc:
            erro = " ".join(exc.messages)
    return render(request, "frequencia/online.html", {"inscricao": inscricao, "programacao": programacao, "erro": erro, "acesso_liberado": acesso_liberado})
