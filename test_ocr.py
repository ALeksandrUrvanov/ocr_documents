
import sys
import time
from pathlib import Path

import requests

BASE_URL = "http://localhost:8086"

FILE_PATH = "test_3.pdf"


def main():
    file_path = Path(FILE_PATH)

    if not file_path.is_file():
        print(f"Ошибка: файл не найден: {file_path}")
        sys.exit(1)

    # 1. Отправляем файл в OCR
    print(f"Загрузка {file_path.name}...")
    with open(file_path, "rb") as f:
        r = requests.post(
            f"{BASE_URL}/api/documents/upload",
            files={"file": (file_path.name, f)},
            timeout=60,
        )

    if r.status_code != 202:
        print(f"Ошибка {r.status_code}: {r.text}")
        sys.exit(1)

    task_id = r.json()["task_id"]
    print(f"  Задача: {task_id}")

    # 2. Ждём окончания (опрос раз в 2 сек)
    print("Ожидание обработки...")
    max_wait = 3000
    elapsed = 0

    while elapsed < max_wait:
        r = requests.get(f"{BASE_URL}/api/documents/{task_id}/status", timeout=10)
        if r.status_code == 404:
            print("Ошибка: задача не найдена")
            sys.exit(1)

        data = r.json()
        status = data["status"]

        if status == "completed":
            print(f"  Готово: {data['processed_pages']}/{data['total_pages']} стр.")
            break
        if status == "failed":
            print("  Ошибка обработки")
            sys.exit(1)

        print(f"  Обработка... {data.get('processed_pages', 0)}/{data.get('total_pages', 0)}", end="\r")
        time.sleep(2)
        elapsed += 2

    if elapsed >= max_wait:
        print("Ошибка: превышено время ожидания")
        sys.exit(1)

    # 3. Забираем текст и сохраняем в .txt
    r = requests.get(f"{BASE_URL}/api/documents/{task_id}/result", timeout=60)
    if r.status_code != 200:
        print(f"Ошибка {r.status_code}: {r.text}")
        sys.exit(1)

    full_text = r.json().get("full_text", "")
    out_file = file_path.with_suffix(".txt")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(full_text)

    print(f"\nРезультат сохранён: {out_file}")


if __name__ == "__main__":
    main()