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

WELL       = 22
HCL_VIAL   = 0   # vial_rack_12 index
NAOH_VIAL  = 1   # vial_rack_12 index
WATER_VIAL = 2   # vial_rack_12 index
NUM_REPEATS = 10
BLOWOUT_REPEATS_START = 5
COLOR_SPACE = "RGB"   # "RGB", "LAB", "HSV"
OUTPUT_DIR  = "well_plate_photos"  # matches Liquid_Dispenser default

ACID_VOLUME_ML = 0.60
BASE_VOLUME_ML = 0.10
BASE_CONCENTRATION_M_DEFAULT = 0.02

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

    # Startup explicit blowout conditioning in water
    dispenser.condition_needle(
        source_location="vial_rack_12",
        source_index=WATER_VIAL,
        dest_location="vial_rack_12",
        dest_index=WATER_VIAL,
        num_conditions=BLOWOUT_REPEATS_START,
        vol_pipet=0.45,
    )

    # Step 0 — HCl baseline
    dispenser.dispense_between("vial_rack_12", HCL_VIAL, "well_plate", WELL, transfer_vol=ACID_VOLUME_ML)
    color = dispenser.get_image_color("well_plate_camera", WELL, "step_0", color_space=COLOR_SPACE)
    logger.info(f"Step 0 (HCl baseline): {color}")
    q.put((0, color, crop_path_for(0)))
    dispenser.rinse_needle("vial_rack_12", WATER_VIAL)

    # Titration loop
    for i in range(1, NUM_REPEATS + 1):
        dispenser.dispense_between("vial_rack_12", NAOH_VIAL, "well_plate", WELL, transfer_vol=BASE_VOLUME_ML)
        dispenser.rinse_needle("vial_rack_12", WATER_VIAL)
        # mix the well
        dispenser.dispense_between(
            source_location="well_plate",
            source_index=WELL,
            dest_location="well_plate",
            dest_index=WELL,
            transfer_vol=0,
            mixing_vol=0.45,
            num_mixes=8,
        )
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
        self.endpoint_marker = None

        # Endpoint detection config for RGB titration
        self.endpoint_min_db = 5.0
        self.endpoint_min_dr = 10.0
        self.base_conc_var = tk.DoubleVar(value=BASE_CONCENTRATION_M_DEFAULT)

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

        input_row = tk.Frame(root, bg="#1e1e1e")
        input_row.pack(fill="x", padx=10, pady=(0, 4))
        tk.Label(input_row, text="Base concentration (M):", bg="#1e1e1e", fg="#cccccc", font=("Arial", 9)).pack(side="left")
        tk.Entry(input_row, textvariable=self.base_conc_var, width=8).pack(side="left", padx=(6, 0))
        self.endpoint_var = tk.StringVar(value="Endpoint: pending")
        tk.Label(root, textvariable=self.endpoint_var, bg="#1e1e1e", fg="#b5c7ff", font=("Arial", 10, "bold")).pack(pady=(0, 8))

        root.after(100, self._poll)

    def _detect_endpoint_step(self):
        """Detect endpoint as strongest transition with +ΔB and -ΔR."""
        if COLOR_SPACE != "RGB":
            return None, None, None

        xs = sorted(self.step_data)
        if len(xs) < 2:
            return None, None, None

        best_step = None
        best_score = -1.0
        best_db = None
        best_dr = None

        for prev_step, curr_step in zip(xs[:-1], xs[1:]):
            prev = self.step_data[prev_step]
            curr = self.step_data[curr_step]

            db = float(curr.get("B", 0) - prev.get("B", 0))
            dr = float(curr.get("R", 0) - prev.get("R", 0))
            red_drop = -dr

            if db >= self.endpoint_min_db and red_drop >= self.endpoint_min_dr:
                score = db + red_drop
                if score > best_score:
                    best_score = score
                    best_step = curr_step
                    best_db = db
                    best_dr = red_drop

        return best_step, best_db, best_dr

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

        endpoint_step, db, dr = self._detect_endpoint_step()
        if self.endpoint_marker is not None:
            self.endpoint_marker.remove()
            self.endpoint_marker = None

        if endpoint_step is not None:
            self.endpoint_marker = self.ax.axvline(endpoint_step, color="#ffd166", linestyle="--", linewidth=1.8, alpha=0.95)
            self.endpoint_var.set(f"Endpoint detected at step {endpoint_step}  (ΔB={db:.1f}, ΔR=-{dr:.1f})")
            try:
                base_conc_m = float(self.base_conc_var.get())
            except Exception:
                base_conc_m = BASE_CONCENTRATION_M_DEFAULT

            # 1:1 neutralization assumption: C_acid * V_acid = C_base * V_base
            base_vol_ml = endpoint_step * BASE_VOLUME_ML
            acid_conc_m = (base_conc_m * base_vol_ml / ACID_VOLUME_ML) if ACID_VOLUME_ML > 0 else 0.0

            self.endpoint_var.set(
                f"Endpoint step {endpoint_step} (ΔB={db:.1f}, ΔR=-{dr:.1f}) | Estimated acid: {acid_conc_m:.4f} M"
            )
        else:
            self.endpoint_var.set("Endpoint: pending")

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
