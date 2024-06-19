from fastapi import APIRouter, Depends, status, UploadFile, File
from sqlalchemy.orm import Session
import cloudinary
import cloudinary.uploader

from src.database.db import get_db
from src.database.models import User
from src.repository import users as repository_users
from src.services.auth import auth_service
from src.conf.config import settings
from src.schemas import UserDb

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me/", response_model=UserDb)
async def read_users_me(current_user: User = Depends(auth_service.get_current_user)):
    """
    Endpoint to retrieve details of the current authenticated user.

    Args:
        current_user (User, optional): Current authenticated user. Defaults to Depends(auth_service.get_current_user).

    Returns:
        UserDb: User details.

    Raises:
        HTTPException: If user details cannot be retrieved.
    """
    return current_user

@router.patch("/avatar", response_model=UserDb)
async def update_avatar_user(
    file: UploadFile = File(),
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Endpoint to update the avatar of the current authenticated user.

    Args:
        file (UploadFile, optional): Uploaded file containing the new avatar image. Defaults to File().
        current_user (User, optional): Current authenticated user. Defaults to Depends(auth_service.get_current_user).
        db (Session, optional): Database session. Defaults to Depends(get_db).

    Returns:
        UserDb: Updated user details including the new avatar URL.

    Raises:
        HTTPException: If no file is provided, upload fails, or avatar update in the database fails.
    """
    try:
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")

        # Configure Cloudinary with credentials from settings
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )

        # Upload file to Cloudinary
        upload_result = cloudinary.uploader.upload(
            file.file,
            public_id=f'NotesApp/{current_user.username}',
            overwrite=True,
            width=250,
            height=250,
            crop='fill'
        )

        # Build URL for the uploaded avatar
        src_url = cloudinary.CloudinaryImage(f'NotesApp/{current_user.username}') \
            .build_url(version=upload_result.get('version'))

        # Update avatar URL in the database
        updated_user = await repository_users.update_avatar(current_user.email, src_url, db)
        return updated_user
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload avatar: {str(e)}")

