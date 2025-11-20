from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# The path to the SQLite database created by Prisma
# Assuming the server runs from the root and the db is in web/prisma/dev.db
SQLALCHEMY_DATABASE_URL = "sqlite:///./web/prisma/dev.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
