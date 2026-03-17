import os
import queue
import threading
import tkinter as tk

from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from base_workflow import Liquid_Dispenser, start_workflow_logging

# --- Config ---
VIRTUAL    = False
WELL       = 6 
HCL_VIAL   = 0   # vial_rack_12 index
NAOH_VIAL  = 1   # vial_rack_12 index
WATER_VIAL = 2   # vial_rack_12 index
NUM_REPEATS = 10
COLOR_SPACE = "RGB"   # "RGB", "LAB", "HSV"
OUTPUT_DIR  = "well_plate_photos"  # matches Liquid_Dispenser default

THUMB_W, THUMB_H = 100, 100
TOTAL_STEPS = NUM_REPEATS + 1

CHANNEL_STYLES = {
    "RGB": {"R": "tomato",   "G": "limegreen",  "B": "dodgerblue"},
    "LAB": {"L": "white",    "A": "magenta",    "B": "goldenrod"},
    "HSV": {"H": "orchid",   "S": "orange",     "V": "skyblue"},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def crop_path_for(step):
    suffix = f"step_{step}"
    return os.path.join(OUTPUT_DIR, "center_crops", f"center_crop_well_plate{suffix}.jpg")


# ---------------------------------------------------------------------------
# Workflow (runs in background thread)
# ---------------------------------------------------------------------------

def run_workflow(q):
    logger   = start_workflow_logging("titration", virtual=VIRTUAL)
    dispenser = Liquid_Dispenser(cnc_comport="COM5", actuator_comport="COM3", virtual=VIRTUAL)
    dispenser.cnc_machine.home()

    # Startup tip conditioning in water x5
    dispenser.rinse_needle("vial_rack_12", WATER_VIAL, num_mixes=5)

    # Step 0 — HCl baseline
    dispenser.dispense_between("vial_rack_12", HCL_VIAL, "well_plate", WELL, transfer_vol=0.8)
    color = dispenser.get_image_color("well_plate_camera", WELL, "step_0", color_space=COLOR_SPACE)
    logger.info(f"Step 0 (HCl baseline): {color}")
    q.put((0, color, crop_path_for(0)))
    dispenser.rinse_needle("vial_rack_12", WATER_VIAL)

    # Titration loop
    for i in range(1, NUM_REPEATS + 1):
        dispenser.dispense_between("vial_rack_12", NAOH_VIAL, "well_plate", WELL, transfer_vol=0.1, mixing_vol=0.45)
        color = dispenser.get_image_color("well_plate_camera", WELL, f"step_{i}", color_space=COLOR_SPACE)
        logger.info(f"Step {i} (after {i * 100} uL NaOH): {color}")
        q.put((i, color, crop_path_for(i)))
        dispenser.rinse_needle("vial_rack_12", WATER_VIAL)

    q.put(None)  # sentinel — workflow done


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

class TitrationGUI:
    def __init__(self, root, q):
        self.root      = root
        self.q         = q
        self.channels  = list(CHANNEL_STYLES[COLOR_SPACE].keys())
        self.ch_colors = CHANNEL_STYLES[COLOR_SPACE]
        self.step_data = {}
        self.photo_refs = []  # prevent GC
        self.thumb_photos = [None] * TOTAL_STEPS  # stable per-step references

        root.title("Titration Demo")
        root.configure(bg="#1e1e1e")

        # --- Image strip ---
        img_frame = tk.Frame(root, bg="#1e1e1e")
        img_frame.pack(fill="x", padx=10, pady=(10, 4))

        self.thumb_labels = []
        placeholder_img = Image.new("RGB", (THUMB_W, THUMB_H), (68, 68, 68))

        for i in range(TOTAL_STEPS):
            ph_photo = ImageTk.PhotoImage(placeholder_img)
            self.photo_refs.append(ph_photo)
            self.thumb_photos[i] = ph_photo

            col = tk.Frame(img_frame, bg="#1e1e1e")
            col.pack(side="left", padx=3)

            lbl = tk.Label(col, image=ph_photo, bg="#1e1e1e", bd=0)
            lbl.image = ph_photo
            lbl.pack()
            tk.Label(col, text=f"step {i}", bg="#1e1e1e", fg="#888888", font=("Arial", 8)).pack()
            self.thumb_labels.append(lbl)

        # --- Chart ---
        fig_w = max(8.0, TOTAL_STEPS * 0.85)
        fig = Figure(figsize=(fig_w, 3.2), dpi=100, facecolor="#2b2b2b")
        self.ax = fig.add_subplot(111, facecolor="#2b2b2b")
        self.ax.set_xlabel("Step", color="#cccccc", fontsize=9)
        self.ax.set_ylabel(COLOR_SPACE, color="#cccccc", fontsize=9)
        self.ax.tick_params(colors="#cccccc", labelsize=8)
        for sp in self.ax.spines.values():
            sp.set_edgecolor("#555555")
        self.ax.set_xlim(-0.5, TOTAL_STEPS - 0.5)
        self.ax.set_xticks(range(TOTAL_STEPS))
        fig.tight_layout(pad=1.5)

        self.lines = {}
        for ch in self.channels:
            line, = self.ax.plot([], [], color=self.ch_colors[ch], marker="o",
                                 label=ch, linewidth=2, markersize=5)
            self.lines[ch] = line
        self.ax.legend(facecolor="#3a3a3a", labelcolor="white", framealpha=0.9, fontsize=8)

        canvas = FigureCanvasTkAgg(fig, master=root)
        canvas.get_tk_widget().pack(fill="x", padx=10, pady=(4, 10))
        self.fig_canvas = canvas

        root.after(100, self._poll)

    def _poll(self):
        try:
            while True:
                item = self.q.get_nowait()
                if item is None:
                    return  # done
                self._update(*item)
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def _update(self, step, color, crop_path):
        self.step_data[step] = color

        # Thumbnail: real crop image, or RGB swatch in virtual mode
        loaded = False
        if crop_path and os.path.exists(crop_path):
            try:
                with Image.open(crop_path) as opened_img:
                    img = opened_img.copy().resize((THUMB_W, THUMB_H), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.photo_refs.append(photo)
                self.thumb_photos[step] = photo
                self.thumb_labels[step].config(image=photo)
                self.thumb_labels[step].image = photo
                loaded = True
            except Exception:
                pass

        if not loaded and color and COLOR_SPACE == "RGB":
            r, g, b = (max(0, min(255, int(color.get(k, 128)))) for k in "RGB")
            swatch = Image.new("RGB", (THUMB_W, THUMB_H), (r, g, b))
            photo  = ImageTk.PhotoImage(swatch)
            self.photo_refs.append(photo)
            self.thumb_photos[step] = photo
            self.thumb_labels[step].config(image=photo)
            self.thumb_labels[step].image = photo

        # Chart update
        xs = sorted(self.step_data)
        for ch in self.channels:
            ys = [self.step_data[s].get(ch, 0) for s in xs]
            self.lines[ch].set_data(xs, ys)
        self.ax.relim()
        self.ax.autoscale_view(scalex=False)
        self.fig_canvas.draw()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    q = queue.Queue()
    root = tk.Tk()
    TitrationGUI(root, q)
    threading.Thread(target=run_workflow, args=(q,), daemon=True).start()
    root.mainloop()


if __name__ == "__main__":
    main()
