from django import forms


class UserNameChoiceField(forms.ModelChoiceField):
    """Exibe o nome do usuário sem expor seu CPF usado como login."""

    def label_from_instance(self, usuario):
        return usuario.get_full_name().strip() or usuario.email or f"Usuário #{usuario.pk}"
