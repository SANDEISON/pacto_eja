from django import forms


class BootstrapFormMixin:
    """Aplica automaticamente as classes Bootstrap adequadas a cada widget."""

    def _apply_bootstrap_classes(self):
        """Mantém classes existentes e acrescenta o estilo conforme o tipo de campo."""
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.RadioSelect, forms.CheckboxSelectMultiple)):
                css_class = "certificate-options"
            elif isinstance(widget, forms.CheckboxInput):
                css_class = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css_class = "form-select"
            else:
                css_class = "form-control"
            widget.attrs["class"] = f'{widget.attrs.get("class", "")} {css_class}'.strip()
