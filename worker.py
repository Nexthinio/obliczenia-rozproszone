import time
import threading
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
total_rows = 1
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

    # Tworzymy siatki współrzędnych na GPU
    xs = cp.linspace(task.x_min, task.x_max, task.width)
    ys = cp.linspace(task.y_min, task.y_max, task.height)
    xs_grid, ys_grid = cp.meshgrid(xs, ys)

    # Przygotowanie wyniku
    output = cp.zeros((task.height, task.width), dtype=cp.uint8)

    # Funkcja wektorowa dla GPU
    for py in range(task.height):
        x_row = xs_grid[py, :]
        y_val = ys_grid[py, 0]
        z = cp.zeros_like(x_row, dtype=cp.complex128)
        c = x_row + 1j * y_val
        count = cp.zeros_like(x_row, dtype=cp.int32)

        for i in range(task.max_iter):
            mask = cp.abs(z) <= 2
            z[mask] = z[mask] ** 2 + c[mask]
            count[mask] += 1

        output[py, :] = cp.floor(255 * count / task.max_iter).astype(cp.uint8)

        # Aktualizacja postępu co wiersz
        with progress_lock:
            current_progress += 1

    # Konwersja do NumPy (CPU) i zapis do PNG
    img = Image.fromarray(cp.asnumpy(output), mode='L')
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    with progress_lock:
        is_busy = False
        current_progress = total_rows

    end_time = time.time()
    print(f"Completed in {end_time - start_time:.2f}s")

    return StreamingResponse(buf, media_type="image/png")
