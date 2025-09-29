from typing import Annotated

from fastapi import Depends, FastAPI, Form, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from heraclis.models import Exercise, User, get_engine
from heraclis.schemas import UserData

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def session():
    sess = SessionLocal()
    try:
        yield sess
    finally:
        sess.close()


app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
sess = Annotated[Session, Depends(session)]


def get_user_by_name(name: str, session: Session):
    user = session.scalar(select(User).where(User.username == name))
    return user


@app.get("/users/get/{name}", response_model=UserData)
def get_user(username: str, session: sess) -> User:
    user = get_user_by_name(username, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' does not exist",
        )
    return user


@app.post("/users/create", response_model=UserData)
def create_user(
    username: Annotated[str, Form()], password: Annotated[str, Form()], session: sess
) -> User:
    hashed_password = pwd_context.hash(password)
    user = get_user_by_name(username, session)
    if user:
        raise HTTPException(status_code=409, detail=f"User '{username}' already exists")
    user = User(username=username, hashed_password=hashed_password)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@app.get("/exercises")
def read_exercises(session: sess):
    exercises = session.scalars(select(Exercise)).all()
    if not exercises:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No exercises found"
        )
    return exercises


@app.get("/exercises/{name}")
def read_exercise(name: str, session: sess):
    exercise = session.scalar(select(Exercise).filter_by(name=name))
    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No exercise found named {name}",
        )
    return exercise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("heraclis.api:app", host="127.0.0.1", port=8000, reload=True)
