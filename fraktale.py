import requests
import random
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO

# IP komputerów w sieci LAN
WORKERS = [
    "http://10.6.80.16:8000",
    "http://10.6.80.19:8000",
]

# ==========================================
# Parametry fraktala
# ==========================================
width, height = 1600, 1600
zoom = random.uniform(0.5, 10)
center_x = random.uniform(-0.7, 0.3)
center_y = random.uniform(-0.5, 0.5)
max_iter = 100

scale = 1.5 / zoom
x_min = center_x - scale
x_max = center_x + scale
y_min = center_y - scale
y_max = center_y + scale

tile_h = height // len(WORKERS)

# ==========================================
# Tworzenie zadań dla workerów
# ==========================================
tasks = []
for i, worker in enumerate(WORKERS):
    y1 = y_min + i * (y_max - y_min) / len(WORKERS)
    y2 = y_min + (i + 1) * (y_max - y_min) / len(WORKERS)

    task = {
        "url": worker + "/compute",
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

# ==========================================
# Wysyłanie zadań równolegle
# ==========================================
all_tiles = []
with ThreadPoolExecutor(max_workers=len(WORKERS)) as executor:
    futures = {}
    for t in tasks:
        print(f"➡️ Wysyłam zadanie #{t['id']} do {t['url']} "
              f"→ fragment Y:[{t['data']['y_min']:.3f}, {t['data']['y_max']:.3f}] (offset={t['offset_y']})")
        future = executor.submit(requests.post, t["url"], json=t["data"])
        futures[future] = t

    for future in as_completed(futures):
        t = futures[future]
        try:
            response = future.result()
            response.raise_for_status()

            # 🔹 odbieramy obraz binarny
            img_part = Image.open(BytesIO(response.content)).convert("L")

            # zachowujemy fragment z offsetem
            all_tiles.append((t["offset_y"], img_part))
            print(f"✅ Odpowiedź z {t['url']} (zadanie #{t['id']}) — OK, fragment {img_part.size}")
        except Exception as e:
            print(f"❌ Błąd od {t['url']} (zadanie #{t['id']}): {e}")

# ==========================================
# Składanie obrazu końcowego
# ==========================================
final_img = Image.new("L", (width, height))

for offset_y, tile_img in all_tiles:
    final_img.paste(tile_img, (0, offset_y))
    print(f"🧩 Wklejono kafelek na pozycję Y={offset_y}")

# ==========================================
# Zapis końcowego fraktala
# ==========================================
final_img.save("mandelbrot_distributed.png")
print("✅ Zapisano mandelbrot_distributed.png")
