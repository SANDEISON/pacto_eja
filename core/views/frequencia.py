import secrets
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..models import Atividade, ChamadaFrequencia, Frequencia, Inscricao, ProgramacaoSala
from ..services.frequencia import pode_operar, registrar


@login_required
def frequencia_index(request):
    programacoes = ProgramacaoSala.objects.select_related("sala", "responsavel").prefetch_related("atividades").filter(atividades__isnull=False).distinct()
    if not request.user.has_perm("core.add_frequencia"):
        programacoes = programacoes.filter(responsavel=request.user)
    pares = [(atividade, p) for p in programacoes for atividade in p.atividades.all()]
    inscricoes = Inscricao.objects.filter(usuario=request.user).select_related("atividade").prefetch_related("programacoes__sala", "frequencias__programacao__sala")
    return render(request, "frequencia/index.html", {"pares": pares, "inscricoes": inscricoes})


@login_required
def frequencia_sala(request, pk, programacao_pk):
    atividade = get_object_or_404(Atividade, pk=pk)
    programacao = get_object_or_404(atividade.programacoes.select_related("sala", "responsavel"), pk=programacao_pk)
    if not pode_operar(request.user, programacao):
        raise PermissionDenied
    if request.method == "POST":
        try:
            acao = request.POST.get("acao")
            if acao == "abrir":
                minutos = int(request.POST.get("minutos", "30"))
                if not 1 <= minutos <= 720:
                    raise ValueError
                if timezone.localdate() != programacao.data:
                    raise ValidationError("Abra a chamada na data da programação.")
                if not atividade.ativo:
                    raise ValidationError("O evento está inativo.")
                with transaction.atomic():
                    ProgramacaoSala.objects.select_for_update().get(pk=programacao.pk)
                    ChamadaFrequencia.objects.filter(atividade=atividade, programacao=programacao, encerrada_em__isnull=True).update(encerrada_em=timezone.now())
                    ChamadaFrequencia.objects.create(
                        atividade=atividade, programacao=programacao, responsavel=request.user,
                        expira_em=timezone.now() + timedelta(minutes=minutos),
                        codigo=secrets.token_hex(4).upper() if programacao.modalidade == "online" else "",
                    )
                messages.success(request, "Chamada aberta. A abertura de uma nova chamada invalida o código anterior.")
            elif acao == "encerrar":
                with transaction.atomic():
                    chamada = get_object_or_404(ChamadaFrequencia.objects.select_for_update(), pk=request.POST.get("chamada"), atividade=atividade, programacao=programacao)
                    chamada.encerrada_em = timezone.now()
                    chamada.save(update_fields=["encerrada_em"])
                messages.success(request, "Chamada encerrada.")
            elif acao == "manual" and programacao.modalidade == "presencial":
                chamada = get_object_or_404(ChamadaFrequencia, pk=request.POST.get("chamada"), atividade=atividade, programacao=programacao)
                inscricao = get_object_or_404(Inscricao, pk=request.POST.get("inscricao"), atividade=atividade, programacoes=programacao)
                _, criada = registrar(inscricao, chamada, request.user, Frequencia.Metodo.MANUAL)
                messages.success(request, "Presença registrada." if criada else "Presença já registrada.")
        except (ValidationError, ValueError) as erro:
            messages.error(request, " ".join(erro.messages) if isinstance(erro, ValidationError) else "Informe um prazo entre 1 e 720 minutos.")
        return redirect("frequencia_sala", pk=pk, programacao_pk=programacao_pk)
    chamada = ChamadaFrequencia.objects.filter(atividade=atividade, programacao=programacao).order_by("-aberta_em", "-pk").first()
    inscricoes = Inscricao.objects.filter(atividade=atividade, programacoes=programacao).select_related("usuario").order_by("usuario__first_name", "usuario__username")
    if request.GET.get("q"):
        q = request.GET["q"]
        inscricoes = inscricoes.filter(Q(usuario__first_name__icontains=q) | Q(usuario__last_name__icontains=q) | Q(usuario__email__icontains=q))
    registros = Frequencia.objects.filter(inscricao__atividade=atividade, programacao=programacao).select_related("inscricao__usuario", "registrada_por")
    presentes = set(registros.values_list("inscricao_id", flat=True))
    return render(request, "frequencia/sala.html", {"atividade": atividade, "programacao": programacao, "chamada": chamada, "participantes": [(i, i.pk in presentes) for i in inscricoes], "registros": registros})


@login_required
def frequencia_validar(request, token):
    try:
        pk = signing.Signer(salt="frequencia.inscricao").unsign(token)
        if not pk.isdecimal():
            raise signing.BadSignature
    except signing.BadSignature:
        return render(request, "frequencia/validar.html", {"erro": "QR Code inválido."}, status=400)
    inscricao = get_object_or_404(Inscricao.objects.select_related("usuario", "atividade"), pk=pk)
    chamadas = list(ChamadaFrequencia.objects.filter(
        atividade=inscricao.atividade, programacao__in=inscricao.programacoes.all(),
        programacao__modalidade="presencial", encerrada_em__isnull=True,
        aberta_em__lte=timezone.now(), expira_em__gt=timezone.now(),
    ).select_related("programacao__sala"))
    chamadas = [c for c in chamadas if pode_operar(request.user, c.programacao)]
    # Não expõe os dados nominais do participante para quem apenas possui o QR.
    if not chamadas:
        raise PermissionDenied("Nenhuma chamada presencial aberta sob sua responsabilidade para esta inscrição.")
    if request.method == "POST":
        chamada = next((c for c in chamadas if str(c.pk) == request.POST.get("chamada")), None)
        if chamada is None:
            raise PermissionDenied
        try:
            _, criada = registrar(inscricao, chamada, request.user, Frequencia.Metodo.QR)
            messages.success(request, "Presença registrada." if criada else "Presença já registrada.")
        except ValidationError as erro:
            messages.error(request, " ".join(erro.messages))
        return redirect("frequencia_sala", pk=inscricao.atividade_id, programacao_pk=chamada.programacao_id)
    return render(request, "frequencia/validar.html", {"inscricao": inscricao, "chamadas": chamadas})


@login_required
def frequencia_online(request, pk, programacao_pk):
    inscricao = get_object_or_404(Inscricao, atividade_id=pk, usuario=request.user, modalidade="online", programacoes__pk=programacao_pk)
    programacao = get_object_or_404(inscricao.atividade.programacoes, pk=programacao_pk, modalidade="online")
    erro = ""
    if request.method == "POST":
        codigo = request.POST.get("codigo", "").strip().upper()
        chamada = ChamadaFrequencia.objects.filter(
            atividade_id=pk, programacao=programacao, codigo=codigo,
            encerrada_em__isnull=True, aberta_em__lte=timezone.now(), expira_em__gt=timezone.now(),
        ).order_by("-pk").first() if codigo else None
        if chamada is None:
            erro = "Código inválido, expirado ou de outra programação."
        else:
            try:
                _, criada = registrar(inscricao, chamada, request.user, Frequencia.Metodo.ONLINE, codigo=codigo)
                messages.success(request, "Presença confirmada." if criada else "Presença já confirmada.")
                return redirect("frequencia_index")
            except ValidationError as exc:
                erro = " ".join(exc.messages)
    return render(request, "frequencia/online.html", {"inscricao": inscricao, "programacao": programacao, "erro": erro})
