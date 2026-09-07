from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# 실행 위치와 관계없이 프로젝트 폴더에 DB 파일을 생성합니다.
DATABASE_PATH = Path(__file__).resolve().parent / "smart_cart.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """API 요청마다 DB 세션을 열고, 요청이 끝나면 닫습니다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
