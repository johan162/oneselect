import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.base import Base
from app.api.deps import get_db
from app.core.config import settings
from tests.utils.utils import get_superuser_token_headers, get_user_token_headers

from sqlalchemy.pool import StaticPool

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def db() -> Generator:
    print(f"Creating tables: {Base.metadata.tables.keys()}")
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    # Create superuser
    from app import crud, schemas

    user = crud.user.get_by_email(session, email=settings.FIRST_SUPERUSER)
    if not user:
        user_in = schemas.UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            username=settings.FIRST_SUPERUSER,
            is_superuser=True,
        )
        crud.user.create(session, obj_in=user_in)

    yield session
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session")
def client(db: Generator) -> Generator:
    def override_get_db() -> Generator:
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def superuser_token_headers(client: TestClient) -> dict:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="session")
def normal_user_token_headers(client: TestClient) -> dict:
    """Create a normal user and return auth headers."""
    from app.core.config import settings

    # Register a normal user
    user_data = {
        "username": "normaluser",
        "email": "normal@example.com",
        "password": "normalpassword123",
    }
    client.post(f"{settings.API_V1_STR}/auth/register", json=user_data)

    # Get token headers
    return get_user_token_headers(client, "normaluser", "normalpassword123")
