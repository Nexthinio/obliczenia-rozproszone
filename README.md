# 🌀 Mandelbrot Distributed Generator

**Mandelbrot Distributed Generator** to projekt demonstrujący **rozproszone obliczenia fraktali (zbioru Mandelbrota)** przy użyciu  
**Python + FastAPI + Tkinter + multiprocessing + CUDA (CUPY)**.  

System składa się z aplikacji klienckiej (GUI) i jednego lub wielu serwerów obliczeniowych („workerów”), które wykonują fragmenty obliczeń równolegle i zwracają części obrazu do złożenia.

---

## 📁 Struktura projektu

```
📦 obliczenia-rozproszone
├── server.py # Klient GUI w Tkinter
├── worker-cpu.py # Serwer obliczeniowy z multiprocessing (CPU)
├── worker.py # Serwer obliczeniowy z CuPy (GPU)
└── README.md
```

---

## 🚀 Opis działania

### 🖥️ Aplikacja kliencka (GUI)

Program `server.py`:

- Uruchamia interfejs graficzny w **Tkinter**  
- Losowo wybiera fragment płaszczyzny zespolonej (centrum i zoom)  
- Dzieli obraz na **bloki** (np. 1000 wierszy) i rozdziela je pomiędzy dostępnych **workerów**  
- Wysyła żądania HTTP **POST `/compute`** do serwerów podanych w tablicy `WORKERS`  
- Łączy otrzymane fragmenty obrazu w jeden plik końcowy **`fraktale.png`**  
- Pokazuje **postęp obliczeń** na pasku w GUI  
- Po zakończeniu – wyświetla obraz fraktala w oknie  

---

## ⚙️ Serwery obliczeniowe (workers)

Każdy worker to serwer **FastAPI**, który implementuje endpoint `/compute`.

### 🧠 `worker.py`
- Wykorzystuje bibliotekę **CuPy** do przyspieszenia obliczeń na **GPU (CUDA)**  
- Idealny dla komputerów z kartą **NVIDIA**  
- Zwraca gotowy fragment fraktala jako obraz **PNG** w strumieniu  

### 🧮 `worker-cpu.py`
- Alternatywna wersja **CPU-only**  
- Korzysta z **ProcessPoolExecutor** do rozproszenia obliczeń na wiele rdzeni  
- Przydatny dla komputerów **bez GPU**

---

## 🔧 Wymagania

### 🐍 Python 3.9+

Zainstaluj wymagane biblioteki:

```bash
pip install fastapi uvicorn pillow numpy cupy requests tkinter
```
Uwaga:
tkinter jest częścią standardowej biblioteki Pythona w większości dystrybucji.
Dla wersji CPU nie jest potrzebne CuPy, wystarczy NumPy.

🧩 Uruchomienie
1️⃣ Uruchom serwery (workers)
Każdy worker to instancja FastAPI.

Przykładowe uruchomienie:
```bash
uvicorn worker:app --host 0.0.0.0 --port 8000
```
lub dla wersji CPU:
```bash
uvicorn worker-cpu:app --host 0.0.0.0 --port 8000
```
Sprawdź, czy port 8000 jest dostępny i otwarty w sieci lokalnej.

2️⃣ Skonfiguruj listę workerów w GUI
W pliku server.py:
```bash
WORKERS = [
    {"name": "PC", "url": "http://127.0.0.1:8000"},
    {"name": "laptop", "url": "http://192.168.100.28:8000"},
]
```
Dodaj tu wszystkie serwery, które chcesz wykorzystać.

3️⃣ Uruchom klienta GUI
```bash
python server.py
```
---
### 🧠 Zasada działania
Klient dzieli obraz na bloki pionowe

Worker zwraca gotowy fragment obrazu PNG

Klient scala wszystkie części w końcowy obraz fraktale.png

Postęp i czas obliczeń są wyświetlane w GUI

---
### 🧵 Wielowątkowość i rozproszenie
Każdy worker działa niezależnie

Klient uruchamia osobny wątek dla każdego serwera

Dzięki temu można łączyć moc kilku komputerów (CPU + GPU) w jednej sieci

---
### 📸 Wynik
Wygenerowany obraz zostaje zapisany jako:
```bash
fraktale.png
```
oraz wyświetlony w GUI w rozdzielczości 600x600.

---
### 🧰 Przykładowy wynik logów
```yaml
Size: 8000x8000
Zoom: 1.4729
Center: (-0.3145, 0.1213)
Max iterations: 100
```

Wysłano request do PC. Blok 0-1000
Wysłano request do laptop. Blok 1000-2000
PC skończył blok 0-1000 w 2.54s
laptop skończył blok 1000-2000 w 3.01s
Zakończono — Całkowity czas: 12.37s
---
### 🧪 Testowanie
Możesz sprawdzić połączenie z workerem:

```bash
curl http://127.0.0.1:8000/test
```
Odpowiedź:
```json
{"message": "Test działa poprawnie"}
```
