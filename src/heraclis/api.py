from fastapi import FastAPI, HTTPException, status

from heraclis.database import WorkoutDB

app = FastAPI()

db = WorkoutDB()


@app.get("/exercises")
def read_exercises():
    exercises = db.get_exercises()
    if not exercises:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No exercises found"
        )
    return exercises


@app.get("/exercises/{name}")
def read_exercise(name: str):
    exercise = db.get_exercise_by_name(name)
    if not exercise:
        available = [_["name"] for _ in db.get_exercises()]
        if not available:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No exercises found"
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No exercise with name '{name}'. Avalable exercises: {available}",
        )
    return exercise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("heraclis.api:app", host="127.0.0.1", port=8000, reload=True)
