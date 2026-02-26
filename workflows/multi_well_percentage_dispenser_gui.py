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
        self.VIRTUAL = True
        self.TOTAL_VOLUME_ML = 2.0
        self.RESERVOIRS = {
            'Water': 0,
            'Red': 1,
            'Blue': 2,
            'Yellow': 3,
            'wash': 4,
            'waste': 5
        }
        self.COLOR_ORDER = ['Water', 'Red', 'Blue', 'Yellow']
        
        self.setup_ui()
    
    def setup_ui(self):
        """Create the GUI layout."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="Multi-Well Percentage Dispenser", 
                               font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=4, pady=10)
        
        # Number of vials selector
        num_label = ttk.Label(main_frame, text="Number of Vials:")
        num_label.grid(row=1, column=0, sticky=tk.W, pady=10)
        
        num_spinbox = ttk.Spinbox(main_frame, from_=1, to=12, textvariable=self.num_vials,
                                  width=5, command=self.update_vial_inputs)
        num_spinbox.grid(row=1, column=1, sticky=tk.W, padx=5)
        
        # Scrollable frame for vial inputs
        canvas = tk.Canvas(main_frame, height=400, bg="white")
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), pady=20)
        scrollbar.grid(row=2, column=4, sticky=(tk.N, tk.S))
        
        # Create input fields for vials
        self.scrollable_frame = scrollable_frame
        self.canvas = canvas
        self.update_vial_inputs()
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=4, pady=20)
        
        start_button = ttk.Button(button_frame, text="Start Workflow", 
                                 command=self.start_workflow)
        start_button.pack(side=tk.LEFT, padx=5)
        
        clear_button = ttk.Button(button_frame, text="Clear All", 
                                 command=self.clear_all)
        clear_button.pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready", foreground="green")
        self.status_label.grid(row=4, column=0, columnspan=4, pady=10)
        
        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
    
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
            water_var = tk.DoubleVar(value=50)
            red_var = tk.DoubleVar(value=25)
            blue_var = tk.DoubleVar(value=15)
            yellow_var = tk.DoubleVar(value=10)
            sum_var = tk.StringVar(value="100")
            
            water_spin = ttk.Spinbox(frame, from_=0, to=100, textvariable=water_var, 
                                     width=8, command=lambda: self.update_sum(i))
            water_spin.pack(side=tk.LEFT, padx=5)
            
            red_spin = ttk.Spinbox(frame, from_=0, to=100, textvariable=red_var,
                                   width=8, command=lambda: self.update_sum(i))
            red_spin.pack(side=tk.LEFT, padx=5)
            
            blue_spin = ttk.Spinbox(frame, from_=0, to=100, textvariable=blue_var,
                                    width=8, command=lambda: self.update_sum(i))
            blue_spin.pack(side=tk.LEFT, padx=5)
            
            yellow_spin = ttk.Spinbox(frame, from_=0, to=100, textvariable=yellow_var,
                                      width=8, command=lambda: self.update_sum(i))
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
        total = (vial['water'].get() + vial['red'].get() + 
                vial['blue'].get() + vial['yellow'].get())
        
        vial['sum'].set(f"{total:.1f}")
        
        # Color code: green if 100, red otherwise
        if 99.9 <= total <= 100.1:
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
    
    def condition_needle(self, dispenser, logger):
        """Condition the needle by dispensing between wash and waste."""
        logger.debug("Conditioning needle: wash -> waste")
        
        dispenser.dispense_between(
            source_location="reservoir_12",
            source_index=self.RESERVOIRS['wash'],
            dest_location="reservoir_12",
            dest_index=self.RESERVOIRS['waste'],
            transfer_vol=0.5  # 500 μL for conditioning
        )
        
        time.sleep(0.2)
    
    def dispense_colors_to_vials(self, dispenser, percentage_sets, logger):
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
                
                if volume_ml > 0.025:  # Only dispense if volume is > 25 μL (minimum)
                    logger.info(f"Vial {vial_idx}: Dispensing {volume_ml:.3f} mL of {color}")
                    self.status_label.config(text=f"Dispensing {color} to vial {vial_idx}...")
                    self.root.update()
                    
                    try:
                        dispenser.dispense_between(
                            source_location="reservoir_12",
                            source_index=self.RESERVOIRS[color],
                            dest_location="vial_rack",
                            dest_index=vial_idx,
                            transfer_vol=volume_ml
                        )
                        logger.debug(f"✓ {color} dispensed successfully to vial {vial_idx}")
                    except Exception as e:
                        logger.error(f"✗ Failed to dispense {color} to vial {vial_idx}: {e}")
                        raise
                else:
                    logger.debug(f"Vial {vial_idx}: Skipping {color} (volume {volume_ml:.3f} mL < 25 μL minimum)")
                
                time.sleep(0.1)
            
            # Condition needle after all vials of this color are done
            logger.info(f"Conditioning needle after {color} dispense...")
            self.status_label.config(text=f"Conditioning needle after {color}...")
            self.root.update()
            
            try:
                self.condition_needle(dispenser, logger)
                logger.debug(f"✓ Needle conditioned after {color}")
            except Exception as e:
                logger.error(f"✗ Failed to condition needle: {e}")
                raise
        
        logger.info(f"\n✓ Successfully filled all {num_vials} vials")
    
    def run_workflow(self, percentage_sets):
        """Run the workflow in a background thread."""
        try:
            # Initialize logging
            logger = start_workflow_logging("multi_well_percentage_dispenser", virtual=self.VIRTUAL)
            
            self.status_label.config(text="Initializing hardware...", foreground="blue")
            self.root.update()
            
            # Initialize hardware
            dispenser = Liquid_Dispenser(
                cnc_comport="COM3",
                actuator_comport="COM7",
                virtual=self.VIRTUAL
            )
            
            logger.info("=" * 70)
            logger.info("Starting Multi-Well Percentage Dispenser Workflow (GUI)")
            logger.info("=" * 70)
            
            starttime = time.time()
            
            self.dispense_colors_to_vials(dispenser, percentage_sets, logger)
            
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
