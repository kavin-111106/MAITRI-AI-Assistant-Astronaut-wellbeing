from fastapi import APIRouter,Depends,HTTPException,status,Request
from ..database import session_object,Astronaut
from fastapi.security import OAuth2PasswordRequestForm
from ..utility import verify
from sqlmodel import select
from ..oauth2 import create_access_token
from ..models import Token
from ..rate_limiter import limiter
import logging

logger = logging.getLogger("maitri.auth")
router = APIRouter(prefix="/api/v1/auth", tags=['Authentication'])

@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(
    request: Request,
    session: session_object,
    user_credentials: OAuth2PasswordRequestForm = Depends()
):
    try:
        result = await session.exec(
            select(Astronaut).where(Astronaut.email == user_credentials.username)
        )
        user = result.first()
    except Exception as e:
        logger.error(f"Database error during login: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )
    
    if not user:
        logger.warning(f"Failed login attempt for email: {user_credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Invalid Credentials'
        )
    
    if not verify(user_credentials.password, user.password):
        logger.warning(f"Invalid password for email: {user_credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Invalid Credentials'
        )
    
    access_token = create_access_token(data={"sub": str(user.id),"role":"astronaut"})  
    logger.info(f"Successful login for astronaut id: {user.id}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
