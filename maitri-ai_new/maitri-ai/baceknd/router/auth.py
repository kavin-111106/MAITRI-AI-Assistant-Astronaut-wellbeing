from fastapi import APIRouter,Depends,HTTPException,status
from ..database import session_object,Astronaut
from fastapi.security import OAuth2PasswordRequestForm
from ..utility import verify
from sqlmodel import select
from ..oauth2 import create_access_token
from ..models import Token
router = APIRouter(tags=['Authentication'])

@router.post("/login", response_model=Token)
async def login(
    session: session_object,
    user_credentials: OAuth2PasswordRequestForm = Depends()
):
    
    result = await session.exec(
        select(Astronaut).where(Astronaut.email == user_credentials.username)
    )
    user = result.first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Invalid Credentials'
        )
    
    if not verify(user_credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Invalid Credentials'
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})  
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
