from fastapi import status,HTTPException,APIRouter
from ..database import session_object,Astronaut
from ..models import astronaut_register,AstronautResponse
from .. import utility
from sqlmodel import select
router=APIRouter(
    prefix="/user",
    tags=["Users"]
)

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=AstronautResponse)
async def create_user(new_user: astronaut_register, session: session_object):
    statement = select(Astronaut).where(Astronaut.email == new_user.email)
    result = await session.exec(statement)
    existing_user = result.first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    hashed_password = utility.hash_password(new_user.password)
    new_user.password = hashed_password
    
    the_user = Astronaut.model_validate(new_user)
    session.add(the_user)
    await session.commit() 
    await session.refresh(the_user)  
    
    return the_user

@router.get("/{id}", response_model=AstronautResponse)
async def get_user(id: int, session: session_object):
    
    the_user = await session.get(Astronaut, id)
    
    if not the_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {id} not found"
        )
    
    return the_user