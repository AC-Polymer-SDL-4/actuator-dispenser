#!/usr/bin/env python3
"""
Multi-Well Percentage Dispenser GUI

Simple tkinter GUI for configuring and running the multi-well percentage dispenser workflow.
Allows users to specify color percentages for multiple vials via an intuitive grid interface.

Usage:
    python multi_well_percentage_dispenser_gui.py
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import sys
import os
import random

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_workflow import Liquid_Dispenser, start_workflow_logging
import time
import logging


class PercentageDispenseGUI:
    """GUI for multi-well percentage dispenser workflow."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Multi-Well Percentage Dispenser")
        self.root.geometry("700x700")
        
        self.num_vials = tk.IntVar(value=4)
        self.vial_inputs = []
        self.workflow_running = False
        
        # Workflow configuration
        self.virtual_mode = tk.BooleanVar(value=True)
        self.TOTAL_VOLUME_ML = 3.5
        
        # Vial mapping variables (which vial index for each function)
        self.vial_red = tk.IntVar(value=0)
        self.vial_yellow = tk.IntVar(value=1)
        self.vial_blue = tk.IntVar(value=2)
        self.vial_water = tk.IntVar(value=3)
        self.vial_wash = tk.IntVar(value=4)
        self.vial_waste = tk.IntVar(value=5)
        
        self.COLOR_ORDER = ['Water', 'Red', 'Blue', 'Yellow']
        
        self.setup_ui()

    def generate_random_percentages(self):
        """Generate random Water/Red/Blue/Yellow percentages in 5% increments summing to 100."""
        units = 20  # 20 * 5% = 100%
        cut1 = random.randint(0, units)
        cut2 = random.randint(cut1, units)
        cut3 = random.randint(cut2, units)

        parts = [
            cut1,
            cut2 - cut1,
            cut3 - cut2,
            units - cut3,
        ]
        random.shuffle(parts)

        return {
            'water': parts[0] * 5,
            'red': parts[1] * 5,
            'blue': parts[2] * 5,
            'yellow': parts[3] * 5,
        }
    
    def setup_ui(self):
        """Create the GUI layout."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="Multi-Well Percentage Dispenser", 
                               font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=4, pady=10)
        
        # Configuration frame (Virtual mode + Vial mapping)
        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="5")
        config_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=10)
        
        # Virtual mode checkbox
        virtual_check = ttk.Checkbutton(config_frame, text="Virtual Mode (no hardware)", 
                                        variable=self.virtual_mode)
        virtual_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Number of vials selector
        num_label = ttk.Label(config_frame, text="Number of Destination Vials:")
        num_label.grid(row=0, column=2, sticky=tk.W, padx=(20, 5))
        
        num_spinbox = ttk.Spinbox(config_frame, from_=1, to=6, textvariable=self.num_vials,
                                  width=5, command=self.update_vial_inputs)
        num_spinbox.grid(row=0, column=3, sticky=tk.W, padx=5)
        
        # Vial mapping frame
        mapping_frame = ttk.LabelFrame(main_frame, text="Source Vial Mapping (vial_rack_12 indices 0-11)", padding="5")
        mapping_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=5)
        
        # Row 1: Colors
        ttk.Label(mapping_frame, text="Red:").grid(row=0, column=0, sticky=tk.E, padx=2)
        ttk.Spinbox(mapping_frame, from_=0, to=11, textvariable=self.vial_red, width=3).grid(row=0, column=1, padx=2)
        
        ttk.Label(mapping_frame, text="Yellow:").grid(row=0, column=2, sticky=tk.E, padx=(10, 2))
        ttk.Spinbox(mapping_frame, from_=0, to=11, textvariable=self.vial_yellow, width=3).grid(row=0, column=3, padx=2)
        
        ttk.Label(mapping_frame, text="Blue:").grid(row=0, column=4, sticky=tk.E, padx=(10, 2))
        ttk.Spinbox(mapping_frame, from_=0, to=11, textvariable=self.vial_blue, width=3).grid(row=0, column=5, padx=2)
        
        # Row 2: Water, Wash, Waste
        ttk.Label(mapping_frame, text="Water:").grid(row=1, column=0, sticky=tk.E, padx=2)
        ttk.Spinbox(mapping_frame, from_=0, to=11, textvariable=self.vial_water, width=3).grid(row=1, column=1, padx=2)
        
        ttk.Label(mapping_frame, text="Wash:").grid(row=1, column=2, sticky=tk.E, padx=(10, 2))
        ttk.Spinbox(mapping_frame, from_=0, to=11, textvariable=self.vial_wash, width=3).grid(row=1, column=3, padx=2)
        
        ttk.Label(mapping_frame, text="Waste:").grid(row=1, column=4, sticky=tk.E, padx=(10, 2))
        ttk.Spinbox(mapping_frame, from_=0, to=11, textvariable=self.vial_waste, width=3).grid(row=1, column=5, padx=2)
        
        # Scrollable frame for vial inputs
        canvas = tk.Canvas(main_frame, height=300, bg="white")
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=3, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        scrollbar.grid(row=3, column=4, sticky=(tk.N, tk.S))
        
        # Create input fields for vials
        self.scrollable_frame = scrollable_frame
        self.canvas = canvas
        self.update_vial_inputs()
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=4, pady=10)
        
        start_button = ttk.Button(button_frame, text="Start Workflow", 
                                 command=self.start_workflow)
        start_button.pack(side=tk.LEFT, padx=5)
        
        clear_button = ttk.Button(button_frame, text="Clear All", 
                                 command=self.clear_all)
        clear_button.pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready", foreground="green")
        self.status_label.grid(row=5, column=0, columnspan=4, pady=5)
        
        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
    
    def update_vial_inputs(self):
        """Create input fields for each vial."""
        # Clear existing inputs
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.vial_inputs = []
        
        num_vials = self.num_vials.get()
        
        # Create header
        header_frame = ttk.Frame(self.scrollable_frame)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(header_frame, text="Vial", width=8, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Label(header_frame, text="Water %", width=10, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Label(header_frame, text="Red %", width=10, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Label(header_frame, text="Blue %", width=10, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Label(header_frame, text="Yellow %", width=10, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Label(header_frame, text="Sum", width=8, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        
        # Create input rows
        for i in range(num_vials):
            frame = ttk.Frame(self.scrollable_frame)
            frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Vial number
            ttk.Label(frame, text=f"Vial {i}", width=8).pack(side=tk.LEFT, padx=5)
            
            # Percentage inputs
            random_pct = self.generate_random_percentages()
            water_var = tk.DoubleVar(value=random_pct['water'])
            red_var = tk.DoubleVar(value=random_pct['red'])
            blue_var = tk.DoubleVar(value=random_pct['blue'])
            yellow_var = tk.DoubleVar(value=random_pct['yellow'])
            sum_var = tk.StringVar(value="100.00")
            
            # Use i=i to capture current value (avoid closure bug)
            def make_update_callback(idx):
                return lambda *args: self.update_sum(idx)
            
            update_cb = make_update_callback(i)
            
            # Add trace to update sum when values change (including typing)
            water_var.trace_add('write', update_cb)
            red_var.trace_add('write', update_cb)
            blue_var.trace_add('write', update_cb)
            yellow_var.trace_add('write', update_cb)
            
            water_spin = ttk.Spinbox(frame, from_=0, to=100, textvariable=water_var, 
                                     width=8, increment=1)
            water_spin.pack(side=tk.LEFT, padx=5)
            
            red_spin = ttk.Spinbox(frame, from_=0, to=100, textvariable=red_var,
                                   width=8, increment=1)
            red_spin.pack(side=tk.LEFT, padx=5)
            
            blue_spin = ttk.Spinbox(frame, from_=0, to=100, textvariable=blue_var,
                                    width=8, increment=1)
            blue_spin.pack(side=tk.LEFT, padx=5)
            
            yellow_spin = ttk.Spinbox(frame, from_=0, to=100, textvariable=yellow_var,
                                      width=8, increment=1)
            yellow_spin.pack(side=tk.LEFT, padx=5)
            
            sum_label = ttk.Label(frame, textvariable=sum_var, width=8, foreground="blue")
            sum_label.pack(side=tk.LEFT, padx=5)
            
            self.vial_inputs.append({
                'water': water_var,
                'red': red_var,
                'blue': blue_var,
                'yellow': yellow_var,
                'sum': sum_var,
                'sum_label': sum_label
            })
        
        # Initial sum update
        for i in range(num_vials):
            self.update_sum(i)
    
    def update_sum(self, vial_idx):
        """Update the sum display for a vial."""
        if vial_idx >= len(self.vial_inputs):
            return
        
        vial = self.vial_inputs[vial_idx]
        
        # Safely get values, handling invalid input
        try:
            water = vial['water'].get()
        except tk.TclError: 
            water = 0
        try:
            red = vial['red'].get()
        except tk.TclError:
            red = 0
        try:
            blue = vial['blue'].get()
        except tk.TclError:
            blue = 0
        try:
            yellow = vial['yellow'].get()
        except tk.TclError:
            yellow = 0
        
        total = water + red + blue + yellow
        
        # Show 2 decimal places for accuracy
        vial['sum'].set(f"{total:.2f}")
        
        # Color code: green if exactly 100, red otherwise
        if total == 100.0:
            vial['sum_label'].config(foreground="green")
        else:
            vial['sum_label'].config(foreground="red")
    
    def get_percentage_sets(self):
        """Get percentage sets from inputs."""
        percentage_sets = []
        
        for vial in self.vial_inputs:
            pct_set = {
                'water': vial['water'].get(),
                'red': vial['red'].get(),
                'blue': vial['blue'].get(),
                'yellow': vial['yellow'].get()
            }
            percentage_sets.append(pct_set)
        
        return percentage_sets
    
    def validate_percentages(self, percentage_sets):
        """Validate percentage sets."""
        for i, pct_set in enumerate(percentage_sets):
            total = sum(pct_set.values())
            if not (99.9 <= total <= 100.1):
                messagebox.showerror("Validation Error", 
                    f"Vial {i}: Percentages sum to {total:.1f}%, must equal 100%")
                return False
            
            for color, pct in pct_set.items():
                if pct < 0 or pct > 100:
                    messagebox.showerror("Validation Error",
                        f"Vial {i}, {color}: {pct}% is outside valid range [0, 100]")
                    return False
        
        return True
    
    def clear_all(self):
        """Clear all inputs."""
        for vial in self.vial_inputs:
            vial['water'].set(50)
            vial['red'].set(25)
            vial['blue'].set(15)
            vial['yellow'].set(10)
        
        for i in range(len(self.vial_inputs)):
            self.update_sum(i)
    
    def percentages_to_volumes(self, percentages):
        """Convert percentage set to volumes in mL."""
        volumes = {}
        color_map = {'water': 'Water', 'red': 'Red', 'blue': 'Blue', 'yellow': 'Yellow'}
        
        for lowercase_color, percentage in percentages.items():
            capitalized_color = color_map[lowercase_color.lower()]
            volumes[capitalized_color] = (percentage / 100.0) * self.TOTAL_VOLUME_ML
        
        return volumes
    
    def get_vial_mapping(self):
        """Get current vial mapping from GUI inputs."""
        return {
            'Red': self.vial_red.get(),
            'Yellow': self.vial_yellow.get(),
            'Blue': self.vial_blue.get(),
            'Water': self.vial_water.get(),
            'wash': self.vial_wash.get(),
            'waste': self.vial_waste.get()
        }
    
    def condition_needle(self, dispenser, logger, vial_mapping):
        """Condition the needle by dispensing between wash and waste."""
        logger.debug("Conditioning needle: wash -> waste")
        
        dispenser.dispense_between(
            source_location="vial_rack_12",
            source_index=vial_mapping['wash'],
            dest_location="vial_rack_12",
            dest_index=vial_mapping['waste'],
            transfer_vol=0.5  # 500 μL for conditioning
        )
        
        time.sleep(0.2)
    
    def dispense_colors_to_vials(self, dispenser, percentage_sets, logger, vial_mapping, dest_start_index):
        """Dispense all color combinations to vials with conditioning between each color."""
        num_vials = len(percentage_sets)
        logger.info(f"Preparing to fill {num_vials} vials with {len(self.COLOR_ORDER)} colors each")
        logger.info(f"Dispensing strategy: One color at a time across all vials")
        logger.info(f"Total dispense operations: {num_vials * len(self.COLOR_ORDER)} (plus {len(self.COLOR_ORDER)} conditioning steps)")
        
        # Dispense one color at a time to all vials
        for color in self.COLOR_ORDER:
            logger.info(f"\n{'='*70}")
            logger.info(f"Dispensing {color} to all vials")
            logger.info(f"{'='*70}")
            
            for vial_idx, percentages in enumerate(percentage_sets):
                volumes = self.percentages_to_volumes(percentages)
                volume_ml = volumes.get(color, 0)
                dest_vial = dest_start_index + vial_idx
                
                if volume_ml > 0.025:  # Only dispense if volume is > 25 μL (minimum)
                    logger.info(f"Vial {dest_vial}: Dispensing {volume_ml:.3f} mL of {color}")
                    self.status_label.config(text=f"Dispensing {color} to vial {dest_vial}...")
                    self.root.update()
                    
                    try:
                        dispenser.dispense_between(
                            source_location="vial_rack_12",
                            source_index=vial_mapping[color],
                            dest_location="vial_rack_12",
                            dest_index=dest_vial,
                            transfer_vol=volume_ml
                        )
                        logger.debug(f"✓ {color} dispensed successfully to vial {dest_vial}")
                    except Exception as e:
                        logger.error(f"✗ Failed to dispense {color} to vial {dest_vial}: {e}")
                        raise
                else:
                    logger.debug(f"Vial {dest_vial}: Skipping {color} (volume {volume_ml:.3f} mL < 25 μL minimum)")
                
                time.sleep(0.1)
            
            # Condition needle after all vials of this color are done
            logger.info(f"Conditioning needle after {color} dispense...")
            self.status_label.config(text=f"Conditioning needle after {color}...")
            self.root.update()
            
            try:
                self.condition_needle(dispenser, logger, vial_mapping)
                logger.debug(f"✓ Needle conditioned after {color}")
            except Exception as e:
                logger.error(f"✗ Failed to condition needle: {e}")
                raise
        
        logger.info(f"\n✓ Successfully filled all {num_vials} vials")
    
    def run_workflow(self, percentage_sets):
        """Run the workflow in a background thread."""
        try:
            # Get current settings from GUI
            is_virtual = self.virtual_mode.get()
            vial_mapping = self.get_vial_mapping()
            
            # Destination vials start after the source vials (6-11)
            dest_start_index = 6
            
            # Initialize logging
            logger = start_workflow_logging("multi_well_percentage_dispenser", virtual=is_virtual)
            
            self.status_label.config(text="Initializing hardware...", foreground="blue")
            self.root.update()
            
            # Initialize hardware
            dispenser = Liquid_Dispenser(
                cnc_comport="COM5",
                actuator_comport="COM3",
                virtual=is_virtual
            )
            
            logger.info("=" * 70)
            logger.info("Starting Multi-Well Percentage Dispenser Workflow (GUI)")
            logger.info(f"Virtual mode: {is_virtual}")
            logger.info(f"Vial mapping: {vial_mapping}")
            logger.info(f"Destination vials: {dest_start_index} to {dest_start_index + len(percentage_sets) - 1}")
            logger.info("=" * 70)
            
            starttime = time.time()
            
            self.dispense_colors_to_vials(dispenser, percentage_sets, logger, vial_mapping, dest_start_index)
            
            elapsed_time = time.time() - starttime
            
            # Success
            self.status_label.config(text=f"✓ Completed in {elapsed_time:.1f}s", foreground="green")
            messagebox.showinfo("Success", f"Workflow completed successfully!\nTime: {elapsed_time:.1f} seconds")
            
            logger.info(f"✓ WORKFLOW COMPLETED SUCCESSFULLY in {elapsed_time:.1f} seconds")
            
        except Exception as e:
            self.status_label.config(text="✗ Workflow failed", foreground="red")
            messagebox.showerror("Workflow Error", f"Workflow failed:\n{str(e)}")
        
        finally:
            self.workflow_running = False
    
    def start_workflow(self):
        """Validate and start the workflow."""
        if self.workflow_running:
            messagebox.showwarning("Warning", "Workflow is already running")
            return
        
        percentage_sets = self.get_percentage_sets()
        
        # Validate
        if not self.validate_percentages(percentage_sets):
            return
        
        # Confirm
        num_vials = len(percentage_sets)
        response = messagebox.askyesno("Confirm", 
            f"Start workflow with {num_vials} vials?\n\nThis will dispense liquids.")
        
        if not response:
            return
        
        self.workflow_running = True
        self.status_label.config(text="Workflow starting...", foreground="blue")
        
        # Run in background thread
        workflow_thread = threading.Thread(target=self.run_workflow, args=(percentage_sets,))
        workflow_thread.daemon = True
        workflow_thread.start()


def main():
    root = tk.Tk()
    app = PercentageDispenseGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
