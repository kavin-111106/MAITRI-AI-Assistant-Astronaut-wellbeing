from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select
from backend import utility
from .. import database, oauth2
from ..models import AdminRegister, AdminResponse, Token
from ..rate_limiter import limiter
import logging

logger = logging.getLogger("maitri.admin")
router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


@router.post("/create-admin", status_code=status.HTTP_201_CREATED, response_model=AdminResponse)
async def create_admin(admin_data: AdminRegister, session: database.session_object):
    statement = select(database.Admin).where(database.Admin.email == admin_data.email)
    result = await session.exec(statement)
    existing_admin = result.first()

    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    try:
        hashed_password = utility.hash_password(admin_data.password)
        admin_data.password = hashed_password

        new_admin = database.Admin.model_validate(admin_data)
        session.add(new_admin)
        await session.commit()
        await session.refresh(new_admin)
    except Exception as e:
        logger.error(f"Error creating admin: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the admin account",
        )

    logger.info(f"New admin created: id={new_admin.id}, email={new_admin.email}")
    return new_admin


@router.post("/admin-login", response_model=Token)
async def admin_login(
    session: database.session_object,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    statement = select(database.Admin).where(database.Admin.email == form_data.username)
    result = await session.exec(statement)
    admin = result.first()

    if not admin:
        logger.warning(f"Failed login attempt for email: {form_data.username}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")

    if not utility.verify(form_data.password, admin.password):
        logger.warning(f"Invalid password for email: {form_data.username}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")

    access_token = oauth2.create_access_token(data={"sub": str(admin.id),"role":"admin"})
    logger.info(f"Admin login successful: id={admin.id}, email={admin.email}")
    return {"access_token": access_token, "token_type": "bearer"}