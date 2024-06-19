# src/repository/user.py
from src.database.models import User
from sqlalchemy.orm import Session
from libgravatar import Gravatar


async def get_user_by_email(email: str, db: Session) -> User:
    """
    Асинхронно отримує користувача з бази даних за електронною поштою.

    Параметри:
    - email: str - електронна пошта користувача.
    - db: AsyncSession - об'єкт асинхронної сесії бази даних.

    Повертає:
    Об'єкт користувача з бази даних, якщо користувач знайдений.

    Викидає:
    HTTPException: статус 404, якщо користувач не знайдений.
    """
    return db.query(User).filter(User.email == email).first()

async def get_user_by_username(username: str, db: Session) -> User:
    """
    Асинхронно отримує користувача з бази даних за електронною поштою.

    Параметри:
    - username: str - електронна пошта користувача.
    - db: AsyncSession - об'єкт асинхронної сесії бази даних.

    Повертає:
    Об'єкт користувача з бази даних, якщо користувач знайдений.

    Викидає:
    HTTPException: статус 404, якщо користувач не знайдений.
    """
    return db.query(User).filter(User.username == username).first()

async def create_user(body, db: Session) -> User:
    """
    Асинхронно створює нового користувача в базі даних.

    Параметри:
    - body: UserCreate - дані нового користувача.
    - db: AsyncSession - об'єкт асинхронної сесії бази даних.

    Повертає:
    Об'єкт нового користувача з бази даних.

    Викидає:
    Немає.
    """
    avatar = None
    try:
        g = Gravatar(body.email)
        avatar = g.get_image()
    except Exception as e:
        print(e)
    new_user = User(**body.dict(), avatar=avatar)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


async def update_token(user: User, token: str | None, db: Session) -> None:
    """
    Updates the refresh token of a user in the database.

    Args:
        user (User): The user object whose token is to be updated.
        token (str | None): The new refresh token, or None to remove the token.
        db (Session): Database session.

    Returns:
        None: This function does not return any value.
    """
    user.refresh_token = token
    db.commit()



async def confirmed_email(email: str, db: Session) -> None:
    """
    Підтверджує статус електронної пошти користувача в базі даних.

    Параметри:
    - email: str - електронна пошта користувача.
    - db: AsyncSession - об'єкт асинхронної сесії бази даних.

    Повертає:
    None

    Викидає:
    HTTPException: статус 404, якщо користувач не знайдений в базі даних.
    """
    user = await get_user_by_email(email, db)
    user.confirmed = True
    db.commit()


async def update_avatar(email, url: str, db: Session) -> User:
    """
    Асинхронно оновлює URL аватара користувача в базі даних.

    Параметри:
    - email: str - електронна пошта користувача.
    - url: str - новий URL аватара.
    - db: AsyncSession - об'єкт асинхронної сесії бази даних.

    Повертає:
    Об'єкт користувача з оновленим URL аватара.

    Викидає:
    Немає.
    """
    user = await get_user_by_email(email, db)
    user.avatar = url
    db.commit()
    return user