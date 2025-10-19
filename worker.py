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
from numba import cuda, jit
import numpy as np

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

@cuda.jit
def mandelbrot_kernel(x_min, x_max, y_min, y_max, width, height, max_iter, output):
    px, py = cuda.grid(2)
    if px >= width or py >= height:
        return

    x0 = x_min + (x_max - x_min) * px / width
    y0 = y_min + (y_max - y_min) * py / height

    x = 0.0
    y = 0.0
    iteration = 0
    while (x*x + y*y <= 4.0) and (iteration < max_iter):
        xtemp = x*x - y*y + x0
        y = 2*x*y + y0
        x = xtemp
        iteration += 1

    output[py, px] = int(255 * iteration / max_iter)



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

    # Przygotowanie obrazu w GPU
    output = np.zeros((task.height, task.width), dtype=np.uint8)
    d_output = cuda.to_device(output)

    threadsperblock = (16, 16)
    blockspergrid_x = (task.width + threadsperblock[0] - 1) // threadsperblock[0]
    blockspergrid_y = (task.height + threadsperblock[1] - 1) // threadsperblock[1]
    blockspergrid = (blockspergrid_x, blockspergrid_y)

    mandelbrot_kernel[blockspergrid, threadsperblock](task.x_min, task.x_max,
                                                      task.y_min, task.y_max,
                                                      task.width, task.height,
                                                      task.max_iter,
                                                      d_output)
    d_output.copy_to_host(output)  # pobranie wyniku z GPU

    # Tworzymy obraz w pamięci
    img = Image.fromarray(output, mode='L')
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    with progress_lock:
        is_busy = False
        current_progress = total_rows  # 100%

    end_time = time.time()
    print(f"Completed in {end_time - start_time:.2f}s")

    return StreamingResponse(buf, media_type="image/png")

