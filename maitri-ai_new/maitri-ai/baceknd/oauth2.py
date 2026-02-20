import jwt
from jwt.exceptions import InvalidTokenError
from datetime import datetime,timedelta
from . import database,models
from fastapi import Depends,status,HTTPException
from fastapi.security import OAuth2PasswordBearer
from .config import settings

oauth2_scheme=OAuth2PasswordBearer(tokenUrl="login")

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
def create_access_token(data: dict):
    to_encode=data.copy()

    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp":expire})

    encoded_jwt=jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)

    return encoded_jwt

def verify_access_token(token: str, credentials_exception):
    try:
        payload = jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        id : str = payload.get("sub")
        if id is None:
            raise credentials_exception
        token_data = models.TokenData(id=str(id))
    except InvalidTokenError:
        raise credentials_exception
    
    return token_data
    
async def get_current_user(session:database.session_object,token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Could not validate credentials", 
        headers={"WWW-Authenticate": "Bearer"}
    )
    token_data = verify_access_token(token,credentials_exception)
    user = await session.get(database.Astronaut,int(token_data.id))
    if user is None:
        raise credentials_exception
    return user