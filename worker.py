from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Tuple
import uvicorn
import numpy as np
from concurrent.futures import ProcessPoolExecutor

app = FastAPI()

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
        z = z*z + c
        if abs(z) > 2:
            return i
    return max_iter

def compute_row(args) -> List[Tuple[int,int,int]]:
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

@app.post("/compute")
def compute(task: Task):
    print("Otrzymano zadanie")
    xs = np.linspace(task.x_min, task.x_max, task.width)
    ys = np.linspace(task.y_min, task.y_max, task.height)

    # przygotowanie argumentów dla wierszy
    args_list = [(py, y, xs, task.max_iter) for py, y in enumerate(ys)]

    # równoległe obliczenia
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(compute_row, args_list))

    # spłaszczamy wynik
    flat_result = [pixel for row in results for pixel in row]

    return {"data": flat_result}
14:31
Mateusz Pruszkowski
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Tuple
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
from PIL import Image

app = FastAPI()

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
        z = z*z + c
        if abs(z) > 2:
            return i
    return max_iter

def compute_row(args) -> List[Tuple[int,int,int]]:
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

@app.post("/compute")
def compute(task: Task):
    print("Otrzymano zadanie")
    xs = np.linspace(task.x_min, task.x_max, task.width)
    ys = np.linspace(task.y_min, task.y_max, task.height)

    # przygotowanie argumentów dla wierszy
    args_list = [(py, y, xs, task.max_iter) for py, y in enumerate(ys)]

    results = []
    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(compute_row, args) for args in args_list]
        for f in tqdm(as_completed(futures), total=len(futures), desc="Obliczenia"):
            results.append(f.result())

    # spłaszczamy wynik
    flat_result = [pixel for row in results for pixel in row]

    # Tworzymy obraz lokalnie
    image_array = np.zeros((task.height, task.width), dtype=np.uint8)
    for x, y, color in flat_result:
        image_array[y, x] = color

    img = Image.fromarray(image_array, mode='L')  # 'L' = grayscale
    img.save("mandelbrot_result.png")
    print("Zapisano obraz: mandelbrot_result.png")

    return {"data": flat_result}