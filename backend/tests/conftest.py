import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.rate_limit import _tentativas_falhas
from app.main import app


@pytest.fixture(autouse=True)
def limpar_rate_limit_de_login():
    # O contador de tentativas de login é um dict em memória no nível do
    # processo (ver app/core/rate_limit.py) — sem isso, testes que
    # provocam várias falhas de login vazariam bloqueio para outros
    # testes que reusam o mesmo e-mail.
    _tentativas_falhas.clear()
    yield
    _tentativas_falhas.clear()


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / f"test_{uuid.uuid4().hex}.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        test_client = TestClient(app)
        # Exposto para testes que precisam inspecionar o banco diretamente
        # (ex.: confirmar que um segredo foi salvo criptografado, não em
        # texto puro) sem depender de uma rota de API para isso.
        test_client.db_session_factory = TestingSessionLocal
        yield test_client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
