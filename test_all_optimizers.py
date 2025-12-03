"""
Quick test to compare all three optimizers in virtual mode
"""

import subprocess
import os
import time

def run_optimizer_test(optimizer_type):
    """Run the workflow with a specific optimizer and measure performance"""
    print(f"\n🚀 Testing {optimizer_type.upper()} Optimizer...")
    
    # Read current workflow file
    with open("workflows/color_matching_workflow.py", "r") as f:
        content = f.read()
    
    # Backup original
    with open("workflows/color_matching_workflow_backup.py", "w") as f:
        f.write(content)
    
    # Update optimizer type
    updated_content = content.replace(
        f"OPTIMIZER_TYPE = 'baybe'", 
        f"OPTIMIZER_TYPE = '{optimizer_type}'"
    ).replace(
        f"OPTIMIZER_TYPE = 'gradient'", 
        f"OPTIMIZER_TYPE = '{optimizer_type}'"
    ).replace(
        f"OPTIMIZER_TYPE = 'convex'", 
        f"OPTIMIZER_TYPE = '{optimizer_type}'"
    )
    
    # Also ensure we only run a few iterations for testing
    updated_content = updated_content.replace(
        "MAX_WELLS = 24",
        "MAX_WELLS = 8"  # Only run 8 wells for quick test
    )
    
    # Write updated file
    with open("workflows/color_matching_workflow.py", "w") as f:
        f.write(updated_content)
    
    # Run the workflow
    start_time = time.time()
    try:
        result = subprocess.run(
            ["python", "workflows/color_matching_workflow.py"],
            capture_output=True,
            text=True,
            cwd="."
        )
        end_time = time.time()
        
        if result.returncode == 0:
            print(f"✅ {optimizer_type.upper()} completed successfully in {end_time-start_time:.1f}s")
            
            # Check for convergence in logs
            log_files = sorted([f for f in os.listdir("logs") if f.startswith("color_matching")], 
                              key=lambda x: os.path.getmtime(f"logs/{x}"))
            if log_files:
                latest_log = f"logs/{log_files[-1]}"
                with open(latest_log, "r") as f:
                    log_content = f.read()
                    if "Best result found" in log_content:
                        best_line = [line for line in log_content.split('\n') if 'Best result found' in line]
                        if best_line:
                            print(f"   {best_line[-1].split('|')[-1].strip()}")
                
        else:
            print(f"❌ {optimizer_type.upper()} failed:")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ Error running {optimizer_type}: {e}")
    
    # Restore original file
    with open("workflows/color_matching_workflow_backup.py", "r") as f:
        original_content = f.read()
    with open("workflows/color_matching_workflow.py", "w") as f:
        f.write(original_content)

def main():
    print("🧪 OPTIMIZER COMPARISON TEST")
    print("=" * 40)
    
    optimizers = ['baybe', 'gradient', 'convex']
    
    for optimizer in optimizers:
        run_optimizer_test(optimizer)
    
    print(f"\n📊 COMPARISON COMPLETE!")
    print("Check the output/ folder for results from each optimizer")
    print("Look for patterns in convergence speed and final results")

if __name__ == "__main__":
    main()