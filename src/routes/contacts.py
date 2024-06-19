from fastapi import APIRouter, HTTPException, Depends, Query, status, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from fastapi.security import HTTPBearer
from src.database.db import get_db
from src.repository import contacts as contact_repository
from src.schemas import ContactCreate, ContactUpdate, ContactInDB
from src.database.models import User,Contact
from src.repository import contacts
from jose import JWTError, jwt
from src.conf.config import settings
from typing import List
from fastapi_limiter.depends import RateLimiter
import cloudinary
import cloudinary.uploader
import logging
from sqlalchemy.future import select
oauth2_scheme = HTTPBearer()
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.algorithm

router = APIRouter(prefix="/contacts", tags=["contacts"])
logger = logging.getLogger(__name__)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Dependency function to authenticate and retrieve the current user based on JWT token.

    Args:
        token (str, optional): JWT token extracted from HTTP bearer scheme. Defaults to Depends(oauth2_scheme).
        db (Session, optional): Database session. Defaults to Depends(get_db).

    Returns:
        User: Current user object fetched from the database.
    
    Raises:
        HTTPException: If credentials validation fails or user is not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    db_user = db.query(User).filter(User.email == email).first()
    if db_user is None:
        raise credentials_exception

    return db_user

@router.post("/contacts/", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def create_contact(
    contact: ContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ContactInDB:
    """
    Endpoint to create a new contact.

    Args:
        contact (ContactCreate): Contact creation data.
        db (AsyncSession, optional): Async database session. Defaults to Depends(get_db).
        current_user (User, optional): Current authenticated user. Defaults to Depends(get_current_user).

    Returns:
        ContactInDB: Newly created contact.

    Raises:
        HTTPException: If creation fails.
    """
    new_contact = await contact_repository.create_contact(db, contact)
    return new_contact

@router.get("/", response_model=List[ContactInDB], dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def get_contacts(
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[ContactInDB]:
    """
    Endpoint to retrieve a list of contacts.

    Args:
        skip (int, optional): Number of contacts to skip. Defaults to 0.
        limit (int, optional): Maximum number of contacts to retrieve. Defaults to 10.
        db (AsyncSession, optional): Async database session. Defaults to Depends(get_db).
        current_user (User, optional): Current authenticated user. Defaults to Depends(get_current_user).

    Returns:
        List[ContactInDB]: List of contacts.

    Raises:
        HTTPException: If retrieval fails.
    """
    contacts_list = await contact_repository.get_contacts(db, skip, limit)
    return contacts_list

@router.get("/contacts/{contact_id}", response_model=ContactInDB, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def read_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ContactInDB:
    """
    Endpoint to retrieve a single contact by ID.

    Args:
        contact_id (int): ID of the contact to retrieve.
        db (AsyncSession, optional): Async database session. Defaults to Depends(get_db).
        current_user (User, optional): Current authenticated user. Defaults to Depends(get_current_user).

    Returns:
        ContactInDB: Contact details.

    Raises:
        HTTPException: If contact with specified ID is not found.
    """
    db_contact = await contact_repository.get_contact(db, contact_id)
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return db_contact

@router.put("/{contact_id}", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def update_contact(
    contact_id: int,
    contact_update: ContactUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactInDB:
    """
    Endpoint to update a contact by ID.

    Args:
        contact_id (int): ID of the contact to update.
        contact_update (ContactUpdate): Contact update data.
        db (AsyncSession, optional): Async database session. Defaults to Depends(get_db).
        current_user (User, optional): Current authenticated user. Defaults to Depends(get_current_user).

    Returns:
        ContactInDB: Updated contact details.

    Raises:
        HTTPException: If update fails or contact with specified ID is not found.
    """
    updated_contact = await contact_repository.update_contact(db, contact_id, contact_update)
    if updated_contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return updated_contact

@router.delete("/delete/{contact_id}", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def delete_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Endpoint to delete a contact by ID.

    Args:
        contact_id (int): ID of the contact to delete.
        db (AsyncSession, optional): Async database session. Defaults to Depends(get_db).
        current_user (User, optional): Current authenticated user. Defaults to Depends(get_current_user).

    Returns:
        dict: Confirmation message.

    Raises:
        HTTPException: If deletion fails or contact with specified ID is not found.
    """
    db_contact = db.execute(select(Contact).filter(Contact.id == contact_id))
    contact_to_delete = db_contact.scalar()

    if contact_to_delete is None:
        raise HTTPException(status_code=404, detail="Contact not found")

    db.delete(contact_to_delete)
    db.commit()
    return {"message": f"Contact with id {contact_id} has been deleted"}

@router.get("/search/", response_model=List[ContactInDB], dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def search_contacts(
    query: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[ContactInDB]:
    """
    Endpoint to search contacts by name or email.

    Args:
        query (str): Search query string.
        db (AsyncSession, optional): Async database session. Defaults to Depends(get_db).
        current_user (User, optional): Current authenticated user. Defaults to Depends(get_current_user).

    Returns:
        List[ContactInDB]: List of contacts matching the search query.

    Raises:
        HTTPException: If search fails.
    """
    db_contact = await contact_repository.search_contacts(db, query)
    return db_contact

@router.get("/upcoming_birthdays/", response_model=List[ContactInDB], dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def upcoming_birthdays(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[ContactInDB]:
    """
    Endpoint to retrieve upcoming birthdays within the next week.

    Args:
        db (AsyncSession, optional): Async database session. Defaults to Depends(get_db).
        current_user (User, optional): Current authenticated user. Defaults to Depends(get_current_user).

    Returns:
        List[ContactInDB]: List of contacts with upcoming birthdays.

    Raises:
        HTTPException: If retrieval fails.
    """
    return await contact_repository.get_upcoming_birthdays(db)

import logging

logger = logging.getLogger(__name__)