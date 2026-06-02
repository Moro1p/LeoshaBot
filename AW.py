import pygame as py
import win32api
import win32con
import win32gui
import pyaudio
import numpy as np
import time
import sys
from pathlib import Path
import random
import threading
import queue
import tkinter as tk
from tkinter import filedialog, messagebox, Listbox, Button, Label, Frame
import shutil

sys.stdout.reconfigure(encoding='utf-8')

# ---------------------------
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
WINDOW_WIDTH = 500   # Размеры окна витуберки (размер спрайта уменьшается пропорционально)
WINDOW_HEIGHT = 500
window_screen = None
hwnd = None
CHUNK_SIZE = 1024
MAX_SHAKE_PX = 0.5  # МОДИФИКАТОР ТРЯСКИ

# Потокобезопасность
layers_lock = threading.Lock()
command_queue = queue.Queue()
gui_running = True

# Список слоёв и активный индекс
layers = []
active_layer_index = 0

# ---------------------------
# ДВИЖЕНИЕ ОКНА
# ---------------------------
def move_window():
    hwnd = py.display.get_wm_info()["window"]
    x, y = win32api.GetCursorPos()
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, x-350, y-350, 0, 0, win32con.SWP_NOSIZE)

def resize_window(new_width, new_height):
    global WINDOW_WIDTH, WINDOW_HEIGHT, window_screen, hwnd
    rect = win32gui.GetWindowRect(hwnd)
    WINDOW_WIDTH = new_width
    WINDOW_HEIGHT = new_height
    window_screen = py.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), py.NOFRAME | py.SRCALPHA)
    hwnd = py.display.get_wm_info()["window"]
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST,
                          rect[2] - WINDOW_WIDTH, rect[3] - WINDOW_HEIGHT,
                          WINDOW_WIDTH, WINDOW_HEIGHT, 0)

# ---------------------------
# ГРОМКОСТЬ
# ---------------------------
def get_loudness(stream):
    try:
        data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
        samples = np.frombuffer(data, dtype=np.int16)
        return np.abs(samples).mean()
    except:
        return 0

# ---------------------------
# ЗАГРУЗКА ИЗОБРАЖЕНИЙ
# ---------------------------
def load_img(path):
    return py.image.load(path).convert_alpha()

class Layer:
    def __init__(self, dir_path, layer_id):
        self.id = layer_id
        self.name = dir_path.name
        self.frames = []
        self.cur_frame_id = 0
        png_files = sorted(dir_path.glob("*.png"), key=lambda p: int(p.stem))
        for img_path in png_files:
            self.frames.append(load_img(img_path))
        if not self.frames:
            raise ValueError(f"В папке {dir_path} нет PNG файлов")

    def render(self, window_width, window_height, margin, window_screen, shake_level=0.0):
        if not self.frames:
            return
        frame = self.frames[self.cur_frame_id]
        orig_w = frame.get_width()
        orig_h = frame.get_height()
        scale_w = window_width / orig_w
        scale_h = window_height / orig_h
        scale = min(scale_w, scale_h)
        scaled_width = int(orig_w * scale)
        scaled_height = int(orig_h * scale)
        scaled_sprite = py.transform.scale(frame, (scaled_width, scaled_height))
        base_x = window_width - scaled_width - margin
        base_y = window_height - scaled_height - margin
       
        if shake_level > 0:
            max_offset = int(MAX_SHAKE_PX * shake_level * len(self.frames)) # Тут можно менять разброс тряски
            # if not self.cur_frame_id: max_offset = 0
            offset_x = random.randint(-max_offset, max_offset)
            offset_y = random.randint(-max_offset, max_offset)
            pos_x = base_x + offset_x
            pos_y = base_y + offset_y
        else:
            pos_x = base_x
            pos_y = base_y
        window_screen.blit(scaled_sprite, (pos_x, pos_y))

    def on_loudness_check(self, level):
        if not self.frames:
            return
        mouth_index = round(level * (len(self.frames) - 1))
        # print(level, mouth_index, len(self.frames))
        if abs(mouth_index - self.cur_frame_id) > 1:  # Штука чтобы спрайт не перескакивал серез спрайты (с 0.png на 4.png например)
            self.cur_frame_id += (1 if mouth_index > self.cur_frame_id else -1)
        else:
            self.cur_frame_id = mouth_index

# ---------------------------
# ОБРАБОТКА КОМАНД ИЗ ОЧЕРЕДИ
# ---------------------------
def process_gui_commands():
    global active_layer_index, layers, close
    try:
        while True:
            cmd, data = command_queue.get_nowait()
            if cmd == "add_layer":
                folder_path = data
                try:
                    new_layer = Layer(Path(folder_path), len(layers))
                    with layers_lock:
                        layers.append(new_layer)
                    with layers_lock:
                        active_layer_index = len(layers) - 1
                except Exception as e:
                    print(f"Ошибка добавления витуберки: {e}")

            elif cmd == "remove_layer":
                idx = data
                with layers_lock:
                    if 0 <= idx < len(layers):
                        # Удаляем папку с диска
                        layer_to_remove = layers[idx]
                        folder_path = Path("./Sprites") / layer_to_remove.name
                        try:
                            if folder_path.exists():
                                shutil.rmtree(folder_path)
                        except Exception as e:
                            print(f"Ошибка удаления папки {folder_path}: {e}")
                        # Удаляем из списка слоёв
                        del layers[idx]
                        if active_layer_index >= len(layers):
                            active_layer_index = max(0, len(layers) - 1)

            elif cmd == "set_active":
                idx = data
                with layers_lock:
                    if 0 <= idx < len(layers):
                        active_layer_index = idx
            elif cmd == "quit":
                close = True
            elif cmd == "refresh_gui":
                pass
    except queue.Empty:
        pass

# ---------------------------
# GUI НА TKINTER (отдельный поток)
# ---------------------------
class LayerManagerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Управление витуберками")
        self.root.geometry("400x350")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Список слоёв
        self.listbox = tk.Listbox(main_frame, selectmode=tk.SINGLE)
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind("<Double-Button-1>", self.on_select)

        # Кнопка Добавить
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        tk.Button(btn_frame, text="Добавить витуберку", command=self.add_layer).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Удалить витуберку", command=self.remove_layer).pack(side=tk.LEFT, padx=2)

        self.refresh_listbox()
        
    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        with layers_lock:
            for layer in layers:
                self.listbox.insert(tk.END, layer.name)
            print(active_layer_index)
            if 0 <= active_layer_index < len(layers):
                self.listbox.selection_set(active_layer_index)
                

    def add_layer(self):
        folder_selected = filedialog.askdirectory(title="Выберите папку со спрайтами")
        if folder_selected:
            src_path = Path(folder_selected)
            dst_path = Path("./Sprites") / src_path.name
            try:
                if dst_path.exists():  
                    shutil.rmtree(dst_path)
                shutil.copytree(src_path, dst_path)
                command_queue.put(("add_layer", str(dst_path)))
                self.root.after(100, self.refresh_listbox)
            except Exception as e:
                messagebox.showerror("Ошибка копирования", f"Не удалось скопировать папку:\n{e}")

    def remove_layer(self):
        selection = self.listbox.curselection()
        if selection:
            idx = selection[0]
            if len(layers) <= 1:
                messagebox.showwarning("Предупреждение", "Нельзя удалить последний слой.")
                return
            layer_name = layers[idx].name
            if messagebox.askyesno("Подтверждение", f"Удалить слой '{layer_name}'?\nПапка будет удалена с диска."):
                command_queue.put(("remove_layer", idx))
                self.root.after(100, self.refresh_listbox)

    def on_select(self, event=None):
        selection = self.listbox.curselection()
        if selection:
            idx = selection[0]
            command_queue.put(("set_active", idx))
           

    def on_close(self):
        command_queue.put(("quit", None))
        self.root.destroy()

    def run(self):
        self.root.mainloop()

def gui_thread_func():
    global gui_running
    app = LayerManagerGUI()
    app.run()
    gui_running = False

# ---------------------------
# INIT PYGAME
# ---------------------------
py.init()
window_screen = py.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), py.NOFRAME)
hwnd = py.display.get_wm_info()["window"]
win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
    win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(255, 0, 128), 0, win32con.LWA_COLORKEY)

# ---------------------------
# ЗАГРУЗКА СЛОЁВ ИЗ ПАПКИ SPRITES
# ---------------------------
root_dir = Path("./Sprites")
for subdir in root_dir.iterdir():
    if not subdir.is_dir():
        continue
    try:
        layers.append(Layer(subdir, len(layers)))
    except Exception as e:
        print(f"Ошибка загрузки {subdir}: {e}")
if not layers:
    print("Нет ни одного слоя! Создайте папку Sprites с подпапками, содержащими PNG-кадры.")
    sys.exit(1)

layers.sort(key=lambda x: x.name)
active_layer_index = 0

# ---------------------------
# АУДИО
# ---------------------------
p = pyaudio.PyAudio()
try:
    default_device = p.get_default_input_device_info()
    device_index = default_device['index']
    print(f"Используется микрофон: {default_device['name']}")
except:
    device_index = 1
    print("Не удалось определить микрофон по умолчанию, используется индекс 1")

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
stream = p.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    input_device_index=device_index,
    frames_per_buffer=CHUNK_SIZE
)


# ---------------------------
# CALIBRATION
# ---------------------------
# print("Калибровка... молчи")

# noise_samples = []
# start = time.time()

# while time.time() - start < 2:
#     noise_samples.append(get_loudness(stream))
# BACKGROUND_NOISE = np.mean(noise_samples)
BACKGROUND_NOISE = 20

# DYNAMIC_MAX = BACKGROUND_NOISE * 10   #- ДЛЯ ДИНАМИЧЕСКОГО ИЗМЕНЕНИЯ МАКС.ГРОМКОСТИ

# print("Калибровка... кричи")

# noise_samples = []
# start = time.time()

# while time.time() - start < 2:
#     noise_samples.append(get_loudness(stream))
# CONSTANT_MAX = np.mean(noise_samples)
CONSTANT_MAX = 800



DYNAMIC_MAX = CONSTANT_MAX
SMOOTHING = 0.8
smoothed_level = 0.0
print("Noise floor:", BACKGROUND_NOISE)

# ---------------------------
# FPS CONTROL
# ---------------------------
clock = py.time.Clock()
fps_update_interval = 1.0

# ---------------------------
# ЗАПУСК GUI ПОТОКА
# ---------------------------
gui_thread = threading.Thread(target=gui_thread_func, daemon=True)
gui_thread.start()

# ---------------------------
# MAIN LOOP
# ---------------------------
close = False
while not close:
    clock.tick(60)
    current_fps = clock.get_fps()
    now = time.time()

    # Обработка событий Pygame
    for event in py.event.get():
        # if py.mouse.get_pressed()[0]:            # Раскоментируй это чтобы витуберка обновлялась при перемещении
        #     py.event.get()
        #     move_window()
        if event.type == py.QUIT:
            close = True
        elif event.type == py.MOUSEBUTTONDOWN:     #  Закоментируй это чтобы витуберка обновлялась при перемещении
            while py.mouse.get_pressed()[0]:       #
                py.event.get()                     #
                move_window()                      #
        elif event.type == py.KEYDOWN: 
            if event.key == py.K_EQUALS or event.key == py.K_PLUS:
                new_width = int(WINDOW_WIDTH * 1.1)
                new_height = int(WINDOW_HEIGHT * 1.1)
                resize_window(new_width, new_height)
            elif event.key == py.K_MINUS:
                new_width = int(WINDOW_WIDTH * 0.9)
                new_height = int(WINDOW_HEIGHT * 0.9)
                resize_window(new_width, new_height)

    # Обработка команд из GUI
    process_gui_commands()

    # Аудио-анализ
    loudness = get_loudness(stream) - BACKGROUND_NOISE

    # if loudness >= DYNAMIC_MAX: DYNAMIC_MAX = loudness
    # else: DYNAMIC_MAX = max(CONSTANT_MAX, DYNAMIC_MAX * 0.995)
    # level = loudness / DYNAMIC_MAX  # ДЛЯ ДИНАМИЧЕСКОГО ИЗМЕНЕНИЯ МАКС.ГРОМКОСТИ

    if loudness > CONSTANT_MAX: loudness = CONSTANT_MAX
    level = loudness / CONSTANT_MAX

    if level < 0.05: level = 0

    smoothed_level = abs(SMOOTHING * smoothed_level + (1 - SMOOTHING) * level)

    if smoothed_level < 0.05: smoothed_level = 0

    window_screen.fill((255, 0, 128))

    with layers_lock:
        if 0 <= active_layer_index < len(layers):
            active_layer = layers[active_layer_index]
        else:
            active_layer = None

    if active_layer:
        active_layer.on_loudness_check(smoothed_level)
        active_layer.render(WINDOW_WIDTH, WINDOW_HEIGHT, 0, window_screen, shake_level=smoothed_level)

    py.display.update()

# ---------------------------
# EXIT
# ---------------------------
stream.stop_stream()
stream.close()
p.terminate()
py.quit()
