import statistics
import math
import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext

from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except Exception:
    DND_FILES = None
    TkinterDnD = None

from analyze_color_matching_results import (
    _compute_input_distances,
    _find_latest_results_csv,
    _load_experiment_rows,
    _resolve_csv_path,
    _summarize_consistency,
)


class AnalysisGUI:
    def __init__(self, root, dnd_available=False):
        self.root = root
        self.dnd_available = dnd_available
        self.root.title("Color Matching Results Analyzer")
        self.root.geometry("1200x820")

        self.path_var = tk.StringVar(value="")
        self.target_r_var = tk.StringVar(value="0.40")
        self.target_y_var = tk.StringVar(value="0.55")
        self.target_b_var = tk.StringVar(value="0.05")
        self.input_close_threshold_var = tk.StringVar(value="0.10")
        self.input_step_size_var = tk.StringVar(value="0.05")
        self.top_k_var = tk.StringVar(value="5")
        self.output_plot_scale_var = tk.StringVar(value="minmax")

        self.compare_paths = []
        self.image_refs = []
        self.prefs_path = Path(".color_matching_gui_prefs.json")

        self._load_prefs()

        self._build_ui()
        self._auto_fill_latest_path()
        self._refresh_compare_listbox()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        container = tk.Frame(self.root, padx=10, pady=10)
        container.pack(fill=tk.BOTH, expand=True)

        title = tk.Label(container, text="Analyze Color Matching Run", font=("Segoe UI", 14, "bold"))
        title.pack(anchor="w", pady=(0, 10))

        if self.dnd_available:
            dnd_note = "Drag-and-drop enabled: drop a CSV/folder into the path box or compare list"
        else:
            dnd_note = "Drag-and-drop unavailable (install tkinterdnd2 to enable); browse buttons still work"
        tk.Label(container, text=dnd_note, fg="#666666").pack(anchor="w", pady=(0, 8))

        path_frame = tk.LabelFrame(container, text="Single Run: Results CSV / Run Folder", padx=8, pady=8)
        path_frame.pack(fill=tk.X, pady=(0, 10))

        self.path_entry = tk.Entry(path_frame, textvariable=self.path_var)
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        tk.Button(path_frame, text="Browse File", width=12, command=self._browse_file).grid(row=0, column=1, padx=(0, 6))
        tk.Button(path_frame, text="Browse Folder", width=12, command=self._browse_folder).grid(row=0, column=2, padx=(0, 6))
        tk.Button(path_frame, text="Use Latest", width=12, command=self._auto_fill_latest_path).grid(row=0, column=3)
        path_frame.columnconfigure(0, weight=1)

        targets = tk.LabelFrame(container, text="Target Recipe (R, Y, B)", padx=8, pady=8)
        targets.pack(fill=tk.X, pady=(0, 10))

        tk.Label(targets, text="R").grid(row=0, column=0, sticky="w")
        tk.Entry(targets, textvariable=self.target_r_var, width=10).grid(row=0, column=1, padx=(4, 16))
        tk.Label(targets, text="Y").grid(row=0, column=2, sticky="w")
        tk.Entry(targets, textvariable=self.target_y_var, width=10).grid(row=0, column=3, padx=(4, 16))
        tk.Label(targets, text="B").grid(row=0, column=4, sticky="w")
        tk.Entry(targets, textvariable=self.target_b_var, width=10).grid(row=0, column=5, padx=(4, 16))

        close_frame = tk.LabelFrame(container, text="Close-Sample Settings", padx=8, pady=8)
        close_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(close_frame, text="Input close threshold (L2)").grid(row=0, column=0, sticky="w", pady=(6, 0))
        tk.Entry(close_frame, textvariable=self.input_close_threshold_var, width=10).grid(row=0, column=1, sticky="w", padx=(4, 16), pady=(6, 0))

        tk.Label(close_frame, text="Input step size").grid(row=0, column=2, sticky="w", pady=(6, 0))
        tk.Entry(close_frame, textvariable=self.input_step_size_var, width=10).grid(row=0, column=3, sticky="w", padx=(4, 0), pady=(6, 0))

        tk.Label(close_frame, text="Top K").grid(row=1, column=0, sticky="w", pady=(6, 0))
        tk.Entry(close_frame, textvariable=self.top_k_var, width=10).grid(row=1, column=1, sticky="w", padx=(4, 16), pady=(6, 0))

        tk.Label(close_frame, text="Output scale (plots + summary)").grid(row=1, column=2, sticky="w", pady=(6, 0))
        tk.OptionMenu(close_frame, self.output_plot_scale_var, "minmax", "raw", "zscore").grid(row=1, column=3, sticky="w", pady=(6, 0))

        compare_frame = tk.LabelFrame(container, text="Compare Multiple Run Folders", padx=8, pady=8)
        compare_frame.pack(fill=tk.X, pady=(0, 10))

        self.compare_listbox = tk.Listbox(compare_frame, height=4)
        self.compare_listbox.grid(row=0, column=0, columnspan=4, sticky="ew", padx=(0, 8))

        tk.Button(compare_frame, text="Add Folder", width=12, command=self._add_compare_folder).grid(row=1, column=0, pady=(6, 0), sticky="w")
        tk.Button(compare_frame, text="Remove Selected", width=14, command=self._remove_selected_compare_folder).grid(row=1, column=1, padx=(6, 0), pady=(6, 0), sticky="w")
        tk.Button(compare_frame, text="Clear List", width=10, command=self._clear_compare_folders).grid(row=1, column=2, padx=(6, 0), pady=(6, 0), sticky="w")
        tk.Button(compare_frame, text="Run Comparison", width=13, command=self._run_comparison, bg="#0e639c", fg="white").grid(row=1, column=3, padx=(6, 0), pady=(6, 0), sticky="w")
        compare_frame.columnconfigure(0, weight=1)

        btn_frame = tk.Frame(container)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Button(btn_frame, text="Run Analysis", command=self._run_analysis, bg="#0e639c", fg="white", width=16).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="Clear Output", command=self._clear_output, width=12).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(btn_frame, text="Plot Distances", command=self._plot_distances, width=13).pack(side=tk.LEFT, padx=(8, 0))

        output_visual_frame = tk.LabelFrame(container, text="Visual Preview: Output Closeness (Target + Lowest Output)", padx=6, pady=6)
        output_visual_frame.pack(fill=tk.X, pady=(0, 8))
        self.output_thumb_container = tk.Frame(output_visual_frame)
        self.output_thumb_container.pack(fill=tk.X)

        input_visual_frame = tk.LabelFrame(container, text="Visual Preview: Input Closeness (Target Recipe + Lowest Input Distance)", padx=6, pady=6)
        input_visual_frame.pack(fill=tk.X, pady=(0, 10))
        self.input_thumb_container = tk.Frame(input_visual_frame)
        self.input_thumb_container.pack(fill=tk.X)

        out_frame = tk.LabelFrame(container, text="Report", padx=6, pady=6)
        out_frame.pack(fill=tk.BOTH, expand=True)
        self.output = scrolledtext.ScrolledText(out_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.output.pack(fill=tk.BOTH, expand=True)

        self._setup_drag_and_drop()

    def _setup_drag_and_drop(self):
        if not self.dnd_available or DND_FILES is None:
            return

        self.path_entry.drop_target_register(DND_FILES)
        self.path_entry.dnd_bind("<<Drop>>", self._on_drop_to_path)

        self.compare_listbox.drop_target_register(DND_FILES)
        self.compare_listbox.dnd_bind("<<Drop>>", self._on_drop_to_compare)

    def _split_drop_paths(self, raw_data):
        try:
            parts = self.root.tk.splitlist(raw_data)
        except Exception:
            parts = [raw_data]
        cleaned = [str(Path(part.strip())).strip() for part in parts if str(part).strip()]
        return cleaned

    def _on_drop_to_path(self, event):
        paths = self._split_drop_paths(event.data)
        if not paths:
            return
        self.path_var.set(paths[0])

    def _on_drop_to_compare(self, event):
        paths = self._split_drop_paths(event.data)
        changed = False
        for p in paths:
            candidate = Path(p)
            if candidate.is_file():
                candidate = candidate.parent
            path_text = str(candidate)
            if path_text not in self.compare_paths:
                self.compare_paths.append(path_text)
                self.compare_listbox.insert(tk.END, path_text)
                changed = True
        if changed:
            self._save_prefs()

    def _browse_file(self):
        selected = filedialog.askopenfilename(
            title="Select color_matching_results.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if selected:
            self.path_var.set(selected)

    def _browse_folder(self):
        selected = filedialog.askdirectory(title="Select run folder")
        if selected:
            self.path_var.set(selected)

    def _auto_fill_latest_path(self):
        if self.path_var.get().strip():
            return
        latest = _find_latest_results_csv("output")
        if latest is not None:
            self.path_var.set(str(latest))

    def _refresh_compare_listbox(self):
        if not hasattr(self, "compare_listbox"):
            return
        self.compare_listbox.delete(0, tk.END)
        for path in self.compare_paths:
            self.compare_listbox.insert(tk.END, path)

    def _load_prefs(self):
        if not self.prefs_path.exists():
            return
        try:
            with self.prefs_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            compare_paths = data.get("compare_paths", [])
            if isinstance(compare_paths, list):
                cleaned = []
                for item in compare_paths:
                    p = Path(str(item))
                    if p.exists() and p.is_dir():
                        cleaned.append(str(p))
                self.compare_paths = cleaned
        except Exception:
            self.compare_paths = []

    def _save_prefs(self):
        payload = {
            "compare_paths": self.compare_paths,
        }
        with self.prefs_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def _on_close(self):
        try:
            self._save_prefs()
        finally:
            self.root.destroy()

    def _add_compare_folder(self):
        selected = filedialog.askdirectory(title="Select run folder for comparison")
        if not selected:
            return
        path = str(Path(selected))
        if path in self.compare_paths:
            return
        self.compare_paths.append(path)
        self.compare_listbox.insert(tk.END, path)
        self._save_prefs()

    def _remove_selected_compare_folder(self):
        selected_indices = list(self.compare_listbox.curselection())
        if not selected_indices:
            return
        for index in reversed(selected_indices):
            del self.compare_paths[index]
            self.compare_listbox.delete(index)
        self._save_prefs()

    def _clear_compare_folders(self):
        self.compare_paths.clear()
        self.compare_listbox.delete(0, tk.END)
        self._save_prefs()

    def _clear_output(self):
        self.output.delete("1.0", tk.END)

    def _read_float(self, value, field_name):
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(f"Invalid number for {field_name}: '{value}'") from exc

    def _read_int(self, value, field_name):
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ValueError(f"Invalid integer for {field_name}: '{value}'") from exc
        if parsed < 1:
            raise ValueError(f"{field_name} must be >= 1")
        return parsed

    def _transform_output_values(self, values, mode):
        output_mode = str(mode).strip().lower()
        if output_mode == "raw":
            return list(values), "output(raw)"

        if output_mode == "zscore":
            mean_v = statistics.mean(values)
            std_v = statistics.pstdev(values) if len(values) > 1 else 0.0
            if std_v == 0:
                return [0.0 for _ in values], "output(zscore)"
            return [((v - mean_v) / std_v) for v in values], "output(zscore)"

        min_v = min(values)
        max_v = max(values)
        span = max_v - min_v
        if span == 0:
            return [0.0 for _ in values], "output(minmax)"
        return [((v - min_v) / span) for v in values], "output(minmax)"

    def _collect_runs_for_plot(self, target_r, target_y, target_b):
        runs = []
        if self.compare_paths:
            for folder in self.compare_paths:
                csv_path = _resolve_csv_path(folder)
                summary = self._analyze_csv(csv_path, target_r, target_y, target_b)
                runs.append(summary)
        else:
            path_text = self.path_var.get().strip()
            if path_text:
                csv_path = _resolve_csv_path(path_text)
            else:
                csv_path = _find_latest_results_csv("output")
                if csv_path is None:
                    raise FileNotFoundError("No color_matching_results.csv found under output/")
            summary = self._analyze_csv(csv_path, target_r, target_y, target_b)
            runs.append(summary)
        return runs

    def _plot_distances(self):
        try:
            target_r = self._read_float(self.target_r_var.get().strip(), "Target R")
            target_y = self._read_float(self.target_y_var.get().strip(), "Target Y")
            target_b = self._read_float(self.target_b_var.get().strip(), "Target B")

            runs = self._collect_runs_for_plot(target_r, target_y, target_b)
            if not runs:
                messagebox.showinfo("Plot", "No runs available to plot.")
                return

            plot_window = tk.Toplevel(self.root)
            plot_window.title("Distance vs Well")
            plot_window.geometry("1100x700")

            figure = Figure(figsize=(11, 7), dpi=100)
            ax_out = figure.add_subplot(211)
            ax_in = figure.add_subplot(212)

            out_scale_mode = self.output_plot_scale_var.get().strip().lower()

            output_ylabel = "Output distance"

            for summary in runs:
                run_name = summary["csv_path"].parent.name
                rows_sorted = sorted(summary["rows"], key=lambda row: row["well"])
                wells = [row["well"] for row in rows_sorted]
                out_vals = [row["output"] for row in rows_sorted]
                in_vals = [row["input_l2"] for row in rows_sorted]
                out_vals_plot, output_ylabel = self._transform_output_values(out_vals, out_scale_mode)

                ax_out.plot(wells, out_vals_plot, marker="o", linewidth=1.5, label=run_name)
                ax_in.plot(wells, in_vals, marker="o", linewidth=1.5, label=run_name)

            if out_scale_mode == "raw":
                ax_out.set_title("Output-space distance vs Well")
            elif out_scale_mode == "zscore":
                ax_out.set_title("Output-space distance vs Well (z-score by run)")
            else:
                ax_out.set_title("Output-space distance vs Well (min-max normalized by run)")
            ax_out.set_xlabel("Well")
            ax_out.set_ylabel(output_ylabel)
            ax_out.grid(True, alpha=0.3)
            ax_out.legend(loc="best", fontsize=8)

            ax_in.set_title("Input-space distance vs Well")
            ax_in.set_xlabel("Well")
            ax_in.set_ylabel("Input distance (L2)")
            ax_in.grid(True, alpha=0.3)
            ax_in.legend(loc="best", fontsize=8)

            figure.tight_layout(pad=2.0)

            canvas = FigureCanvasTkAgg(figure, master=plot_window)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        except Exception as exc:
            messagebox.showerror("Plot Error", str(exc))

    def _analyze_csv(self, csv_path, target_r, target_y, target_b):
        rows, _ = _load_experiment_rows(csv_path)
        _compute_input_distances(rows, target_r, target_y, target_b)

        outputs = [row["output"] for row in rows]
        input_l2_values = [row["input_l2"] for row in rows]
        out_scale_mode = self.output_plot_scale_var.get().strip().lower()
        output_scaled, output_scaled_label = self._transform_output_values(outputs, out_scale_mode)
        out_min = min(outputs)
        out_max = max(outputs)
        out_mean = statistics.mean(outputs)
        out_median = statistics.median(outputs)
        out_std = statistics.pstdev(outputs) if len(outputs) > 1 else 0.0
        out_scaled_best = min(output_scaled)
        out_scaled_mean = statistics.mean(output_scaled)
        out_scaled_median = statistics.median(output_scaled)
        out_scaled_std = statistics.pstdev(output_scaled) if len(output_scaled) > 1 else 0.0
        input_best = min(input_l2_values)
        input_mean = statistics.mean(input_l2_values)
        best_output_row = min(rows, key=lambda row: row["output"])
        closest_input_row = min(rows, key=lambda row: row["input_l2"])

        step_size = self._read_float(self.input_step_size_var.get().strip(), "Input step size")
        if step_size <= 0:
            raise ValueError("Input step size must be > 0")

        close_threshold = self._read_float(self.input_close_threshold_var.get().strip(), "Input close threshold (L2)")
        threshold_source = "shared_input_l2"

        for row in rows:
            delta_l1 = abs(row["delta_R"]) + abs(row["delta_Y"]) + abs(row["delta_B"])
            row["move_count"] = delta_l1 / (2.0 * step_size)

        close_rows = [row for row in rows if row["input_l2"] <= close_threshold]
        consistency = _summarize_consistency(close_rows, rows)
        close_rows_1move = [row for row in rows if row["move_count"] <= 1.0 + 1e-9]
        close_rows_2move = [row for row in rows if row["move_count"] <= 2.0 + 1e-9]
        move_count_min = min(row["move_count"] for row in rows)
        move_count_mean = statistics.mean(row["move_count"] for row in rows)

        return {
            "csv_path": Path(csv_path),
            "rows": rows,
            "best_output_row": best_output_row,
            "closest_input_row": closest_input_row,
            "out_min": out_min,
            "out_max": out_max,
            "out_mean": out_mean,
            "out_median": out_median,
            "out_std": out_std,
            "out_scaled_best": out_scaled_best,
            "out_scaled_mean": out_scaled_mean,
            "out_scaled_median": out_scaled_median,
            "out_scaled_std": out_scaled_std,
            "out_scaled_label": output_scaled_label,
            "input_best": input_best,
            "input_mean": input_mean,
            "close_threshold": close_threshold,
            "threshold_source": threshold_source,
            "consistency": consistency,
            "step_size": step_size,
            "close_count_1move": len(close_rows_1move),
            "close_count_2move": len(close_rows_2move),
            "min_move_count": move_count_min,
            "mean_move_count": move_count_mean,
        }

    def _find_target_image(self, run_dir):
        crop_dir = Path(run_dir) / "center_crops"
        if not crop_dir.exists():
            return None
        matches = sorted(crop_dir.glob("*target_sample*.*"))
        return matches[0] if matches else None

    def _find_well_image(self, run_dir, well):
        crop_dir = Path(run_dir) / "center_crops"
        if not crop_dir.exists():
            return None
        matches = sorted(crop_dir.glob(f"*experiment_{well}_*.*"))
        return matches[0] if matches else None

    def _draw_visuals(self, container, run_dir, ranked_rows, metric_key, max_items, title_prefix=""):
        for widget in container.winfo_children():
            widget.destroy()

        def add_thumb(col_idx, title, img_path):
            panel = tk.Frame(container, padx=4, pady=4)
            panel.grid(row=0, column=col_idx, sticky="n")
            tk.Label(panel, text=title, font=("Segoe UI", 9, "bold")).pack()

            if img_path is None or not Path(img_path).exists():
                tk.Label(panel, text="(image not found)", width=24, height=10).pack()
                return

            image = Image.open(img_path)
            image.thumbnail((210, 210))
            photo = ImageTk.PhotoImage(image)
            self.image_refs.append(photo)
            tk.Label(panel, image=photo).pack()
            tk.Label(panel, text=Path(img_path).name, wraplength=220, justify="center").pack()

        add_thumb(0, "Target sample", self._find_target_image(run_dir))
        for idx, row in enumerate(ranked_rows[:max_items], start=1):
            if title_prefix:
                title = f"{title_prefix} | well {row['well']} ({metric_key}={row[metric_key]:.3f})"
            else:
                title = f"Top {idx}: well {row['well']} ({metric_key}={row[metric_key]:.3f})"
            add_thumb(idx, title, self._find_well_image(run_dir, row["well"]))

    def _render_single_report(self, summary, target_r, target_y, target_b, top_k):
        lines = []
        lines.append(f"CSV: {summary['csv_path']}")
        lines.append(f"Target recipe (R,Y,B): ({target_r:.3f}, {target_y:.3f}, {target_b:.3f})")
        lines.append("")
        lines.append("=== Output-space closeness (to 0) ===")
        lines.append(f"best_output: {summary['out_min']:.6f}")
        lines.append(f"max_output: {summary['out_max']:.6f}")
        lines.append(f"mean_output: {summary['out_mean']:.6f}")
        lines.append(f"median_output: {summary['out_median']:.6f}")
        lines.append(f"std_output: {summary['out_std']:.6f}")
        lines.append(f"best_{summary['out_scaled_label']}: {summary['out_scaled_best']:.6f}")
        lines.append(f"mean_{summary['out_scaled_label']}: {summary['out_scaled_mean']:.6f}")
        lines.append(f"median_{summary['out_scaled_label']}: {summary['out_scaled_median']:.6f}")
        lines.append(f"std_{summary['out_scaled_label']}: {summary['out_scaled_std']:.6f}")
        lines.append("")
        lines.append("=== Input-space closeness (to target recipe) ===")

        best_output_row = summary["best_output_row"]
        closest_input_row = summary["closest_input_row"]
        lines.append(
            f"Best output well: well={best_output_row['well']}, output={best_output_row['output']:.6f}, "
            f"recipe(R,Y,B)=({best_output_row['R']:.3f}, {best_output_row['Y']:.3f}, {best_output_row['B']:.3f}), "
            f"input_l1={best_output_row['input_l1']:.3f}, input_l2={best_output_row['input_l2']:.3f}"
        )
        lines.append(
            f"Closest recipe well: well={closest_input_row['well']}, output={closest_input_row['output']:.6f}, "
            f"recipe(R,Y,B)=({closest_input_row['R']:.3f}, {closest_input_row['Y']:.3f}, {closest_input_row['B']:.3f}), "
            f"input_l1={closest_input_row['input_l1']:.3f}, input_l2={closest_input_row['input_l2']:.3f}"
        )
        lines.append(
            "Best output deltas from target: "
            f"dR={best_output_row['delta_R']:+.3f}, dY={best_output_row['delta_Y']:+.3f}, dB={best_output_row['delta_B']:+.3f}"
        )
        lines.append("")
        lines.append("=== Close-sample consistency ===")
        lines.append(f"close_threshold_input_l2: {summary['close_threshold']:.6f} ({summary['threshold_source']})")
        lines.append(
            f"close_samples: {summary['consistency']['close_count']}/{summary['consistency']['total_count']} "
            f"({100.0 * summary['consistency']['close_ratio']:.1f}%)"
        )
        lines.append(
            f"number_close_<=1move: {summary['close_count_1move']}/{summary['consistency']['total_count']} "
            f"(step={summary['step_size']:.3f})"
        )
        lines.append(
            f"number_close_<=2moves: {summary['close_count_2move']}/{summary['consistency']['total_count']} "
            f"(step={summary['step_size']:.3f})"
        )
        lines.append(f"min_move_count: {summary['min_move_count']:.3f}")
        lines.append(f"mean_move_count: {summary['mean_move_count']:.3f}")
        lines.append(f"close_wells: {summary['consistency']['close_wells']}")
        lines.append(f"longest_consecutive_close_streak: {summary['consistency']['longest_streak']}")
        lines.append(
            f"close_distribution: first_half={summary['consistency']['close_first_half']}, "
            f"second_half={summary['consistency']['close_second_half']}"
        )
        lines.append(f"consistency_assessment: {summary['consistency']['label']}")
        lines.append("")
        lines.append("=== Top output wells ===")
        for index, row in enumerate(sorted(summary["rows"], key=lambda r: r["output"])[:top_k], start=1):
            lines.append(
                f"{index:>2}. well={row['well']:>2}, output={row['output']:.6f}, "
                f"recipe=({row['R']:.3f}, {row['Y']:.3f}, {row['B']:.3f}), input_l2={row['input_l2']:.3f}"
            )

        lines.append("")
        lines.append("=== Top input-closeness wells (Top 5) ===")
        for index, row in enumerate(sorted(summary["rows"], key=lambda r: r["input_l2"])[:5], start=1):
            lines.append(
                f"{index:>2}. well={row['well']:>2}, input_l2={row['input_l2']:.6f}, "
                f"recipe=({row['R']:.3f}, {row['Y']:.3f}, {row['B']:.3f}), output={row['output']:.6f}"
            )
        return "\n".join(lines)

    def _run_analysis(self):
        try:
            path_text = self.path_var.get().strip()
            if path_text:
                csv_path = _resolve_csv_path(path_text)
            else:
                csv_path = _find_latest_results_csv("output")
                if csv_path is None:
                    raise FileNotFoundError("No color_matching_results.csv found under output/")

            target_r = self._read_float(self.target_r_var.get().strip(), "Target R")
            target_y = self._read_float(self.target_y_var.get().strip(), "Target Y")
            target_b = self._read_float(self.target_b_var.get().strip(), "Target B")
            top_k = self._read_int(self.top_k_var.get().strip(), "Top K")

            summary = self._analyze_csv(csv_path, target_r, target_y, target_b)
            report = self._render_single_report(summary, target_r, target_y, target_b, top_k)
            self.output.delete("1.0", tk.END)
            self.output.insert(tk.END, report)

            top_output_rows = sorted(summary["rows"], key=lambda r: r["output"])[:3]
            top_input_rows = sorted(summary["rows"], key=lambda r: r["input_l2"])[:5]
            run_dir = summary["csv_path"].parent
            self.image_refs = []
            self._draw_visuals(self.output_thumb_container, run_dir, top_output_rows, "output", 3)
            self._draw_visuals(self.input_thumb_container, run_dir, top_input_rows, "input_l2", 5)

        except Exception as exc:
            messagebox.showerror("Analysis Error", str(exc))

    def _run_comparison(self):
        try:
            if not self.compare_paths:
                messagebox.showinfo("Comparison", "Add at least one run folder to compare.")
                return

            target_r = self._read_float(self.target_r_var.get().strip(), "Target R")
            target_y = self._read_float(self.target_y_var.get().strip(), "Target Y")
            target_b = self._read_float(self.target_b_var.get().strip(), "Target B")

            summaries = []
            for folder in self.compare_paths:
                csv_path = _resolve_csv_path(folder)
                summary = self._analyze_csv(csv_path, target_r, target_y, target_b)
                summaries.append(summary)

            summaries.sort(
                key=lambda s: (
                    -s["close_count_1move"],
                    -s["close_count_2move"],
                    -s["consistency"]["close_ratio"],
                    -s["consistency"]["close_count"],
                    s["mean_move_count"],
                )
            )

            lines = []
            lines.append("=== Multi-Run Comparison ===")
            lines.append("Ranking prioritizes finding low-move recipes: #<=1move, then #<=2moves, then close ratio/count, then mean moves.")
            lines.append("Close is defined in INPUT space: a well is close if input_l2 <= shared input threshold.")
            lines.append("")
            lines.append("Metric definitions:")
            lines.append("- mean_out_scaled: average output after selected scaling mode (lower is better).")
            lines.append("- best_in: smallest input_l2 to target recipe across wells (lower is better).")
            lines.append("- mean_in: average input_l2 across wells in that run (lower is better).")
            lines.append("- move_count: (|ΔR|+|ΔY|+|ΔB|) / (2*step_size); this is exact grid moves and includes distances like 0.12247 as <=2 moves.")
            lines.append("- close_samples: count of wells with input_l2 <= input_close_threshold.")
            lines.append(f"- output scaling mode: {self.output_plot_scale_var.get().strip().lower()}.")
            lines.append("")
            header = (
                f"{'Rank':<5} {'Run':<22} {'Close':<10} {'Close%':<7} {'#<=1Mv':<8} {'#<=2Mv':<8} "
                f"{'MinMv':<7} {'MeanMv':<8} {'BestOutS':<10} {'MeanOutS':<10} {'BestIn':<9} {'MeanIn':<9} {'Consistency':<20}"
            )
            lines.append(header)
            lines.append("-" * len(header))

            for idx, s in enumerate(summaries, start=1):
                run_name = s["csv_path"].parent.name
                close = f"{s['consistency']['close_count']}/{s['consistency']['total_count']}"
                close_pct = f"{100.0 * s['consistency']['close_ratio']:.1f}%"
                one_move = f"{s['close_count_1move']}/{s['consistency']['total_count']}"
                two_move = f"{s['close_count_2move']}/{s['consistency']['total_count']}"
                lines.append(
                    f"{idx:<5} {run_name:<22.22} {close:<10} {close_pct:<7} {one_move:<8} {two_move:<8} "
                    f"{s['min_move_count']:<7.3f} {s['mean_move_count']:<8.3f} {s['out_scaled_best']:<10.6f} {s['out_scaled_mean']:<10.6f} {s['input_best']:<9.6f} {s['input_mean']:<9.6f} {s['consistency']['label']:<20}"
                )

            global_best_output = None
            global_best_input = None
            for s in summaries:
                best_out_row = min(s["rows"], key=lambda r: r["output"])
                best_in_row = min(s["rows"], key=lambda r: r["input_l2"])

                if global_best_output is None or best_out_row["output"] < global_best_output["row"]["output"]:
                    global_best_output = {"summary": s, "row": best_out_row}

                if global_best_input is None or best_in_row["input_l2"] < global_best_input["row"]["input_l2"]:
                    global_best_input = {"summary": s, "row": best_in_row}

            winner = summaries[0]
            lines.append("")
            lines.append(f"Best overall by close-sample count/ratio: {winner['csv_path'].parent.name}")
            lines.append(
                f"Winner close_samples: {winner['consistency']['close_count']}/{winner['consistency']['total_count']} "
                f"({100.0 * winner['consistency']['close_ratio']:.1f}%)"
            )
            lines.append(f"Input close threshold used: {winner['close_threshold']:.6f} ({winner['threshold_source']})")
            lines.append(
                f"Move metric uses step={winner['step_size']:.3f}; "
                "1 move = one +step/-step transfer, 2 moves includes patterns like (+2,-2,0) and (+1,+1,-2)."
            )
            lines.append("")
            lines.append("Shared close threshold applies identically to all runs.")
            lines.append("")
            lines.append("Input-closeness ranking (lower best_in is better):")
            input_ranked = sorted(summaries, key=lambda s: s["input_best"])
            for idx, s in enumerate(input_ranked, start=1):
                lines.append(
                    f"{idx}. {s['csv_path'].parent.name}: best_in={s['input_best']:.6f}, mean_in={s['input_mean']:.6f}"
                )
            lines.append("")
            lines.append("Global best wells across all selected folders:")
            lines.append(
                f"- Best output: run={global_best_output['summary']['csv_path'].parent.name}, "
                f"well={global_best_output['row']['well']}, output={global_best_output['row']['output']:.6f}"
            )
            lines.append(
                f"- Best input closeness: run={global_best_input['summary']['csv_path'].parent.name}, "
                f"well={global_best_input['row']['well']}, input_l2={global_best_input['row']['input_l2']:.6f}"
            )

            self.output.delete("1.0", tk.END)
            self.output.insert(tk.END, "\n".join(lines))

            top_output_rows = [global_best_output["row"]]
            top_input_rows = [global_best_input["row"]]
            output_run_dir = global_best_output["summary"]["csv_path"].parent
            input_run_dir = global_best_input["summary"]["csv_path"].parent
            output_run_name = global_best_output["summary"]["csv_path"].parent.name
            input_run_name = global_best_input["summary"]["csv_path"].parent.name
            self.image_refs = []
            self._draw_visuals(
                self.output_thumb_container,
                output_run_dir,
                top_output_rows,
                "output",
                1,
                title_prefix=f"Best output ({output_run_name})",
            )
            self._draw_visuals(
                self.input_thumb_container,
                input_run_dir,
                top_input_rows,
                "input_l2",
                1,
                title_prefix=f"Best input ({input_run_name})",
            )

        except Exception as exc:
            messagebox.showerror("Comparison Error", str(exc))


def main():
    if TkinterDnD is not None:
        root = TkinterDnD.Tk()
        dnd_available = True
    else:
        root = tk.Tk()
        dnd_available = False
    AnalysisGUI(root, dnd_available=dnd_available)
    root.mainloop()


if __name__ == "__main__":
    main()
