from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.db.models import Count, F

from core.models import (
    EducadorEscola,
    Escola,
    Estado,
    Cidade,
    Educador,
    Funcao,
    FuncaoCaracterizacaoTurma,
)

# Only staff users can access the reports page
staff_required = user_passes_test(lambda u: u.is_authenticated and u.is_staff)

@method_decorator(staff_required, name="dispatch")
class ReportsView(TemplateView):
    template_name = "reports.html"

    def get_context_data(self, **kwargs):
        import json
        ctx = super().get_context_data(**kwargs)

        # KPI Summary Stats
        ctx["total_educadores"] = Educador.objects.count()
        ctx["total_vinculos"] = EducadorEscola.objects.count()
        ctx["total_escolas"] = EducadorEscola.objects.values('escola').distinct().count()
        ctx["total_municipios"] = EducadorEscola.objects.values('cidade').distinct().count()

        # Raw querysets
        ctx["participantes_por_municipio"] = (
            EducadorEscola.objects.values(city_name=F('cidade__nome_cidade'))
            .annotate(qtd=Count('id'))
            .order_by('-qtd')
        )
        ctx["participantes_por_escola"] = (
            EducadorEscola.objects.values(escola_name=F('escola__nome'))
            .annotate(qtd=Count('id'))
            .order_by('-qtd')
        )
        ctx["participantes_por_estado"] = (
            EducadorEscola.objects.values(state_name=F('cidade__estado__nome_estado'))
            .annotate(qtd=Count('id'))
            .order_by('-qtd')
        )
        ctx["tempo_atuacao"] = (
            EducadorEscola.objects.values('tempo_atuacao')
            .annotate(qtd=Count('id'))
            .order_by('-qtd')
        )
        ctx["genero"] = (
            Educador.objects.values(genero_desc=F('genero__nome'))
            .annotate(qtd=Count('id'))
            .order_by('-qtd')
        )
        ctx["cor_raca"] = (
            Educador.objects.values(cor=F('cor_raca__nome'))
            .annotate(qtd=Count('id'))
            .order_by('-qtd')
        )
        ctx["funcao"] = (
            EducadorEscola.objects.values(funcao_desc=F('funcao__nome'))
            .annotate(qtd=Count('id'))
            .order_by('-qtd')
        )

        def normalize(qs, key_name, map_dict=None):
            res = []
            for item in list(qs):
                raw = item.get(key_name)
                if map_dict and raw in map_dict:
                    val = map_dict[raw]
                elif not raw:
                    val = "Não informado"
                else:
                    val = str(raw)
                res.append({"label": val, "qtd": item["qtd"]})
            return res

        tempo_map = {
            "0_3_anos": "0 a 3 anos",
            "4_6_anos": "4 a 6 anos",
            "mais_6_anos": "Mais de 6 anos",
        }

        # Serialize datasets into clean uniform JSON structures
        ctx['municipio_json'] = json.dumps(normalize(ctx['participantes_por_municipio'], 'city_name'))
        ctx['escola_json'] = json.dumps(normalize(ctx['participantes_por_escola'], 'escola_name'))
        ctx['estado_json'] = json.dumps(normalize(ctx['participantes_por_estado'], 'state_name'))
        ctx['genero_json'] = json.dumps(normalize(ctx['genero'], 'genero_desc'))
        ctx['cor_json'] = json.dumps(normalize(ctx['cor_raca'], 'cor'))
        ctx['funcao_json'] = json.dumps(normalize(ctx['funcao'], 'funcao_desc'))
        ctx['tempo_json'] = json.dumps(normalize(ctx['tempo_atuacao'], 'tempo_atuacao', tempo_map))

        return ctx

# Expose as a view function for URLconf
reports = ReportsView.as_view()
