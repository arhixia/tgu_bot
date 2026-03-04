# src/services/llm_service.py

import json
import uuid
import tempfile
from openai import AsyncOpenAI
from src.db.config import YANDEX_CLOUD_API_KEY, YANDEX_CLOUD_FOLDER
import logging


logger = logging.getLogger(__name__)

YANDEX_CLOUD_MODEL = "yandexgpt-5-pro/latest"

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


async def generate_task(llm_prompt: str) -> dict:
    system = (
        "Ты генератор задач по математическому анализу для студентов технических вузов. "
        "Отвечай строго в формате JSON без markdown, без пояснений, без текста вне JSON. "
        "JSON должен содержать ровно три поля: hint, correct_answer, matplotlib_code."
    )

    user_prompt = (
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

    raw = await _call_yandex(system, user_prompt, temperature=0.7)
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