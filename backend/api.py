from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from backend.database import init_db, save_feedback, load_feedback

app = FastAPI(title="Tag Builder API")

@app.on_event("startup")
def startup(): # чтобы не стирало старые записи.
    init_db()

class FeedbackCreate(BaseModel):
    name_human: str | None = None # (поле ввода может быть пустым)
    name_project: str | None = None
    name_system: str | None = None
    message: str

@app.get("/health")
def health(): # Проверка, что backend запущен.
    return {"status": "ok"}

@app.post("/feedback")
def create_feedback(feedback: FeedbackCreate): # сохранить обратную связь  в SQLite.
    if feedback.message.strip() == "":
        raise HTTPException(status_code=400, detail="Сообщение не должно быть пустым") #для поля с сообщением
    feedback_id = save_feedback(
        name_human=feedback.name_human,
        name_project=feedback.name_project,
        name_system=feedback.name_system,
        message=feedback.message,)
    return {"status": "saved", "feedback_id": feedback_id}

@app.get("/feedback")
def get_feedback(): # прочитать сохранённые сообщения обратной связи.
    return load_feedback()
