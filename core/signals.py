from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Educador


@receiver(post_save, sender=get_user_model())
def create_user_profile(sender, instance, created, **kwargs):
    nome_completo = instance.get_full_name().strip() or instance.get_username()
    if created:
        Educador.objects.get_or_create(
            usuario=instance,
            defaults={"nome_completo": nome_completo},
        )
    else:
        Educador.objects.filter(usuario=instance).exclude(nome_completo=nome_completo).update(
            nome_completo=nome_completo,
        )
