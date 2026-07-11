from app.core.db import get_db_session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_health_reports_ok_with_connected_db(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "connected"}


def test_health_reports_degraded_when_db_unreachable(client):
    def broken_session():
        # A session bound to a port where nothing is listening.
        engine = create_engine("postgresql+psycopg://nobody:nothing@127.0.0.1:1/none")
        session = sessionmaker(bind=engine)()
        try:
            yield session
        finally:
            session.close()
            engine.dispose()

    client.app.dependency_overrides[get_db_session] = broken_session
    try:
        response = client.get("/health")
    finally:
        client.app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "db": "unavailable"}
