import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.security import verify_password
from app.models.psychologist import Psychologist
from app.seed_admin import garantir_admin


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'seed_admin.db'}")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def test_cria_conta_quando_nao_existe(db):
    assert garantir_admin(db, "mayra@exemplo.com", "senha123456", "Mayra") == "criada"

    conta = db.query(Psychologist).filter_by(email="mayra@exemplo.com").one()
    assert conta.name == "Mayra"
    assert verify_password("senha123456", conta.password_hash)


def test_nome_padrao_quando_nao_informado(db):
    garantir_admin(db, "mayra@exemplo.com", "senha123456")

    assert db.query(Psychologist).one().name == "Administrador"


def test_idempotente_com_mesma_senha(db):
    garantir_admin(db, "mayra@exemplo.com", "senha123456")

    assert garantir_admin(db, "mayra@exemplo.com", "senha123456") == "sem alterações"
    assert db.query(Psychologist).count() == 1


def test_troca_de_senha_na_variavel_redefine_a_senha(db):
    garantir_admin(db, "mayra@exemplo.com", "senha123456", "Mayra")

    assert garantir_admin(db, "mayra@exemplo.com", "outrasenha99", "Outro Nome") == "senha atualizada"

    conta = db.query(Psychologist).one()
    assert verify_password("outrasenha99", conta.password_hash)
    # O nome não é sobrescrito: pode ter sido editado pela própria psicóloga.
    assert conta.name == "Mayra"


def test_senha_curta_e_recusada(db):
    with pytest.raises(ValueError):
        garantir_admin(db, "mayra@exemplo.com", "curta")
    assert db.query(Psychologist).count() == 0


def test_conta_criada_consegue_logar(client):
    db = next(client.app.dependency_overrides[get_db]())
    garantir_admin(db, "mayra@exemplo.com", "senha123456")

    resposta = client.post("/api/auth/login", json={"email": "mayra@exemplo.com", "password": "senha123456"})
    assert resposta.status_code == 200
    assert "access_token" in resposta.json()
