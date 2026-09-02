from django.db import models


class CursoCertificado(models.Model):
    nome = models.CharField("curso", max_length=150, unique=True)

    class Meta:
        db_table = "Curso_Certificado"
        verbose_name = "curso para certificado"
        verbose_name_plural = "cursos para certificados"
        ordering = ("id",)

    def __str__(self):
        return self.nome
