import os
import sys
import random
import datetime

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pacto_eja.settings")
django.setup()

from django.contrib.auth import get_user_model
from core.models import (
    Educador,
    EducadorEscola,
    FuncaoEducador,
    EducadorGenero,
    CorRaca,
    EducadorEstadoCivil,
    Cidade,
    Escola,
    Funcao,
    FuncaoCaracterizacaoTurma,
    CursoCertificado
)

User = get_user_model()

def gen_cpf():
    while True:
        digits = [random.randint(0, 9) for _ in range(9)]
        if len(set(digits)) == 1:
            continue
        s1 = sum(digits[i] * (10 - i) for i in range(9))
        d1 = (s1 * 10 % 11) % 10
        digits.append(d1)
        s2 = sum(digits[i] * (11 - i) for i in range(10))
        d2 = (s2 * 10 % 11) % 10
        digits.append(d2)
        cpf = ''.join(str(x) for x in digits)
        if not Educador.objects.filter(cpf=cpf).exists():
            return cpf

SAMPLE_NAMES = [
    ("Carlos Eduardo", "Medeiros", "Carlos Medeiros"),
    ("Fernanda Maria", "Albuquerque", ""),
    ("Gabriel Henrique", "Santos", "Gabriel Santos"),
    ("Juliana Paes", "Nogueira", ""),
    ("Lucas Ramon", "Oliveira", "Lucas Oliveira"),
    ("Beatriz Souza", "Cavalcanti", ""),
    ("Thiago Augusto", "Ferreira", "Thiago Ferreira"),
    ("Amanda Cristina", "Ribeiro", ""),
    ("Rodrigo Antonio", "Martins", "Rodrigo Martins"),
    ("Patricia Helena", "Gomes", ""),
    ("Rafael Barbosa", "Lima", "Rafael Lima"),
    ("Camila Rocha", "Vasconcelos", ""),
    ("Diego Vinicius", "Melo", "Diego Melo"),
    ("Vanessa Araujo", "Teixeira", ""),
    ("Bruno Cesar", "Carvalho", "Bruno Carvalho")
]

# Fetch Catalog Options
generos = list(EducadorGenero.objects.all())
cores = list(CorRaca.objects.all())
estados_civis = list(EducadorEstadoCivil.objects.all())
funcoes = list(Funcao.objects.all())
funcoes_turma = list(FuncaoCaracterizacaoTurma.objects.all())
cursos = list(CursoCertificado.objects.all())

# Preferred cities for rich data (Paraíba and neighbouring states)
cidades_alvo = list(Cidade.objects.filter(estado__sigla__in=["PB", "PE", "RN", "SP", "RJ", "BA"]).select_related("estado"))
if not cidades_alvo:
    cidades_alvo = list(Cidade.objects.select_related("estado")[:50])

tempos_atuacao = ["0_3_anos", "4_6_anos", "mais_6_anos"]

print("Iniciando população de 15 educadores completos...")
created_count = 0

for first_name, last_name, nome_social in SAMPLE_NAMES:
    nome_completo = f"{first_name} {last_name}"
    username_base = f"{first_name.split()[0].lower()}.{last_name.lower()}"
    username = username_base
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{username_base}{counter}"
        counter += 1

    email = f"{username}@educador.pacto.gov.br"
    
    # 1. Create User (signal automatically creates Educador profile)
    user = User.objects.create_user(
        username=username,
        email=email,
        password="PactoEja2026!",
        first_name=first_name,
        last_name=last_name
    )

    # Birth date between 1970 and 2002
    year = random.randint(1970, 2002)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    birth_date = datetime.date(year, month, day)

    # Phone
    ddd = random.choice([83, 81, 84, 11, 21, 71])
    num = random.randint(980000000, 999999999)
    telefone = f"({ddd}) {str(num)[:5]}-{str(num)[5:]}"

    genero_obj = random.choice(generos) if generos else None
    cor_obj = random.choice(cores) if cores else None
    estado_civil_obj = random.choice(estados_civis) if estados_civis else None

    # 2. Get and update Educador profile
    educador, _ = Educador.objects.get_or_create(usuario=user)
    educador.nome_completo = nome_completo
    educador.nome_social = nome_social
    educador.cpf = gen_cpf()
    educador.data_nascimento = birth_date
    educador.genero = genero_obj
    educador.telefone = telefone
    educador.estado_civil = estado_civil_obj
    educador.cor_raca = cor_obj
    educador.save()

    if cursos:
        selected_cursos = random.sample(cursos, k=random.randint(1, len(cursos)))
        educador.cursos_certificados.set(selected_cursos)

    # 3. Create EducadorEscola link
    cidade_obj = random.choice(cidades_alvo)
    escola_qs = None
    if cidade_obj.codigo_ibge:
        escola_qs = Escola.objects.filter(id_municipio=cidade_obj.codigo_ibge)
    
    if not escola_qs or not escola_qs.exists():
        escola_qs = Escola.objects.filter(sigla_uf=cidade_obj.estado.sigla)

    if not escola_qs.exists():
        escola_qs = Escola.objects.all()

    escola_obj = random.choice(list(escola_qs[:30]))
    funcao_obj = random.choice(funcoes) if funcoes else None
    funcao_turma_obj = random.choice(funcoes_turma) if funcoes_turma else None
    tempo_val = random.choice(tempos_atuacao)

    vinculo = EducadorEscola.objects.create(
        cidade=cidade_obj,
        escola=escola_obj,
        funcao=funcao_obj,
        funcao_caracterizacao_turmas=funcao_turma_obj,
        tempo_atuacao=tempo_val
    )

    # 4. Create FuncaoEducador relation
    FuncaoEducador.objects.create(
        educador=educador,
        educador_escola=vinculo
    )

    created_count += 1
    print(f"[{created_count}/15] Criado: {nome_completo} | CPF: {educador.cpf} | Cidade: {cidade_obj.nome_cidade} - {cidade_obj.estado.sigla} | Escola: {escola_obj.nome}")

print("Concluído com sucesso! 15 novos educadores completos inseridos no banco de dados.")
