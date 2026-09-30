import pytest

from app.core.config import Settings


@pytest.mark.parametrize(
    "entrada",
    ["postgres://u:s@host:5432/db", "postgresql://u:s@host:5432/db", "postgresql+psycopg://u:s@host:5432/db"],
)
def test_url_do_postgres_da_railway_usa_psycopg(entrada):
    assert Settings(database_url=entrada).database_url == "postgresql+psycopg://u:s@host:5432/db"


def test_sqlite_continua_igual():
    assert Settings(database_url="sqlite:///./dev.db").database_url == "sqlite:///./dev.db"
