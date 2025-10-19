import time

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Tuple
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
from PIL import Image
from io import BytesIO
from fastapi.responses import StreamingResponse
import threading

app = FastAPI()

# =============================
# GLOBALNE ZMIENNE DO POSTĘPU
# =============================
progress_lock = threading.Lock()
current_progress = 0
total_rows = 1  # żeby uniknąć dzielenia przez zero
is_busy = False


class Task(BaseModel):
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    width: int
    height: int
    max_iter: int


def mandelbrot(x: float, y: float, max_iter: int) -> int:
    c = complex(x, y)
    z = 0
    for i in range(max_iter):
        z = z * z + c
        if abs(z) > 2:
            return i
    return max_iter


def compute_row(args) -> List[Tuple[int, int, int]]:
    py, y, xs, max_iter = args
    row_result = []
    for px, x in enumerate(xs):
        i = mandelbrot(x, y, max_iter)
        color = int(255 * i / max_iter)
        row_result.append((px, py, color))
    return row_result


@app.get("/test")
def test():
    return {"message": "Test działa poprawnie"}


@app.get("/percentcomplete")
def timeleft():
    """Zwraca procent ukończenia aktualnego zadania."""
    with progress_lock:
        percent = (current_progress / total_rows) * 100
        status = "busy" if is_busy else "idle"
    return {"status": status, "progress": round(percent, 2)}


@app.post("/compute")
def compute(task: Task):
    global current_progress, total_rows, is_busy
    print("Otrzymano zadanie\n")

    start_time = time.time()
    with progress_lock:
        current_progress = 0
        total_rows = task.height
        is_busy = True

    xs = np.linspace(task.x_min, task.x_max, task.width)
    ys = np.linspace(task.y_min, task.y_max, task.height)
    args_list = [(py, y, xs, task.max_iter) for py, y in enumerate(ys)]

    results = []
    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(compute_row, args) for args in args_list]
        for f in as_completed(futures):
            results.append(f.result())
            with progress_lock:
                current_progress += 1  # zwiększamy licznik o 1 wiersz

    # spłaszczamy wynik
    flat_result = [pixel for row in results for pixel in row]

    # Tworzymy obraz w pamięci
    image_array = np.zeros((task.height, task.width), dtype=np.uint8)
    for x, y, color in flat_result:
        image_array[y, x] = color

    img = Image.fromarray(image_array, mode='L')

    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    with progress_lock:
        is_busy = False
        current_progress = total_rows  # 100%

    end_time = time.time()

    print(f"Completed in {end_time - start_time:.2f}s")

    return StreamingResponse(buf, media_type="image/png")
