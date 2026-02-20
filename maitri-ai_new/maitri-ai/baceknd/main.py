from fastapi import FastAPI
#from .database import create_db_and_tables
from .router import auth,users,chat

app=FastAPI()

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(chat.router)

@app.on_event("startup")
async def on_startup():
      #create_db_and_tables()
      pass


@app.get("/")
def root():
    return {"message": "Hello World!"}