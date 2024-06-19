from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base
from src.conf.config import settings

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency
def get_db():
    """
    Функція для отримання об'єкта сесії бази даних.

    Повертає:
    generator: Генератор, який повертає об'єкт сесії бази даних.

    Приклад використання:
    ```
    db = next(get_db())
    try:
        # Виконання операцій з базою даних
        ...
    finally:
        db.close()
    ```
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

