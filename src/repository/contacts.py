#from sqlalchemy.orm import Session
from src.database.models import Contact
from src.schemas import ContactCreate, ContactUpdate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import or_
from typing import List, Optional
from src.database.models import Contact
from fastapi import HTTPException, status
async def create_contact(db: AsyncSession, contact: ContactCreate):
    """
    Creates a new contact in the database.

    Args:
        db (AsyncSession): Database session.
        contact (ContactCreate): Data of the new contact.

    Returns:
        Contact: The created contact object.
    """
    db_contact = Contact(**contact.dict())
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

async def get_contacts(db: AsyncSession, skip: int = 0, limit: int = 10):
    """
    Retrieves a list of contacts from the database with optional pagination.

    Args:
        db (AsyncSession): Database session.
        skip (int, optional): Number of records to skip. Defaults to 0.
        limit (int, optional): Maximum number of records to return. Defaults to 10.

    Returns:
        List[Contact]: A list of contact objects.
    """
    query = select(Contact).offset(skip).limit(limit)
    result = db.execute(query)
    contacts = result.scalars().all()
    return contacts

async def get_contact(db: AsyncSession, contact_id: int):
    """
    Retrieves a single contact by its ID from the database.

    Args:
        db (AsyncSession): Database session.
        contact_id (int): ID of the contact to retrieve.

    Returns:
        Optional[Contact]: The contact object if found, otherwise None.
    """
    query = select(Contact).filter(Contact.id == contact_id)
    result = db.execute(query)
    return result.scalar_one_or_none()

async def update_contact(db: AsyncSession, contact_id: int, contact_update: ContactUpdate):
    """
    Updates an existing contact in the database.

    Args:
        db (AsyncSession): Database session.
        contact_id (int): ID of the contact to update.
        contact_update (ContactUpdate): Updated data for the contact.

    Returns:
        Optional[Contact]: The updated contact object if found, otherwise None.
    """
    db.execute(Contact.__table__.update().where(Contact.id == contact_id).values(**contact_update.dict()))
    db.commit()
    query = select(Contact).filter(Contact.id == contact_id)
    result = db.execute(query)
    return result.scalar_one_or_none()

async def delete_contact(db: AsyncSession, contact_id: int):
    """
    Deletes a contact from the database by its ID.

    Args:
        db (AsyncSession): Database session.
        contact_id (int): ID of the contact to delete.

    Raises:
        HTTPException: If the contact is not found.

    Returns:
        dict: A message indicating the contact has been deleted.
    """
    db_contact = select(Contact).filter(Contact.id == contact_id)
    if db_contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    await db.delete(db_contact)
    await db.commit()
    return {"message": f"Contact with id {contact_id} has been deleted"}

async def search_contacts(db: AsyncSession, query: str):
    """
    Searches for contacts in the database based on a query string.

    Args:
        db (AsyncSession): Database session.
        query (str): The search query string.

    Returns:
        List[Contact]: A list of contacts matching the search criteria.
    """
    search_query = select(Contact).filter(
        or_(
            Contact.first_name.contains(query),
            Contact.last_name.contains(query),
            Contact.email.contains(query)
        )
    )
    result = db.execute(search_query)
    return result.scalars().all()

async def get_upcoming_birthdays(db: AsyncSession) -> List[Contact]:
    """
    Retrieves contacts with upcoming birthdays within the next week.

    Args:
        db (AsyncSession): Database session.

    Returns:
        List[Contact]: A list of contacts with upcoming birthdays.
    """
    from datetime import date, timedelta
    
    today = date.today()
    next_week = today + timedelta(days=7)
    contacts_query = select(Contact)
    result = db.execute(contacts_query)
    contacts = result.scalars().all()
    
    upcoming_birthdays = []

    for contact in contacts:
        if contact.birthday:
            birthday_this_year = contact.birthday.replace(year=today.year)
            if birthday_this_year < today:
                birthday_this_year = contact.birthday.replace(year=today.year + 1)
            if today <= birthday_this_year <= next_week:
                upcoming_birthdays.append(contact)

    return upcoming_birthdays

