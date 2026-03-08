import jwt
from datetime import datetime, timezone, timedelta
from . import database, models
from fastapi import Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer
from .config import settings

# --- GIVE THEM UNIQUE INTERNAL NAMES ---
astronaut_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scheme_name="AstronautAuth"  # <--- Unique ID
)

admin_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/admin/admin-login",
    scheme_name="AdminAuth"      # <--- Unique ID
)

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(session: database.session_object, token: str = Depends(astronaut_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id, role = payload.get("sub"), payload.get("role")
        if not user_id or role != "astronaut":
            raise HTTPException(status_code=403, detail="Astronaut role required")
        user = await session.get(database.Astronaut, int(user_id))
        if not user: raise HTTPException(status_code=401)
        return user
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_admin(session: database.session_object, token: str = Depends(admin_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        admin_id, role = payload.get("sub"), payload.get("role")
        if not admin_id or role != "admin":
            raise HTTPException(status_code=403, detail="Admin role required")
        admin = await session.get(database.Admin, int(admin_id))
        if not admin: raise HTTPException(status_code=401)
        return admin
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")