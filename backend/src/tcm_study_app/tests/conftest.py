"""Shared test fixtures."""
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import tcm_study_app.main as main_module
import tcm_study_app.services.demo_seed as demo_seed_module
from tcm_study_app.db import get_db
from tcm_study_app.db.session import Base
from tcm_study_app.main import app
from tcm_study_app.services.llm_service import llm_service


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """Create an isolated test client backed by an in-memory database."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        class_=Session,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    original_init_db = main_module.init_db
    original_main_session_local = main_module.SessionLocal
    original_demo_seed_session_local = demo_seed_module.SessionLocal
    original_anthropic_api_key = llm_service.anthropic_api_key
    original_openai_api_key = llm_service.openai_api_key
    main_module.init_db = lambda: Base.metadata.create_all(bind=engine)
    main_module.SessionLocal = testing_session_local
    demo_seed_module.SessionLocal = testing_session_local
    llm_service.anthropic_api_key = None
    llm_service.openai_api_key = None

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    main_module.init_db = original_init_db
    main_module.SessionLocal = original_main_session_local
    demo_seed_module.SessionLocal = original_demo_seed_session_local
    llm_service.anthropic_api_key = original_anthropic_api_key
    llm_service.openai_api_key = original_openai_api_key
    Base.metadata.drop_all(bind=engine)
