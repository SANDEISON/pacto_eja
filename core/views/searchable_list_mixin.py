from django.db.models import Q


class SearchableListMixin:
    """Adiciona busca textual por ``?q=`` e paginação às listagens genéricas."""
    paginate_by = 20
    search_fields = ()

    def get_queryset(self):
        """Combina os campos configurados com OR e filtra o queryset base."""
        queryset = super().get_queryset()
        query = self.request.GET.get("q", "").strip()
        if query:
            filters = Q()
            for field in self.search_fields:
                filters |= Q(**{f"{field}__icontains": query})
            queryset = queryset.filter(filters)
        return queryset

    def get_context_data(self, **kwargs):
        """Mantém o termo pesquisado disponível para o campo no template."""
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "").strip()
        return context
