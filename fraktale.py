import requests
import random
import time
import threading
from PIL import Image, ImageTk
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
import tkinter as tk
from tkinter import ttk, messagebox

# ==========================================
WORKERS = [
    "http://127.0.0.1:8000",
]

# ==========================================
# GLOBALNE ZMIENNE DO OBSŁUGI WIDOKU
center_x = -0.5
center_y = 0.0
scale = 1.5
canvas_width = 600
canvas_height = 600
drag_start = None
last_img = None  # ostatnio wygenerowany obraz (PIL)

# ==========================================
def generate_fractal(size, progress_var, progress_label, canvas):
    global center_x, center_y, scale, canvas_width, canvas_height, last_img

    width = height = size
    max_iter = 100

    x_min = center_x - scale
    x_max = center_x + scale
    y_min = center_y - scale
    y_max = center_y + scale
    tile_h = height // len(WORKERS)

    tasks = []
    for i, worker in enumerate(WORKERS):
        y1 = y_min + i * (y_max - y_min) / len(WORKERS)
        y2 = y_min + (i + 1) * (y_max - y_min) / len(WORKERS)
        task = {
            "url": worker + "/compute",
            "progress_url": worker + "/percentcomplete",
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
            "offset_y": i * tile_h
        }
        tasks.append(task)

    all_tiles = []
    with ThreadPoolExecutor(max_workers=len(WORKERS)) as executor:
        futures = {}
        for t in tasks:
            future = executor.submit(requests.post, t["url"], json=t["data"])
            futures[future] = t

        completed = 0
        while completed < len(WORKERS):
            progresses = []
            for t in tasks:
                try:
                    r = requests.get(t["progress_url"], timeout=0.5)
                    if r.status_code == 200:
                        data = r.json()
                        progresses.append(data.get("progress", 0))
                except Exception:
                    progresses.append(0)

            if progresses:
                avg_progress = sum(progresses) / len(progresses)
                progress_var.set(avg_progress)
                progress_label.config(text=f"Postęp: {avg_progress:.2f}%")
                root.update_idletasks()

            completed = sum(1 for f in futures if f.done())
            time.sleep(0.5)

        # odbieranie wyników
        for future in as_completed(futures):
            t = futures[future]
            try:
                response = future.result()
                response.raise_for_status()
                img_part = Image.open(BytesIO(response.content)).convert("L")
                all_tiles.append((t["offset_y"], img_part))
            except Exception as e:
                messagebox.showerror("Błąd", f"Błąd od {t['url']}: {e}")

    # składanie końcowego obrazu
    final_img = Image.new("L", (width, height))
    for offset_y, tile_img in all_tiles:
        final_img.paste(tile_img, (0, offset_y))

    last_img = final_img  # zapisujemy do globalnego podglądu

    img_resized = final_img.resize((canvas_width, canvas_height))
    img_tk = ImageTk.PhotoImage(img_resized)
    canvas.delete("all")
    canvas.create_image(0, 0, anchor="nw", image=img_tk)
    canvas.image = img_tk

    progress_var.set(100)
    progress_label.config(text="✅ Zakończono")

# ==========================================
# FUNKCJE INTERAKCJI
def start_computation():
    try:
        size = int(size_entry.get())
        if size < 100:
            raise ValueError
    except ValueError:
        messagebox.showerror("Błąd", "Podaj poprawny rozmiar (>100)")
        return
    progress_var.set(0)
    progress_label.config(text="Postęp: 0%")
    threading.Thread(target=generate_fractal, args=(size, progress_var, progress_label, canvas), daemon=True).start()

def on_mouse_down(event):
    global drag_start
    drag_start = (event.x, event.y)

def on_mouse_move(event):
    global drag_start, center_x, center_y, last_img
    if drag_start and last_img:
        dx = event.x - drag_start[0]
        dy = event.y - drag_start[1]
        center_x -= (dx / canvas_width) * (2 * scale)
        center_y -= (dy / canvas_height) * (2 * scale)
        drag_start = (event.x, event.y)

        # podgląd aktualnego przesunięcia
        img_resized = last_img.resize((canvas_width, canvas_height))
        img_tk = ImageTk.PhotoImage(img_resized)
        canvas.delete("all")
        canvas.create_image(0, 0, anchor="nw", image=img_tk)
        canvas.image = img_tk

def on_mouse_up(event):
    global drag_start
    drag_start = None

def on_scroll(event):
    global scale, last_img
    if last_img:
        factor = 0.9 if event.delta > 0 else 1.1
        scale *= factor

        # podgląd zoomu
        img_resized = last_img.resize((canvas_width, canvas_height))
        img_tk = ImageTk.PhotoImage(img_resized)
        canvas.delete("all")
        canvas.create_image(0, 0, anchor="nw", image=img_tk)
        canvas.image = img_tk

# ==========================================
# GUI
root = tk.Tk()
root.title("Interaktywny Mandelbrot")

tk.Label(root, text="Rozmiar obrazu (px):").pack()
size_entry = tk.Entry(root)
size_entry.insert(0, "800")
size_entry.pack()

ttk.Button(root, text="Start", command=start_computation).pack(pady=5)

progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100, length=400)
progress_bar.pack(pady=5)
progress_label = tk.Label(root, text="Postęp: 0%", font=("Segoe UI", 10))
progress_label.pack(pady=5)

canvas = tk.Canvas(root, width=canvas_width, height=canvas_height, bg="black")
canvas.pack(pady=10)

canvas.bind("<ButtonPress-1>", on_mouse_down)
canvas.bind("<B1-Motion>", on_mouse_move)
canvas.bind("<ButtonRelease-1>", on_mouse_up)
canvas.bind("<MouseWheel>", on_scroll)
canvas.bind("<Button-4>", lambda e: on_scroll(e))  # Linux scroll up
canvas.bind("<Button-5>", lambda e: on_scroll(e))  # Linux scroll down

root.mainloop()
