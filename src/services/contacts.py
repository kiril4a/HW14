from fastapi import APIRouter, HTTPException, Depends, Query, status, File, UploadFile
from sqlalchemy.orm import Session
from fastapi.security import HTTPBearer
from database.db import get_db
from src.repository import contacts as contact_repository
from src.repository.users import update_avatar
from src.schemas import ContactCreate, ContactUpdate, ContactInDB, User
from src.services.auth import pwd_context
from src.services.auth import verify_password as auth_verify_password
from src.database.models import User
from jose import JWTError, jwt
from datetime import datetime, timedelta
from src.conf.config import settings
from typing import List
from fastapi_limiter.depends import RateLimiter
import cloudinary
import cloudinary.uploader

router = APIRouter()

oauth2_scheme = HTTPBearer()
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.algorithm

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Retrieves the current user from the JWT token.

    Parameters:
    - token: str - JWT token passed in the Authorization header.

    Returns:
    User object corresponding to the email extracted from the JWT token.

    Raises:
    HTTPException: if credentials cannot be validated or user not found in database.
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

@router.post("/", response_model=ContactInDB, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
def create_contact(
    contact: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new contact for the current user.

    Parameters:
    - contact: ContactCreate - data to create a new contact.
    - db: Session = Depends(get_db) - database session dependency.
    - current_user: User = Depends(get_current_user) - current user from JWT token.

    Returns:
    Created contact.

    Raises:
    HTTPException: if failed to create contact.
    """
    return contact_repository.create_contact(db, contact)

@router.get("/", response_model=List[ContactInDB], dependencies=[Depends(RateLimiter(times=10, seconds=60))])
def read_contacts(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves a list of contacts for the current user.

    Parameters:
    - skip: int = 0 - number of records to skip.
    - limit: int = 10 - maximum number of records to return.
    - db: Session = Depends(get_db) - database session dependency.
    - current_user: User = Depends(get_current_user) - current user from JWT token.

    Returns:
    List of contacts.

    Raises:
    HTTPException: if failed to retrieve contacts.
    """
    return contact_repository.get_contacts(db, skip=skip, limit=limit)

@router.get("/{contact_id}", response_model=ContactInDB, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
def read_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves a specific contact by its ID for the current user.

    Parameters:
    - contact_id: int - contact ID.
    - db: Session = Depends(get_db) - database session dependency.
    - current_user: User = Depends(get_current_user) - current user from JWT token.

    Returns:
    Contact with the specified ID.

    Raises:
    HTTPException: if contact not found.
    """
    contact = contact_repository.get_contact(db, contact_id)
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact

@router.put("/{contact_id}", response_model=ContactInDB, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
def update_contact(
    contact_id: int,
    contact: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates an existing contact for the current user by its ID.

    Parameters:
    - contact_id: int - contact ID to update.
    - contact: ContactUpdate - data to update the contact.
    - db: Session = Depends(get_db) - database session dependency.
    - current_user: User = Depends(get_current_user) - current user from JWT token.

    Returns:
    Updated contact.

    Raises:
    HTTPException: if contact not found or failed to update.
    """
    updated_contact = contact_repository.update_contact(db, contact_id, contact)
    if updated_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return updated_contact

@router.delete("/{contact_id}", response_model=ContactInDB, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
def delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes a contact by its ID for the current user.

    Parameters:
    - contact_id: int - contact ID to delete.
    - db: Session = Depends(get_db) - database session dependency.
    - current_user: User = Depends(get_current_user) - current user from JWT token.

    Returns:
    Deleted contact.

    Raises:
    HTTPException: if contact not found or failed to delete.
    """
    deleted_contact = contact_repository.delete_contact(db, contact_id)
    if deleted_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return deleted_contact

@router.get("/search/", response_model=List[ContactInDB], dependencies=[Depends(RateLimiter(times=10, seconds=60))])
def search_contacts(
    query: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Searches contacts by query string for the current user.

    Parameters:
    - query: str - search query string among contacts.
    - db: Session = Depends(get_db) - database session dependency.
    - current_user: User = Depends(get_current_user) - current user from JWT token.

    Returns:
    List of contacts matching the search criteria.

    Raises:
    HTTPException: if no contacts found or query parameter not provided.
    """
    return contact_repository.search_contacts(db, query)

@router.get("/upcoming_birthdays/", response_model=List[ContactInDB], dependencies=[Depends(RateLimiter(times=10, seconds=60))])
def upcoming_birthdays(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves a list of contacts with upcoming birthdays for the current user.

    Parameters:
    - db: Session = Depends(get_db) - database session dependency.
    - current_user: User = Depends(get_current_user) - current user from JWT token.

    Returns:
    List of contacts with upcoming birthdays.

    Raises:
    HTTPException: if failed to retrieve contacts or query parameter not provided.
    """
    return contact_repository.get_upcoming_birthdays(db)

@router.patch('/avatar')
async def update_avatar_user(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates user's avatar based on the uploaded file on Cloudinary.

    Parameters:
    - file: UploadFile = File(...) - uploaded file (image) to update the avatar.
    - current_user: User = Depends(get_current_user) - current user from JWT token.
    - db: Session = Depends(get_db) - database session dependency.

    Returns:
    Updated user with new avatar URL.

    Raises:
    HTTPException: if file was not uploaded or error occurred during avatar update.
    """
    try:
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")

        cloudinary.config(
            cloud_name=settings.cloudinary_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
            secure=True
        )

        upload_result = cloudinary.uploader.upload(
            file.file,
            public_id=f'NotesApp/{current_user.username}',
            overwrite=True,
            width=250,
            height=250,
            crop='fill'
        )

        src_url = cloudinary.CloudinaryImage(f'NotesApp/{current_user.username}') \
            .build_url(version=upload_result.get('version'))

        # Update avatar in the database
        updated_user = await update_avatar(current_user.email, src_url, db)
        return updated_user
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload avatar: {str(e)}")
