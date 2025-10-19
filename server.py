import requests
import random
import time
import sys
import threading
from PIL import Image, ImageTk
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
import tkinter as tk
from tkinter import ttk, messagebox

# ==========================================
# KONFIGURACJA
# ==========================================
WORKERS = [
    {"name": "localhost", "url": "http://127.0.0.1:8000"},
    {"name": "macbook", "url":  "http://192.168.18.39:8000"},
]

# ==========================================
# FUNKCJA OBLICZENIOWA (SERWER)
# ==========================================
def generate_fractal(size, progress_var, progress_label, canvas):
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
    tile_h = height // len(WORKERS)

    print("==============================================")
    print(f"Size: {size}x{size}")
    print(f"Zoom: {zoom:.4f}")
    print(f"Center: ({center_x:.4f}, {center_y:.4f})")
    print(f"Max iterations: {max_iter}")
    print(f"x_min: {x_min:.4f}, x_max: {x_max:.4f}")
    print(f"y_min: {y_min:.4f}, y_max: {y_max:.4f}")
    print("==============================================")

    tasks = []
    for i, worker in enumerate(WORKERS):
        y1 = y_min + i * (y_max - y_min) / len(WORKERS)
        y2 = y_min + (i + 1) * (y_max - y_min) / len(WORKERS)

        task = {
            "url": worker["url"] + "/compute",
            "progress_url": worker["url"] + "/percentcomplete",
            "data": {
                "x_min": x_min,
                "x_max": x_max,
                "y_min": y1,
                "y_max": y2,
                "width": width,
                "height": tile_h,
                "max_iter": max_iter
            },
            "id": i,
            "offset_y": i * tile_h,
            "name": worker["name"]  # <-- dodajemy nazwę
        }
        tasks.append(task)

    start_time = time.time()
    all_tiles = []
    with ThreadPoolExecutor(max_workers=len(WORKERS)) as executor:
        futures = {}
        for t in tasks:
            future = executor.submit(requests.post, t["url"], json=t["data"])
            futures[future] = t

        # inicjalizacja listy z ostatnim postępem dla każdego workera
        worker_progresses = [0] * len(WORKERS)

        # monitorowanie postępu
        completed = 0
        total = len(WORKERS)
        while completed < total:
            for idx, t in enumerate(tasks):
                try:
                    r = requests.get(t["progress_url"], timeout=0.5)
                    if r.status_code == 200:
                        data = r.json()
                        # aktualizujemy tylko jeśli endpoint odpowiada
                        worker_progresses[idx] = data.get("progress", worker_progresses[idx])
                except Exception:
                    # jeśli worker nie odpowiada, zostawiamy ostatni postęp
                    pass

            # średnia po ostatnich znanych postępach
            avg_progress = sum(worker_progresses) / len(worker_progresses)
            progress_var.set(avg_progress)
            progress_label.config(text=f"Postęp: {avg_progress:.2f}%")
            root.update_idletasks()

            completed = sum(1 for f in futures if f.done())
            time.sleep(1)

        end_time_calculating = time.time()
        # odbieranie wyników
        for future in as_completed(futures):
            t = futures[future]
            try:
                response = future.result()
                response.raise_for_status()

                img_part = Image.open(BytesIO(response.content)).convert("L")
                all_tiles.append((t["offset_y"], img_part))
                print(f"✅ Odpowiedź z {t['name']} (zadanie #{t['id']}) — OK, fragment {img_part.size}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Błąd od {t['url']}: {e}")

    # składanie końcowego obrazu
    final_img = Image.new("L", (width, height))
    for offset_y, tile_img in all_tiles:
        final_img.paste(tile_img, (0, offset_y))

    final_img.save("fraktale.png")

    end_time_all = time.time()
    # wyświetlenie w GUI
    img_resized = final_img.resize((600, 600))
    img_tk = ImageTk.PhotoImage(img_resized)
    canvas.create_image(0, 0, anchor="nw", image=img_tk)
    canvas.image = img_tk

    progress_var.set(100)
    progress_label.config(text=f"✅ Zakończono — Czas bez generowania obrazu: {end_time_calculating - start_time:.2f}s, Czas całkowity: {end_time_all - start_time:.2f}s")

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

root = tk.Tk()
root.title("Mandelbrot Distributed Generator")

tk.Label(root, text="Rozmiar obrazu (np. 2000):", font=("Segoe UI", 11)).pack(pady=5)
size_entry = tk.Entry(root, font=("Segoe UI", 11), justify="center")
size_entry.insert(0, "1000")
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
