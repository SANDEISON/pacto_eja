from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Value
from django.db.models.functions import Concat
from django.http import FileResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from ..models import Atividade, Credenciamento, Inscricao
from ..services.credenciamento_pdf import gerar_lista_credenciamento


@login_required
@permission_required("core.view_credenciamento", raise_exception=True)
def atividade_credenciamento_pdf(request, pk):
    atividade = get_object_or_404(Atividade, pk=pk)
    inscricoes = Inscricao.objects.filter(
        atividade=atividade, modalidade=Inscricao.Modalidade.PRESENCIAL,
    ).select_related("usuario__educador")
    return FileResponse(
        gerar_lista_credenciamento(atividade, inscricoes), as_attachment=True,
        filename=f"lista-credenciamento-{atividade.pk}.pdf", content_type="application/pdf",
    )


@login_required
@permission_required("core.view_credenciamento", raise_exception=True)
def atividade_credenciamento(request, pk):
    atividade = get_object_or_404(Atividade, pk=pk)
    termo = " ".join(request.GET.get("q", "").split())
    status = request.GET.get("status", "")
    if status not in ("pendente", "credenciado"):
        status = ""
    if request.method == "POST":
        if not request.user.has_perm("core.add_credenciamento"):
            raise PermissionDenied
        acao = request.POST.get("acao", "credenciar")
        if acao not in ("credenciar", "confirmar_cancelamento", "cancelar"):
            return HttpResponseBadRequest("Ação de credenciamento inválida.")
        with transaction.atomic():
            inscricao = get_object_or_404(
                Inscricao.objects.select_for_update(), pk=request.POST.get("inscricao")
                if request.POST.get("inscricao", "").isdecimal() else None,
                atividade=atividade, modalidade=Inscricao.Modalidade.PRESENCIAL,
            )
            if acao == "confirmar_cancelamento":
                get_object_or_404(Credenciamento, inscricao=inscricao)
                return render(request, "management/credenciamento_cancelar.html", {
                    "atividade": atividade, "inscricao": inscricao,
                    "voltar_url": f'{reverse("atividade_credenciamento", args=[pk])}?{urlencode({"q": termo, "status": status})}',
                })
            if acao == "cancelar":
                excluidos, _ = Credenciamento.objects.filter(inscricao=inscricao).delete()
                if excluidos:
                    messages.success(request, "Credenciamento cancelado. O participante voltou para a situação pendente.")
                else:
                    messages.info(request, "Este participante já está sem credenciamento.")
            elif not atividade.ativo:
                messages.error(request, "O evento está inativo. Não é possível credenciar participantes.")
            else:
                registro, criado = Credenciamento.objects.get_or_create(
                    inscricao=inscricao, defaults={"registrado_por": request.user},
                )
                if criado:
                    messages.success(request, "Credenciamento confirmado com sucesso.")
                else:
                    messages.info(request, "Este participante já está credenciado. O registro original foi mantido.")
        return redirect(f'{reverse("atividade_credenciamento", args=[pk])}?{urlencode({"q": termo, "status": status})}')

    inscritos = Inscricao.objects.filter(atividade=atividade, modalidade=Inscricao.Modalidade.PRESENCIAL)
    total = inscritos.count()
    credenciados = inscritos.filter(credenciamento__isnull=False).count()
    participantes = inscritos.select_related(
        "usuario__educador", "credenciamento__registrado_por",
    ).prefetch_related("programacoes__sala", "refeicoes").annotate(
        nome_completo=Concat("usuario__first_name", Value(" "), "usuario__last_name"),
    ).order_by("usuario__first_name", "usuario__last_name", "pk")
    if termo:
        filtro = Q(nome_completo__icontains=termo) | Q(usuario__educador__nome_completo__icontains=termo)
        cpf = "".join(c for c in termo if c.isdecimal())
        if cpf and all(c.isdecimal() or c in ".- " for c in termo):
            filtro |= Q(usuario__educador__cpf__icontains=cpf)
        participantes = participantes.filter(filtro)
    if status:
        participantes = participantes.filter(credenciamento__isnull=status == "pendente")
    pagina = Paginator(participantes, 30).get_page(request.GET.get("page"))
    return render(request, "management/atividade_credenciamento.html", {
        "atividade": atividade, "page_obj": pagina, "total": total,
        "credenciados": credenciados, "pendentes": total - credenciados,
        "search_query": termo, "status": status,
        "filtros": urlencode({"q": termo, "status": status}),
    })
