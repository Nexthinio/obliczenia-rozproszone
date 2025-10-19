import threading
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import requests
import random
import time
from PIL import Image, ImageTk
from io import BytesIO
import tkinter as tk
from tkinter import ttk, messagebox

# ==========================================
# KONFIGURACJA
# ==========================================
WORKERS = [
    {"name": "localhost", "url": "http://127.0.0.1:8000"},
    {"name": "daniel", "url": "http://26.75.133.14:8000"},
    #{"name": "mati komp", "url": "http://26.244.65.123:8000"},
    #{"name": "mati laptop", "url": "http://26.69.88.88:8000"},
]

finished = multiprocessing.Value('i', 0)  # współdzielony licznik zakończonych bloków

# ==========================================
# FUNKCJA OBLICZENIOWA (SERWER)
# ==========================================
def worker_task(worker_idx, y_start, y_end, width, height, x_min, x_max, y_min, y_max, max_iter):
    """Funkcja wykonywana w osobnym procesie"""
    start_time = time.time()
    y1 = y_min + (y_start / height) * (y_max - y_min)
    y2 = y_min + (y_end / height) * (y_max - y_min)
    data = {
        "x_min": x_min,
        "x_max": x_max,
        "y_min": y1,
        "y_max": y2,
        "width": width,
        "height": y_end - y_start,
        "max_iter": max_iter
    }
    url = WORKERS[worker_idx]["url"] + "/compute"
    offset_y = y_start
    name = WORKERS[worker_idx]["name"]

    try:
        r = requests.post(url, json=data)
        print(f"🚩 Wysłano request do {name}. Blok {y_start}-{y_end}")
        r.raise_for_status()
        img_part = Image.open(BytesIO(r.content)).convert("L")
        end_time = time.time()
        print(f"✅ {name} skończył blok {y_start}-{y_end} w {end_time - start_time:.2f}s")
        with finished.get_lock():
            finished.value += 1
        return (offset_y, img_part)
    except Exception as e:
        print(f"❌ Błąd od {name}: {e}")
        return None

def generate_fractal(size, progress_var, progress_label, canvas):
    full_start_time = time.time()
    width = height = size
    zoom = random.uniform(0.5, 2)
    center_x = random.uniform(-0.7, 0.3)
    center_y = random.uniform(-0.5, 0.5)
    max_iter = 100

    scale = 1.5 / zoom
    x_min = center_x - scale
    x_max = center_x + scale
    y_min = center_y - scale
    y_max = center_y + scale

    print("==============================================")
    print(f"Size: {size}x{size}")
    print(f"Zoom: {zoom:.4f}")
    print(f"Center: ({center_x:.4f}, {center_y:.4f})")
    print(f"Max iterations: {max_iter}")
    print(f"x_min: {x_min:.4f}, x_max: {x_max:.4f}")
    print(f"y_min: {y_min:.4f}, y_max: {y_max:.4f}")
    print("==============================================")

    # Generowanie bloków po 500 pikseli
    block_size = 1000
    if height > block_size * len(WORKERS):
        blocks = []
        current_y = 0
        while current_y < height:
            end_y = min(current_y + block_size, height)
            blocks.append((current_y, end_y))
            current_y = end_y
    else:
        tile_h = height // len(WORKERS)
        blocks = [(i * tile_h, (i + 1) * tile_h) for i in range(len(WORKERS))]

    all_tiles = []

    with ProcessPoolExecutor(max_workers=len(WORKERS)) as executor:
        remaining_blocks = blocks.copy()
        futures = {}

        # Przydziel pierwsze bloki do wszystkich workerów
        for i, worker in enumerate(WORKERS):
            if remaining_blocks:
                y_start, y_end = remaining_blocks.pop(0)
                future = executor.submit(worker_task, i, y_start, y_end,
                                         width, height, x_min, x_max, y_min, y_max, max_iter)
                futures[future] = i

        # Monitorowanie i dynamiczne przydzielanie bloków
        while futures:
            for future in as_completed(list(futures.keys())):
                worker_idx = futures.pop(future)
                result = future.result()
                if result:
                    all_tiles.append(result)

                # Przydziel nowy blok, jeśli są
                if remaining_blocks:
                    y_start, y_end = remaining_blocks.pop(0)
                    new_future = executor.submit(worker_task, worker_idx, y_start, y_end,
                                                 width, height, x_min, x_max, y_min, y_max, max_iter)
                    futures[new_future] = worker_idx

                # Aktualizacja paska postępu
                progress_var.set((finished.value * block_size / height) * 100)
                progress_label.config(text=f"Postęp: {progress_var.get():.2f}%")
                canvas.update_idletasks()

    # Składanie obrazu
    final_img = Image.new("L", (width, height))
    for offset_y, tile_img in sorted(all_tiles):
        final_img.paste(tile_img, (0, offset_y))

    final_img.save("fraktale.png")

    img_resized = final_img.resize((600, 600))
    img_tk = ImageTk.PhotoImage(img_resized)
    canvas.create_image(0, 0, anchor="nw", image=img_tk)
    canvas.image = img_tk

    progress_var.set(100)
    progress_label.config(text=f"✅ Zakończono — Czas całkowity: {time.time() - full_start_time:.2f}s")


# ==========================================
# GUI
# ==========================================
def start_computation():
    try:
        size = int(size_entry.get())
        if size < 100:
            raise ValueError
    except ValueError:
        messagebox.showerror("Błąd", "Podaj poprawny rozmiar (liczba całkowita > 100).")
        return

    progress_var.set(0)
    progress_label.config(text="Postęp: 0.00%")
    threading.Thread(target=generate_fractal, args=(size, progress_var, progress_label, canvas), daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Mandelbrot Distributed Generator")

    tk.Label(root, text="Rozmiar obrazu (np. 2000):", font=("Segoe UI", 11)).pack(pady=5)
    size_entry = tk.Entry(root, font=("Segoe UI", 11), justify="center")
    size_entry.insert(0, "8000")
    size_entry.pack(pady=5)

    ttk.Button(root, text="Start", command=start_computation).pack(pady=10)

    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100, length=400)
    progress_bar.pack(pady=5)
    progress_label = tk.Label(root, text="Postęp: 0.00%", font=("Segoe UI", 10))
    progress_label.pack(pady=5)

    canvas = tk.Canvas(root, width=600, height=600, bg="black")
    canvas.pack(pady=10)

    root.mainloop()
