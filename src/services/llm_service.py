# src/services/llm_service.py

import json
import uuid
import tempfile
import httpx
from openai import AsyncOpenAI
from src.db.config import YANDEX_CLOUD_API_KEY, YANDEX_CLOUD_FOLDER, YANDEX_IAM_TOKEN
import logging


logger = logging.getLogger(__name__)

YANDEX_CLOUD_MODEL = "yandexgpt-5-pro/latest"
YANDEX_VISION_CLOUD_MODEL = "yandexgpt-5-pro-vision/latest"

client = AsyncOpenAI(
    api_key=YANDEX_CLOUD_API_KEY,
    base_url="https://ai.api.cloud.yandex.net/v1",
)


async def _call_yandex(system: str, user_prompt: str, temperature: float = 0.7) -> str:
    response = await client.chat.completions.create(
        model=f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}",
        temperature=temperature,
        max_tokens=2000,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ]
    )
    return response.choices[0].message.content


def _parse_json(raw: str) -> dict:
    clean = raw.strip()
    if clean.startswith("```"):
        parts = clean.split("```")
        clean = parts[1] if len(parts) > 1 else clean
        if clean.startswith("json"):
            clean = clean[4:]
    return json.loads(clean.strip())


def _render_matplotlib(code: str, output_path: str):
    import matplotlib.pyplot as plt
    import matplotlib
    
    safe_path = output_path.replace("\\", "\\\\")
    code = code.replace("{output_path}", safe_path)
    
    try:
        exec(code, {"plt": plt, "matplotlib": matplotlib, "__builtins__": __builtins__})
    except Exception as e:
        logger.error(f"matplotlib exec error: {e}\nCode:\n{code}")
        _render_fallback(output_path)


def _render_fallback(output_path: str):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 2.5))
    ax.text(0.5, 0.5, "Не удалось отрисовать задание",
            fontsize=14, ha='center', va='center', transform=ax.transAxes)
    ax.axis('off')
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()

async def _call_yandex_with_history(system: str, messages: list[dict], temperature: float = 0.9) -> str:
    response = await client.chat.completions.create(
        model=f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}",
        temperature=temperature,
        max_tokens=2000,
        messages=[{"role": "system", "content": system}] + messages
    )
    return response.choices[0].message.content

async def generate_task(llm_prompt: str, previous_tasks: list[str] | None = None) -> dict:
    system = (
        "Ты генератор задач по математическому анализу для студентов технических вузов. "
        "Отвечай строго в формате JSON без markdown, без пояснений, без текста вне JSON. "
        "JSON должен содержать ровно три поля: hint, correct_answer, matplotlib_code. "
        "СТРОГО генерируй уникальные задания — никогда не повторяй интегралы из истории."
    )

    base_prompt = (
        f"{llm_prompt}\n\n"
        "Ответь строго в формате JSON:\n"
        "{\n"
        '  "hint": "подсказка направляющая к методу решения, не раскрывая ответ",\n'
        '  "correct_answer": "правильный ответ, например: sin(x²) + C",\n'
        '  "matplotlib_code": "python код который рисует задачу через matplotlib.pyplot '
        "и сохраняет через plt.savefig('{output_path}'). "
        "Белый фон, figsize=(6, 2.5), dpi=150. "
        'Используй mathtext для LaTeX формул. Импортируй только matplotlib.pyplot as plt"\n'
        "}"
    )

    messages = []
    if previous_tasks:
        for i, prev_answer in enumerate(previous_tasks):
            messages.append({"role": "user", "content": base_prompt})
            messages.append({
                "role": "assistant",
                "content": f'{{"hint": "...", "correct_answer": "{prev_answer}", "matplotlib_code": "..."}}'
            })

    if previous_tasks:
        messages.append({
            "role": "user",
            "content": (
                f"{base_prompt}\n\n"
                f"УЖЕ СГЕНЕРИРОВАННЫЕ ОТВЕТЫ (не повторять): {', '.join(previous_tasks)}"
            )
        })
    else:
        messages.append({"role": "user", "content": base_prompt})

    raw = await _call_yandex_with_history(system, messages, temperature=0.9)
    parsed = _parse_json(raw)

    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()
    image_path = tmp.name.replace("\\", "/")
    _render_matplotlib(parsed["matplotlib_code"], image_path)

    return {
        "hint": parsed.get("hint", ""),
        "correct_answer": parsed.get("correct_answer", ""),
        "image_path": image_path,
    }




#======================  Студент ===============


async def _ocr_recognize(image_bytes: bytes) -> str:
    """распознаём текст с фото через Yandex OCR"""
    import base64
    content_b64 = base64.b64encode(image_bytes).decode()

    async with httpx.AsyncClient() as http:
        resp = await http.post(
            url="https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {YANDEX_IAM_TOKEN}",
                "x-folder-id": YANDEX_CLOUD_FOLDER,
                "x-data-logging-enabled": "true",
            },
            json={
                "mimeType": "JPEG",
                "languageCodes": ["ru", "en"],
                "model": "page",
                "content": content_b64,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

    full_text = (
        data.get("result", {})
            .get("textAnnotation", {})
            .get("fullText", "")
            .strip()
    )
    return full_text


async def check_answer(
    correct_answer: str,
    student_image_bytes: bytes,
) -> dict:
    try:
        recognized_text = await _ocr_recognize(student_image_bytes)
    except Exception as e:
        logger.error(f"OCR error: {e}")
        return {"correct": False, "comment": "Ошибка распознавания", "unreadable": True}

    if not recognized_text:
        logger.warning("OCR returned empty text")
        return {"correct": False, "comment": "Не удалось распознать текст", "unreadable": True}

    logger.info(f"=== CHECK ANSWER ===")
    logger.info(f"Правильный ответ: {correct_answer}")
    logger.info(f"OCR распознал:    {recognized_text}")

    system = (
        "Ты проверяешь письменные ответы студентов по математическому анализу. "
        "Отвечай строго в формате JSON без markdown и текста вне JSON."
    )

    user_prompt = (
        f"Правильный ответ задачи: {correct_answer}\n\n"
        f"Ответ студента (распознан OCR с рукописи): {recognized_text}\n\n"
        "ВАЖНО: OCR часто искажает рукописные математические формулы. Применяй следующие правила:\n"
        "1. Игнорируй пробелы, они появляются при распознавании произвольно\n"
        "2. 'in' = 'sin', 'cos' может читаться как 'con' или 'eos'\n"
        "3. Степени могут потеряться: 'sin(x)' вместо 'sin³(x)' — смотри на общую структуру\n"
        "4. Дроби OCR разбивает на строки: числитель и знаменатель могут быть разделены пробелом или переносом\n"
        "5. '1/3 sin³(x)' и 'sin³(x)/3' и 'sin(x)^3/3' — одно и то же\n"
        "6. Константа C может отсутствовать или быть написана как 'c', 'С' (кириллица)\n"
        "7. Умножение может быть опущено: '2sin(x)' = '2·sin(x)'\n\n"
        "Оценивай МАТЕМАТИЧЕСКУЮ СУТЬ, а не точное написание.\n"
        "Если распознанный текст хоть как-то напоминает правильный ответ с поправкой на ошибки OCR — считай правильным.\n"
        "Считай НЕПРАВИЛЬНЫМ только если математически очевидно другой ответ.\n\n"
        "Ответь строго в формате JSON:\n"
        "{\n"
        '  "correct": true или false,\n'
        '  "comment": "краткое пояснение на русском — что не так или поздравление"\n'
        "}"
    )

    raw = await _call_yandex(system, user_prompt, temperature=0)
    logger.info(f"YandexGPT ответил: {raw}")

    try:
        result = _parse_json(raw)
        result["unreadable"] = False
        logger.info(f"Итог проверки: correct={result.get('correct')}, comment={result.get('comment')}")
        logger.info(f"===================")
        return result
    except Exception:
        logger.error(f"check_answer parse error: {raw}")
        return {"correct": False, "comment": "Ошибка проверки", "unreadable": False}


