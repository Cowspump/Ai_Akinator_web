from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import openai
from utils import config


client = openai.OpenAI(api_key=config.OPEN_AI_TOKEN)


system_prompt = """
Ты — ИИ, который играет в игру "Акинатор".
Твоя задача — угадать персонажа, животное или предмет, о котором думает пользователь.
Ты задаешь простые, уточняющие вопросы, опираясь на ответы "да", "нет", "не знаю" или "возможно".
Постепенно сужай круг догадок и пробуй угадать.
"""

# История переписки
messages = [{"role": "system", "content": system_prompt}]
all_user_answers = []

app = FastAPI()


@app.websocket("/game")
async def game(websocket: WebSocket):
    await websocket.accept()


    messages.append({
        "role": "user",
        "content": (
            "Задай 20 простых вопросов для угадывания персонажа. "
            "Формат: номер и текст вопроса. Без лишних комментариев."
        )
    })

    questions = ask_gpt(messages)
    questions_list = [q.strip() for q in questions.strip().split('\n') if q.strip()]

    # Отправляем вопросы по одному
    for question in questions_list:
        await websocket.send_text(f"Вопрос: {question}")

        try:
            user_answer = await websocket.receive_text()
            all_user_answers.append(f"{question} - {user_answer.strip().lower()}")
        except WebSocketDisconnect:
            break


    messages.append({"role": "user", "content": "\n".join(all_user_answers)})

    # Запрос к GPT для угадывания персонажа
    messages.append({"role": "user", "content": (
        "На основе всех ответов попробуй угадать, кто это. "
        "Формат ответа: 'Я думаю, ваш персонаж - <твое предположение>'. Без лишних комментариев."
    )})
    gpt_guess = ask_gpt(messages)

    # Отправляем ответ от GPT
    await websocket.send_text(f"предположение: {gpt_guess}")

    await websocket.close()


def ask_gpt(messages, temperature=0.5):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=temperature
    )
    return response.choices[0].message.content