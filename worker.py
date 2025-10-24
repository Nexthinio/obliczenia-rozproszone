import threading
import time
from io import BytesIO

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
import cupy as cp
from PIL import Image

app = FastAPI()

# =============================
# GLOBALNE ZMIENNE DO POSTĘPU
# =============================
progress_lock = threading.Lock()
current_progress = 0
total_steps = 1
is_busy = False


class Task(BaseModel):
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    width: int
    height: int
    max_iter: int


@app.get("/test")
def test():
    return {"message": "Test działa poprawnie"}


@app.get("/percentcomplete")
def percent_complete():
    with progress_lock:
        percent = (current_progress / total_steps) * 100
        status = "busy" if is_busy else "idle"
    return {"status": status, "progress": round(percent, 2)}


@app.post("/compute")
def compute(task: Task):
    global current_progress, total_steps, is_busy

    print("Otrzymano zadanie\n")
    start_time = time.time()

    with progress_lock:
        current_progress = 0
        total_steps = task.max_iter
        is_busy = True

    # Tworzymy siatki współrzędnych na GPU
    xs = cp.linspace(task.x_min, task.x_max, task.width)
    ys = cp.linspace(task.y_min, task.y_max, task.height)
    xs_grid, ys_grid = cp.meshgrid(xs, ys)
    c = xs_grid + 1j * ys_grid

    # Mandelbrot na GPU, w pełni wektorowo
    z = cp.zeros_like(c, dtype=cp.complex128)
    count = cp.zeros(c.shape, dtype=cp.int32)

    for i in range(task.max_iter):
        mask = cp.abs(z) <= 2
        z[mask] = z[mask]**2 + c[mask]
        count[mask] += 1

        # aktualizacja postępu co ~1%
        if (i % max(1, task.max_iter // 100)) == 0:
            with progress_lock:
                current_progress = i + 1

    output = cp.floor(255 * count / task.max_iter).astype(cp.uint8)

    # Konwersja do CPU i zapis do PNG
    img = Image.fromarray(cp.asnumpy(output), mode='L')
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    with progress_lock:
        is_busy = False
        current_progress = total_steps

    end_time = time.time()
    print(f"Completed in {end_time - start_time:.2f}s")

    return StreamingResponse(buf, media_type="image/png")