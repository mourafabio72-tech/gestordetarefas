import os
import re
from sqlalchemy import inspect, text
from .database import engine, SessionLocal
from .models import Usuario
from .auth import get_password_hash

# A lista vive fora da funcao para a prova poder conferir o schema final contra
# ela, e para o `migrate` poder receber outra no lugar.
MIGRACOES = [
    ("telefone", "ALTER TABLE usuarios ADD COLUMN telefone VARCHAR(20)"),
    ("gestor_id", "ALTER TABLE usuarios ADD COLUMN gestor_id INTEGER REFERENCES usuarios(id)"),
    ("grupo", "ALTER TABLE usuarios ADD COLUMN grupo VARCHAR(20) DEFAULT 'usuario'"),
    ("data_vencimento", "ALTER TABLE tarefas ADD COLUMN data_vencimento TIMESTAMP"),
    ("gera_multa", "ALTER TABLE tarefas ADD COLUMN gera_multa BOOLEAN DEFAULT FALSE"),
    ("regime_tributario", "ALTER TABLE empresas ADD COLUMN regime_tributario VARCHAR(30) DEFAULT 'indefinido'"),
    ("segmento", "ALTER TABLE empresas ADD COLUMN segmento VARCHAR(30)"),
    ("data_prazo_nullable", "ALTER TABLE tarefas ALTER COLUMN data_prazo DROP NOT NULL"),
    ("permissoes", "ALTER TABLE usuarios ADD COLUMN permissoes TEXT"),
    ("obrigacao_id", "ALTER TABLE tarefas ADD COLUMN obrigacao_id INTEGER REFERENCES obrigacoes(id)"),
    ("competencia", "ALTER TABLE tarefas ADD COLUMN competencia VARCHAR(7)"),
    ("identificadores", "ALTER TABLE obrigacoes ADD COLUMN identificadores VARCHAR(200)"),
    ("sentido", "ALTER TABLE obrigacoes ADD COLUMN sentido VARCHAR(10) DEFAULT 'receber'"),
    ("identificadores_maior", "ALTER TABLE obrigacoes ALTER COLUMN identificadores TYPE VARCHAR(2000)"),
    ("saida_nome", "ALTER TABLE tarefas ADD COLUMN saida_nome VARCHAR(200)"),
    ("saida_token", "ALTER TABLE tarefas ADD COLUMN saida_token VARCHAR(64)"),
    ("saida_baixada_em", "ALTER TABLE tarefas ADD COLUMN saida_baixada_em TIMESTAMP"),
    ("saida_downloads", "ALTER TABLE tarefas ADD COLUMN saida_downloads INTEGER DEFAULT 0"),
    ("acesso_contado", "ALTER TABLE saida_acessos ADD COLUMN contado BOOLEAN DEFAULT TRUE"),
    ("acesso_envio", "ALTER TABLE saida_acessos ADD COLUMN envio_id INTEGER REFERENCES tarefa_envios(id)"),
    ("envio_token", "ALTER TABLE tarefa_envios ADD COLUMN token VARCHAR(64)"),
    ("protocolo_entrega", "ALTER TABLE tarefas ADD COLUMN protocolo_entrega VARCHAR(120)"),
    ("data_entrega", "ALTER TABLE tarefas ADD COLUMN data_entrega TIMESTAMP"),
    ("anexo_nome", "ALTER TABLE tarefas ADD COLUMN anexo_nome VARCHAR(200)"),
    ("usuario_tipo", "ALTER TABLE usuarios ADD COLUMN tipo VARCHAR(20) DEFAULT 'colaborador'"),
    ("usuario_empresa_id", "ALTER TABLE usuarios ADD COLUMN empresa_id INTEGER REFERENCES empresas(id)"),
    ("tarefa_supervisor_id", "ALTER TABLE tarefas ADD COLUMN supervisor_id INTEGER REFERENCES usuarios(id)"),
    ("obrigacao_supervisor_id", "ALTER TABLE obrigacoes ADD COLUMN supervisor_id INTEGER REFERENCES usuarios(id)"),
    ("empresa_responsavel_id", "ALTER TABLE empresas ADD COLUMN responsavel_id INTEGER REFERENCES usuarios(id)"),
    ("empresa_supervisor_id", "ALTER TABLE empresas ADD COLUMN supervisor_id INTEGER REFERENCES usuarios(id)"),
    ("empresa_bloqueado", "ALTER TABLE empresas ADD COLUMN bloqueado BOOLEAN DEFAULT FALSE"),
    ("usuario_bloqueado", "ALTER TABLE usuarios ADD COLUMN bloqueado BOOLEAN DEFAULT FALSE"),
    # setor virou interno/global: relaxa o NOT NULL antigo em produção
    ("setor_empresa_nullable", "ALTER TABLE setores ALTER COLUMN empresa_id DROP NOT NULL"),
    ("empresa_grupo", "ALTER TABLE empresas ADD COLUMN grupo VARCHAR(80)"),
    ("tarefa_upload_token", "ALTER TABLE tarefas ADD COLUMN upload_token VARCHAR(64)"),
    ("usuario_setor_id", "ALTER TABLE usuarios ADD COLUMN setor_id INTEGER REFERENCES setores(id)"),
    ("usuario_convite_token", "ALTER TABLE usuarios ADD COLUMN convite_token VARCHAR(64)"),
    ("usuario_ativado", "ALTER TABLE usuarios ADD COLUMN ativado BOOLEAN"),
    ("obrigacao_exige_documento", "ALTER TABLE obrigacoes ADD COLUMN exige_documento BOOLEAN"),
    ("fechamento_cliente", "ALTER TABLE tarefas ADD COLUMN fechamento_cliente DATE"),
    ("alvo_modo", "ALTER TABLE obrigacoes ADD COLUMN alvo_modo VARCHAR(12) DEFAULT 'regra'"),
    ("setor_gestor_id", "ALTER TABLE setores ADD COLUMN gestor_id INTEGER REFERENCES usuarios(id)"),
    ("fechamento_tipo", "ALTER TABLE empresas ADD COLUMN fechamento_tipo VARCHAR(20)"),
    ("fechamento_dia", "ALTER TABLE empresas ADD COLUMN fechamento_dia INTEGER"),
    ("ancora", "ALTER TABLE obrigacoes ADD COLUMN ancora VARCHAR(20)"),
    ("ancora_dias_antes", "ALTER TABLE obrigacoes ADD COLUMN ancora_dias_antes INTEGER DEFAULT 0"),
    ("ancora_tipo_dias", "ALTER TABLE obrigacoes ADD COLUMN ancora_tipo_dias VARCHAR(10) DEFAULT 'uteis'"),
    # "Não se aplica a esta empresa": a tarefa vai para CANCELADA e estes
    # campos dizem que foi decisão, e não desistência.
    ("nao_se_aplica", "ALTER TABLE tarefas ADD COLUMN nao_se_aplica BOOLEAN DEFAULT FALSE"),
    ("nao_se_aplica_motivo", "ALTER TABLE tarefas ADD COLUMN nao_se_aplica_motivo TEXT"),
    ("nao_se_aplica_por_id", "ALTER TABLE tarefas ADD COLUMN nao_se_aplica_por_id INTEGER REFERENCES usuarios(id)"),
    ("nao_se_aplica_em", "ALTER TABLE tarefas ADD COLUMN nao_se_aplica_em TIMESTAMP"),
]

_ADD = re.compile(r"ALTER TABLE (\w+) ADD COLUMN (\w+)", re.I)
_DROP_NOT_NULL = re.compile(
    r"ALTER TABLE (\w+) ALTER COLUMN (\w+) DROP NOT NULL", re.I)
_TIPO_MAIOR = re.compile(
    r"ALTER TABLE (\w+) ALTER COLUMN (\w+) TYPE VARCHAR\((\d+)\)", re.I)


def _colunas(insp, tabela, cache):
    """Colunas de uma tabela, lidas UMA vez por tabela e guardadas."""
    if tabela not in cache:
        cache[tabela] = {c["name"]: c for c in insp.get_columns(tabela)}
    return cache[tabela]


def _precisa_rodar(insp, sql, cache, tabelas):
    """Pergunta ao banco se esta migracao ainda tem o que fazer.

    Perguntar antes e o que troca dezenas de `ERROR: column ... already exists`
    por silencio. Nao e frescura de log: erro de migracao de VERDADE morava no
    meio dessas linhas, e por isso ninguem olhava nenhuma.

    Nao usa `ADD COLUMN IF NOT EXISTS` de proposito. As provas deste projeto
    rodam em SQLite, que nao aceita essa forma, e a suite inteira quebraria. O
    `inspect` do SQLAlchemy ja vem instalado e responde pelos dois bancos.
    """
    if _TIPO_MAIOR.search(sql) and engine.dialect.name == "sqlite":
        # SQLite nao aceita `ALTER COLUMN ... TYPE`, e tambem nao IMPOE o tamanho
        # declarado num VARCHAR: o tipo ali e afinidade, nao limite. Entao nao ha
        # o que fazer, e tentar so produz o mesmo erro de sintaxe a cada boot,
        # para sempre, porque a coluna nunca cresce. Achado de verificador
        # adversarial em 2026-09-09, num banco antigo restaurado em SQLite.
        return False

    # A assimetria abaixo e deliberada, e vale dizer qual e: quando a COLUNA
    # falta, o `ADD COLUMN` roda (e o que ele existe para fazer) e os outros dois
    # pulam em silencio. Relaxar `NOT NULL` ou aumentar um VARCHAR de coluna que
    # nao existe nao e erro a reportar: e migracao orfa, como a
    # `setor_empresa_nullable`, cuja coluna saiu do model. Reportar aquilo seria
    # a linha de erro falso que esta fase veio tirar do log. O preco, declarado:
    # migracao de tipo cuja coluna DEVERIA existir some sem aviso.
    for regex, decidir in (
        (_ADD, lambda m, cols: m.group(2) not in cols),
        # `nullable` e o tipo vem no mesmo `get_columns`, entao as tres
        # migracoes que nao sao ADD COLUMN respondem pelo mesmo caminho.
        (_DROP_NOT_NULL,
         lambda m, cols: m.group(2) in cols and not cols[m.group(2)].get("nullable", True)),
        (_TIPO_MAIOR, lambda m, cols: (
            m.group(2) in cols
            and (getattr(cols[m.group(2)]["type"], "length", None) or 0) < int(m.group(3))
            and getattr(cols[m.group(2)]["type"], "length", None) is not None)),
    ):
        m = regex.search(sql)
        if m:
            if m.group(1).lower() not in tabelas:
                # Tabela que nao existe: NAO se pula em silencio. Do lado do
                # banco, tabela sumida por engano e tabela que nunca existiu sao
                # a mesma coisa, e pular as duas trocaria erro falso por erro
                # ESCONDIDO, que e pior. Deixa rodar, e o log diz o que houve.
                return True
            return decidir(m, _colunas(insp, m.group(1), cache))
    # Forma que este codigo nao conhece: tenta, e o erro aparece no log.
    return True


def migrate(migracoes=None):
    """Aplica so o que falta, e cala a boca sobre o que ja esta feito."""
    migracoes = MIGRACOES if migracoes is None else migracoes
    insp = inspect(engine)
    tabelas = {t.lower() for t in insp.get_table_names()}
    cache = {}

    for col_name, sql in migracoes:
        if not _precisa_rodar(insp, sql, cache, tabelas):
            continue
        with engine.begin() as conn:
            try:
                conn.execute(text(sql))
                print(f"Coluna '{col_name}' adicionada com sucesso!")
            except Exception as e:
                # A rede continua aqui: dois containers subindo ao mesmo tempo
                # podem disputar a mesma migracao, e quem perder a corrida ve o
                # erro do banco. Raro, e honesto de registrar quando acontece.
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print(f"Coluna '{col_name}' já existe.")
                else:
                    print(f"Erro na coluna '{col_name}': {e}")
        cache.pop(_tabela_do_sql(sql), None)


def _tabela_do_sql(sql):
    m = re.search(r"ALTER TABLE (\w+)", sql, re.I)
    return m.group(1) if m else None


def alcance_do_alerta():
    """Fecha o alcance do alerta para responsável + supervisor. Roda uma vez.

    Precisa existir porque a configuração vive no BANCO: mudar o default no
    código não alcança quem já salvou a tela alguma vez, e em produção estava
    gravado `alert_gestor_niveis=2`. Sem isto, o novo padrão valeria só para
    instalação nova.

    A chave `alert_cliente` é o marcador de que esta leva já passou: existindo
    ela, nada é tocado -- assim quem depois decidir religar a cópia dos gestores
    não vê a escolha ser desfeita no próximo deploy.
    """
    db = SessionLocal()
    try:
        from .models import Configuracao
        ja_rodou = db.query(Configuracao).filter(Configuracao.chave == "alert_cliente").first()
        if ja_rodou:
            return
        db.add(Configuracao(chave="alert_cliente", valor="0"))
        niveis = db.query(Configuracao).filter(
            Configuracao.chave == "alert_gestor_niveis").first()
        if niveis:
            niveis.valor = "0"
        else:
            db.add(Configuracao(chave="alert_gestor_niveis", valor="0"))
        db.commit()
        print("Alcance do alerta fechado em responsável + supervisor.")
    except Exception as e:
        print(f"Erro ao ajustar o alcance do alerta: {e}")
        db.rollback()
    finally:
        db.close()


def horarios_por_faixa():
    """Converte os horários antigos (principal/extra) para os das três faixas.

    Roda uma vez, e preserva o que o escritório já tinha escolhido em vez de
    impor o padrão novo: quem definiu "09:30,17:45" tinha razão para isso.
    A conversão distribui esses mesmos horários pelo perfil de cada faixa --
    planejamento no primeiro do dia, o que vence hoje em todos, cobrança no
    último. Já reduz sozinha, porque os horários "extra" deixam de existir como
    disparo separado de tudo.

    A chave `horarios_a_vencer` marca que esta leva já passou, então quem depois
    reajustar na tela não vê a escolha ser desfeita no próximo deploy.
    """
    db = SessionLocal()
    try:
        from .models import Configuracao
        if db.query(Configuracao).filter(Configuracao.chave == "horarios_a_vencer").first():
            return
        antigos = {c.chave: c.valor for c in db.query(Configuracao).filter(
            Configuracao.chave.in_(["horarios_principal", "horarios_extra"])).all()}
        principais = [h.strip() for h in (antigos.get("horarios_principal") or "").split(",") if h.strip()]
        if principais:
            novos = {"horarios_a_vencer": principais[0],
                     "horarios_vence_hoje": ",".join(principais),
                     "horarios_atrasada": principais[-1]}
        else:
            novos = {"horarios_a_vencer": "09:00",
                     "horarios_vence_hoje": "09:30,15:00",
                     "horarios_atrasada": "17:45"}
        for chave, valor in novos.items():
            db.add(Configuracao(chave=chave, valor=valor))
        # As chaves antigas não são mais lidas por ninguém; deixá-las no banco
        # só confundiria quem for depurar a configuração amanhã.
        for c in db.query(Configuracao).filter(
                Configuracao.chave.in_(["horarios_principal", "horarios_extra"])).all():
            db.delete(c)
        db.commit()
        print(f"Horários por faixa: {novos}")
    except Exception as e:
        print(f"Erro ao converter os horários por faixa: {e}")
        db.rollback()
    finally:
        db.close()


def criar_indices():
    """Índices das colunas por que se filtra e se ordena.

    `Base.metadata.create_all` só cria tabela que não existe -- em base já
    criada, marcar `index=True` no model não faz nada. Por isso os índices
    entram aqui, no mesmo mecanismo idempotente das colunas.

    `tarefas` é a tabela grande e a mais consultada, e não tinha índice em
    nenhuma chave estrangeira: toda listagem filtrada por empresa, setor ou
    responsável varria a tabela inteira. `CREATE INDEX IF NOT EXISTS` funciona
    tanto no Postgres do servidor quanto no SQLite local.
    """
    indices = [
        # tarefas: filtros da listagem e do escopo por responsável
        ("ix_tarefas_empresa_id",     "CREATE INDEX IF NOT EXISTS ix_tarefas_empresa_id ON tarefas (empresa_id)"),
        ("ix_tarefas_setor_id",       "CREATE INDEX IF NOT EXISTS ix_tarefas_setor_id ON tarefas (setor_id)"),
        ("ix_tarefas_responsavel_id", "CREATE INDEX IF NOT EXISTS ix_tarefas_responsavel_id ON tarefas (responsavel_id)"),
        ("ix_tarefas_supervisor_id",  "CREATE INDEX IF NOT EXISTS ix_tarefas_supervisor_id ON tarefas (supervisor_id)"),
        ("ix_tarefas_obrigacao_id",   "CREATE INDEX IF NOT EXISTS ix_tarefas_obrigacao_id ON tarefas (obrigacao_id)"),
        ("ix_tarefas_status",         "CREATE INDEX IF NOT EXISTS ix_tarefas_status ON tarefas (status)"),
        ("ix_tarefas_data_prazo",     "CREATE INDEX IF NOT EXISTS ix_tarefas_data_prazo ON tarefas (data_prazo)"),
        # atrasadas = status pendente/andamento COM prazo vencido, sempre juntos
        ("ix_tarefas_status_prazo",   "CREATE INDEX IF NOT EXISTS ix_tarefas_status_prazo ON tarefas (status, data_prazo)"),
        # e-validador procura por (empresa, obrigação, competência)
        ("ix_tarefas_competencia",    "CREATE INDEX IF NOT EXISTS ix_tarefas_competencia ON tarefas (competencia)"),
        # M2M: a PK é (tarefa_id, usuario_id), então buscar POR USUÁRIO -- que é
        # o que o escopo faz -- não aproveita a chave primária.
        ("ix_tarefa_resp_usuario",    "CREATE INDEX IF NOT EXISTS ix_tarefa_resp_usuario ON tarefa_responsaveis (usuario_id)"),
        # mesmo caso na matriz (empresa, setor): a PK começa por vinculo_id, e
        # quem pergunta "de que setores esta pessoa é responsável" busca pelo
        # outro lado. Sem isto, varre a tabela.
        ("ix_resp_setor_usuario",     "CREATE INDEX IF NOT EXISTS ix_resp_setor_usuario ON empresa_setor_resp_usuarios (usuario_id)"),
        # a geração pergunta "quais empresas esta obrigação NÃO alcança" a cada
        # obrigação do mês, e a busca é sempre por obrigacao_id
        ("ix_excecao_obrigacao",      "CREATE INDEX IF NOT EXISTS ix_excecao_obrigacao ON obrigacao_excecao (obrigacao_id)"),
        # subordinados diretos, lidos a cada request para montar o escopo
        ("ix_usuarios_gestor_id",     "CREATE INDEX IF NOT EXISTS ix_usuarios_gestor_id ON usuarios (gestor_id)"),
    ]
    for nome, sql in indices:
        with engine.begin() as conn:
            try:
                conn.execute(text(sql))
            except Exception as e:
                print(f"Erro no índice '{nome}': {e}")


def seed_admin():
    """Cria o admin inicial a partir de ADMIN_EMAIL/ADMIN_PASSWORD apenas
    quando a tabela de usuários está vazia. Sem essas envs, não faz nada."""
    email = os.getenv("ADMIN_EMAIL")
    senha = os.getenv("ADMIN_PASSWORD")
    if not email or not senha:
        return
    db = SessionLocal()
    try:
        if db.query(Usuario).count() == 0:
            db.add(Usuario(
                nome=os.getenv("ADMIN_NOME", "Administrador"),
                email=email,
                senha_hash=get_password_hash(senha),
                cargo="admin",
                grupo="admin",
            ))
            db.commit()
            print(f"Admin inicial criado: {email}")
    finally:
        db.close()


def ensure_admin_grupo():
    """Garante que o admin (por cargo ou pelo ADMIN_EMAIL) fique no grupo 'admin'.
    Necessário porque a coluna 'grupo' nasce com default 'usuario' para linhas antigas."""
    email = os.getenv("ADMIN_EMAIL")
    db = SessionLocal()
    try:
        cond = Usuario.cargo == "admin"
        if email:
            cond = cond | (Usuario.email == email)
        promovidos = 0
        for u in db.query(Usuario).filter(cond).all():
            if u.grupo != "admin":
                u.grupo = "admin"
                promovidos += 1
        if promovidos:
            db.commit()
            print(f"{promovidos} usuário(s) promovido(s) ao grupo admin.")
    finally:
        db.close()


def seed_grupos():
    """Semeia os papéis nativos na tabela `grupos` (uma vez) e carrega o cache
    de permissões. Idempotente: só cria os slugs que ainda não existem."""
    import json
    from .models import Grupo
    from . import permissoes
    db = SessionLocal()
    try:
        existentes = {g.slug for g in db.query(Grupo).all()}
        criados = 0
        for slug, perm in permissoes.PRESETS.items():
            if slug in existentes:
                continue
            label, desc = permissoes.LABELS_NATIVOS.get(slug, (slug.capitalize(), ""))
            db.add(Grupo(slug=slug, label=label, descricao=desc,
                         permissoes=json.dumps(perm), sistema=True, ativo=True))
            criados += 1
        if criados:
            db.commit()
            print(f"{criados} grupo(s) nativo(s) semeado(s).")
        permissoes.carregar_do_banco(db)
    finally:
        db.close()
