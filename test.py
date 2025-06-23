import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
import traceback
import matplotlib.pyplot as plt
import serial
import time
import re
import threading
import math

matplotlib.use("TkAgg")

# === Globals for Monitor Tab ===
data_all = []
serial_port = None
baud_rate = None
producer_thread_started = False

led_bac_blink = False
led_nam_blink = False
led_dong_blink = False
led_tay_blink = False

# === Monitor Functions ===

def blink_leds():
    # Bắc
    current = led_canvas.itemcget(led_bac, "fill")
    if led_bac_blink:
        led_canvas.itemconfig(led_bac, fill="red" if current=="gray" else "gray")
    else:
        led_canvas.itemconfig(led_bac, fill="gray")
    # Nam
    current = led_canvas.itemcget(led_nam, "fill")
    if led_nam_blink:
        led_canvas.itemconfig(led_nam, fill="red" if current=="gray" else "gray")
    else:
        led_canvas.itemconfig(led_nam, fill="gray")
    # Đông
    current = led_canvas.itemcget(led_dong, "fill")
    if led_dong_blink:
        led_canvas.itemconfig(led_dong, fill="red" if current=="gray" else "gray")
    else:
        led_canvas.itemconfig(led_dong, fill="gray")
    # Tây
    current = led_canvas.itemcget(led_tay, "fill")
    if led_tay_blink:
        led_canvas.itemconfig(led_tay, fill="red" if current=="gray" else "gray")
    else:
        led_canvas.itemconfig(led_tay, fill="gray")

    led_canvas.after(200, blink_leds)

def producer():
    global serial_port, baud_rate
    try:
        ser = serial.Serial(serial_port, baud_rate)
    except Exception as e:
        status_label.config(text=f"Lỗi khi mở cổng: {e}")
        return
    time.sleep(1)
    while True:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('ISO-8859-1')
                data_all.append(line)
        except:
            pass

def set_axis_color(ax):
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')
    for spine in ax.spines.values():
        spine.set_edgecolor('white')

def connect_serial():
    global serial_port, baud_rate, producer_thread_started
    serial_port = port_entry.get()
    try:
        baud_rate = int(baud_entry.get())
    except ValueError:
        baud_rate = 9600
    try:
        tmp = serial.Serial(serial_port, baud_rate, timeout=1)
        tmp.close()
        status_label.config(text=f"Serial connected on {serial_port} at {baud_rate} bps")
    except Exception:
        status_label.config(text="Lỗi kết nối cổng serial.")
        return
    if not producer_thread_started:
        threading.Thread(target=producer, daemon=True).start()
        producer_thread_started = True

def update_leds(Bac, Nam, Dong, Tay):
    global led_bac_blink, led_nam_blink, led_dong_blink, led_tay_blink
    led_bac_blink = (Bac == 1)
    led_nam_blink = (Nam == 1)
    led_dong_blink = (Dong == 1)
    led_tay_blink = (Tay == 1)

def update_plots():
    if data_all:
        raw = data_all[-1]
        nums = re.findall(r'-?\d+\.\d+|-?\d+', raw)
        if len(nums) >= 8:
            gx, gy, gz = map(float, nums[:3])
            ax, ay, az = map(float, nums[3:6])
            temp = float(nums[6])
            pres = float(nums[7])

            # update text overlays
            text_gyro_x.set_text(f"GyroX: {gx:.2f}")
            text_gyro_y.set_text(f"GyroY: {gy:.2f}")
            text_gyro_z.set_text(f"GyroZ: {gz:.2f}")
            text_acc_x.set_text(f"AccX: {ax:.2f}")
            text_acc_y.set_text(f"AccY: {ay:.2f}")
            text_acc_z.set_text(f"AccZ: {az:.2f}")
            text_temp.set_text(f"Temp: {temp:.2f}")
            text_pressure.set_text(f"Pressure: {pres:.2f}")

            # append to lists and trim
            for arr, val in [
                (gyro_x_vals, gx), (gyro_y_vals, gy), (gyro_z_vals, gz),
                (acc_x_vals, ax), (acc_y_vals, ay), (acc_z_vals, az),
                (temp_vals, temp), (pressure_vals, pres)
            ]:
                arr.append(val)
                if len(arr) > max_points:
                    arr.pop(0)

            # set data
            line_gyro_x.set_data(range(len(gyro_x_vals)), gyro_x_vals)
            line_gyro_y.set_data(range(len(gyro_y_vals)), gyro_y_vals)
            line_gyro_z.set_data(range(len(gyro_z_vals)), gyro_z_vals)
            line_acc_x.set_data(range(len(acc_x_vals)), acc_x_vals)
            line_acc_y.set_data(range(len(acc_y_vals)), acc_y_vals)
            line_acc_z.set_data(range(len(acc_z_vals)), acc_z_vals)
            line_temp.set_data(range(len(temp_vals)), temp_vals)
            line_pressure.set_data(range(len(pressure_vals)), pressure_vals)

        if len(nums) >= 11:
            try:
                Lat, Lon, Height = map(float, nums[8:11])
                Bac, Nam, Dong, Tay = map(int, nums[12:16])

                lat_value.config(text=f"{Lat:.6f}")
                lon_value.config(text=f"{Lon:.6f}")
                height_value.config(text=f"{Height:.2f}")

                height_vals.append(Height)
                if len(height_vals) > max_points:
                    height_vals.pop(0)
                line_height.set_data(range(len(height_vals)), height_vals)
                text_height.set_text(f"Height: {Height:.2f}")

                # determine deviation
                dirs = []
                revs = []
                if Dong==1: dirs.append("Tây"); revs.append("Đông")
                if Tay==1: dirs.append("Đông"); revs.append("Tây")
                if Bac==1: dirs.append("Nam"); revs.append("Bắc")
                if Nam==1: dirs.append("Bắc"); revs.append("Nam")
                if dirs:
                    status_label.config(text=f"Đang lệch {' '.join(dirs)}, chỉnh về {' '.join(revs)}.")
                else:
                    status_label.config(text="Ổn định vị trí.")
                update_leds(Bac, Nam, Dong, Tay)
            except:
                pass

    plot_canvas.draw()
    root.after(100, update_plots)

# === Globals for Game Tab ===
WIDTH2, HEIGHT2 = 800, 600
cam_x, cam_y, cam_z = 0, 1, -10
fov = 500
t2 = 0.0

def project2(x, y, z):
    dx, dy, dz = x-cam_x, y-cam_y, z-cam_z
    if dz <= 0.1: dz = 0.1
    f = fov / dz
    return dx*f + WIDTH2/2, -dy*f + HEIGHT2/2

def make_box2(cx, cy, cz, w, h, d, color):
    dx, dy, dz = w/2, h/2, d/2
    verts = [
        (cx-dx, cy-dy, cz-dz),(cx+dx, cy-dy, cz-dz),
        (cx+dx, cy+dy, cz-dz),(cx-dx, cy+dy, cz-dz),
        (cx-dx, cy-dy, cz+dz),(cx+dx, cy-dy, cz+dz),
        (cx+dx, cy+dy, cz+dz),(cx-dx, cy+dy, cz+dz),
    ]
    faces = [(0,1,2,3),(4,5,6,7),(0,1,5,4),
             (3,2,6,7),(1,2,6,5),(0,3,7,4)]
    return {'verts': verts, 'faces': faces, 'color': color}

def simulate_movement2():
    global cam_x, cam_y, cam_z, t2
    r = 15
    cam_x = r * math.cos(t2)
    cam_z = -20 + r * math.sin(t2)
    cam_y = 1 + math.sin(t2*0.8)*2
    t2 += 0.02

# build scene2
scene2 = []
sky_color2 = "#87CEEB"
scene2.append(make_box2(0, -1.5, 20, 10, 0.1, 50, "#444444"))
scene2.append(make_box2(0, -1.4, 20, 12, 0.1, 50, "#777777"))
for z in (10,30):
    for x in (-4,4):
        scene2.append(make_box2(x, 2, z, 0.2, 6, 0.2, "#333333"))
        scene2.append(make_box2(x, 5, z, 0.7, 0.7, 0.7, "#FFFF99"))
for z in range(5,50,10):
    for x in (-5,5):
        # make simple tree
        scene2.append(make_box2(x, -1.5+1, z, 0.5, 2, 0.5, "#8B4513"))
        scene2.append(make_box2(x, -1.5+3, z, 2, 2, 2, "#228B22"))
        scene2.append(make_box2(x, -1.5+4, z, 1.5,1.5,1.5, "#2E8B57"))
        scene2.append(make_box2(x, -1.5+5, z, 1,1,1, "#32CD32"))

def draw_balloon2():
    cx, cy = WIDTH2/2, HEIGHT2/2
    rx, ry = 30, 40
    game_canvas.create_oval(cx-rx, cy-ry, cx+rx, cy+ry, fill="#FF6347", outline="black")
    bw, bh = 20, 12
    bx0 = cx-bw/2; by0 = cy+ry+8
    bx1 = cx+bw/2; by1 = by0+bh
    game_canvas.create_rectangle(bx0,by0,bx1,by1, fill="#8B4513", outline="black")
    game_canvas.create_line(cx-rx/2, cy+ry*0.6, bx0,by0)
    game_canvas.create_line(cx+rx/2, cy+ry*0.6, bx1,by0)

def render_game():
    simulate_movement2()
    game_canvas.delete("all")
    game_canvas.configure(bg=sky_color2)
    draw_list = []
    for obj in scene2:
        verts = obj['verts']
        proj = [project2(x,y,z) for x,y,z in verts]
        for face in obj['faces']:
            zavg = sum(verts[i][2] for i in face)/4
            pts = []
            for i in face: pts.extend(proj[i])
            draw_list.append((zavg, pts, obj['color']))
    for _, pts, col in sorted(draw_list, key=lambda x: x[0], reverse=True):
        game_canvas.create_polygon(pts, fill=col, outline="black")
    draw_balloon2()
    game_canvas.after(16, render_game)

# === Main Application ===
root = tk.Tk()
root.title("Rockoon Monitor & Game")
root.geometry("1200x800")
root.configure(bg="red")


# --- Style để notebook và tab nền đen ---
style = ttk.Style()
style.theme_use('default')
# nền sau tabs (phần chứa các tab headers)
style.configure('TNotebook', background='black', borderwidth=0)
# mỗi tab header
style.configure('TNotebook.Tab',
                background='black',
                foreground='white',
                padding=[10, 5])
# màu khi tab được chọn
style.map('TNotebook.Tab',
          background=[('selected','black')],
          foreground=[('selected','white')])



notebook = ttk.Notebook(root)
tab1 = tk.Frame(notebook, bg='black')
tab2 = tk.Frame(notebook, bg='black')
notebook.add(tab1, text="Monitor")
notebook.add(tab2, text="Game")
notebook.pack(fill=tk.BOTH, expand=1)




# --- Build Monitor Tab ---
# Title
title_label = tk.Label(tab1, text="ROCKOON PARAMETER MONITORING",
                       font=("Helvetica",20,"bold"),
                       bg="black", fg="white")
title_label.pack(pady=10)

# Serial frame
serial_frame = tk.Frame(tab1, bg="black")
serial_frame.pack(pady=5)
tk.Label(serial_frame, text="Port:", font=("Helvetica",12),
         bg="black", fg="white").pack(side=tk.LEFT, padx=(10,5))
port_entry = tk.Entry(serial_frame, font=("Helvetica",12))
port_entry.insert(0, "COM5"); port_entry.pack(side=tk.LEFT)
tk.Label(serial_frame, text="Baud Rate:", font=("Helvetica",12),
         bg="black", fg="white").pack(side=tk.LEFT, padx=(20,5))
baud_entry = tk.Entry(serial_frame, font=("Helvetica",12))
baud_entry.insert(0, "9600"); baud_entry.pack(side=tk.LEFT)
tk.Button(serial_frame, text="Connect", font=("Helvetica",12),
          command=connect_serial).pack(side=tk.LEFT, padx=(20,5))

# LEDs
led_canvas = tk.Canvas(tab1, width=170, height=35,
                       bg="white", highlightthickness=0)
led_canvas.pack()
led_radius, yc = 10, 20
positions = {"W":20,"N":60,"S":100,"E":140}
led_tay = led_canvas.create_oval(positions["W"]-led_radius, yc-led_radius,
                                 positions["W"]+led_radius, yc+led_radius,
                                 fill="gray")
led_canvas.create_text(positions["W"], yc, text="W", fill="white")
led_bac = led_canvas.create_oval(positions["N"]-led_radius, yc-led_radius,
                                 positions["N"]+led_radius, yc+led_radius,
                                 fill="gray")
led_canvas.create_text(positions["N"], yc, text="N", fill="white")
led_nam = led_canvas.create_oval(positions["S"]-led_radius, yc-led_radius,
                                 positions["S"]+led_radius, yc+led_radius,
                                 fill="gray")
led_canvas.create_text(positions["S"], yc, text="S", fill="white")
led_dong = led_canvas.create_oval(positions["E"]-led_radius, yc-led_radius,
                                  positions["E"]+led_radius, yc+led_radius,
                                  fill="gray")
led_canvas.create_text(positions["E"], yc, text="E", fill="white")
blink_leds()

# Status label
status_label = tk.Label(tab1, text="", font=("Helvetica",16,"bold"),
                        bg="black", fg="white")
status_label.pack(pady=5)

# Lat/Lon/Height
lat_lon_frame = tk.Frame(tab1, bg="black")
lat_lon_frame.pack(pady=5)
tk.Label(lat_lon_frame, text="Latitude:", font=("Helvetica",12,"bold"),
         bg="black", fg="white").pack(side=tk.LEFT, padx=(10,5))
lat_value = tk.Label(lat_lon_frame, text="N/A", font=("Helvetica",12),
                     bg="black", fg="white"); lat_value.pack(side=tk.LEFT)
tk.Label(lat_lon_frame, text="  Longitude:", font=("Helvetica",12,"bold"),
         bg="black", fg="white").pack(side=tk.LEFT, padx=(20,5))
lon_value = tk.Label(lat_lon_frame, text="N/A", font=("Helvetica",12),
                     bg="black", fg="white"); lon_value.pack(side=tk.LEFT)
tk.Label(lat_lon_frame, text="  Height:", font=("Helvetica",12,"bold"),
         bg="black", fg="white").pack(side=tk.LEFT, padx=(20,5))
height_value = tk.Label(lat_lon_frame, text="N/A", font=("Helvetica",12),
                        bg="black", fg="white"); height_value.pack(side=tk.LEFT)

# Matplotlib figure in Tab1
fig, axs = plt.subplots(2,3, figsize=(14,8))
fig.patch.set_facecolor('black')
ax1,ax2,ax3,ax4,ax5,ax6 = axs[0,0],axs[0,1],axs[0,2],axs[1,0],axs[1,1],axs[1,2]
for ax in [ax1,ax2,ax3,ax4,ax5]:
    ax.set_facecolor('black'); set_axis_color(ax)
ax1.set_xlim(0,100); ax1.set_ylim(-180,180)
ax2.set_xlim(0,100); ax2.set_ylim(-2,2)
ax3.set_xlim(0,100); ax3.set_ylim(0,100)
ax4.set_xlim(0,100); ax4.set_ylim(0,1500)
ax5.set_xlim(0,100); ax5.set_ylim(0,100)

# Plot lines and text
gyro_x_vals,gyro_y_vals,gyro_z_vals = [],[],[]
acc_x_vals,acc_y_vals,acc_z_vals = [],[],[]
temp_vals,pressure_vals,height_vals = [],[],[]
max_points = 100

line_gyro_x, = ax1.plot([],[], label="GyroX", color="red")
line_gyro_y, = ax1.plot([],[], label="GyroY", color="green")
line_gyro_z, = ax1.plot([],[], label="GyroZ", color="blue")
ax1.legend(facecolor='black', edgecolor='white', labelcolor='white')
line_acc_x, = ax2.plot([],[], label="AccX", color="red")
line_acc_y, = ax2.plot([],[], label="AccY", color="green")
line_acc_z, = ax2.plot([],[], label="AccZ", color="blue")
ax2.legend(facecolor='black', edgecolor='white', labelcolor='white')
line_temp, = ax3.plot([],[], label="Temp", color="orange")
ax3.legend(facecolor='black', edgecolor='white', labelcolor='white')
line_pressure, = ax4.plot([],[], label="Pressure", color="purple")
ax4.legend(facecolor='black', edgecolor='white', labelcolor='white')
line_height, = ax5.plot([],[], label="Height", color="brown")
ax5.legend(facecolor='black', edgecolor='white', labelcolor='white')

text_gyro_x = ax1.text(0.05,0.9,'',transform=ax1.transAxes, color="red")
text_gyro_y = ax1.text(0.05,0.85,'',transform=ax1.transAxes, color="green")
text_gyro_z = ax1.text(0.05,0.8,'',transform=ax1.transAxes, color="blue")
text_acc_x  = ax2.text(0.05,0.9,'',transform=ax2.transAxes, color="red")
text_acc_y  = ax2.text(0.05,0.85,'',transform=ax2.transAxes, color="green")
text_acc_z  = ax2.text(0.05,0.8,'',transform=ax2.transAxes, color="blue")
text_temp   = ax3.text(0.05,0.9,'',transform=ax3.transAxes, color="orange")
text_pressure= ax4.text(0.05,0.9,'',transform=ax4.transAxes, color="purple")
text_height = ax5.text(0.05,0.9,'',transform=ax5.transAxes, color="brown")

# Logo in ax6
try:
    img = Image.open("logo.png").resize((300,300))
    ax6.imshow(np.array(img))
except Exception as e:
    print("Không mở logo:", e)
ax6.axis('off')

plot_canvas = FigureCanvasTkAgg(fig, master=tab1)
plot_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=1)

# start update loop
root.after(100, update_plots)

# --- Build Game Tab ---
game_canvas = tk.Canvas(tab2, width=WIDTH2, height=HEIGHT2)
game_canvas.pack(expand=1)

render_game()

# === Run ===
root.mainloop()
