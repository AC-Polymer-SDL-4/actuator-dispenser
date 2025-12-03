"""
Test script to demonstrate different optimization methods for color matching.

This script shows how to easily switch between Bayesian optimization, 
gradient descent, and convex optimization by changing the OPTIMIZER_TYPE
in the color matching workflow.
"""

import sys
import os

# Add workflows directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_optimizer_import(optimizer_type):
    """Test that optimizer can be imported successfully"""
    print(f"\n=== Testing {optimizer_type.upper()} Optimizer ===")
    
    try:
        if optimizer_type == 'baybe':
            from color_matching_optimizer import initialize_campaign, get_initial_recommendations, get_new_recs_from_results
        elif optimizer_type == 'gradient':
            from color_matching_gradient_optimizer import initialize_campaign, get_initial_recommendations, get_new_recs_from_results
        elif optimizer_type == 'convex':
            from color_matching_convex_optimizer import initialize_campaign, get_initial_recommendations, get_new_recs_from_results
        else:
            raise ValueError(f"Unknown optimizer: {optimizer_type}")
            
        print(f"✓ {optimizer_type.title()} optimizer imported successfully")
        
        # Test initialization
        campaign, searchspace = initialize_campaign(upper_bound=50, random_seed=42)
        print(f"✓ {optimizer_type.title()} campaign initialized")
        
        # Test initial recommendations
        campaign, initial_suggestions = get_initial_recommendations(campaign, size=3)
        print(f"✓ Generated {len(initial_suggestions)} initial recommendations")
        print("Sample recommendations:")
        print(initial_suggestions)
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("  Make sure required packages are installed:")
        if optimizer_type == 'gradient':
            print("  - scipy")
        elif optimizer_type == 'convex':
            print("  - cvxpy")
            print("  - scipy")
        return False
        
    except Exception as e:
        print(f"✗ Error testing {optimizer_type}: {e}")
        return False

def main():
    """Test all available optimizers"""
    print("Testing Color Matching Optimization Methods")
    print("=" * 50)
    
    optimizers = ['baybe', 'gradient', 'convex']
    results = {}
    
    for optimizer in optimizers:
        results[optimizer] = test_optimizer_import(optimizer)
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    for optimizer, success in results.items():
        status = "✓ Working" if success else "✗ Failed"
        print(f"  {optimizer.upper():<10}: {status}")
    
    print(f"\n📋 TO USE DIFFERENT OPTIMIZERS:")
    print(f"   Edit color_matching_workflow.py and change:")
    print(f"   OPTIMIZER_TYPE = 'baybe'     # Bayesian optimization (default)")
    print(f"   OPTIMIZER_TYPE = 'gradient'  # Gradient descent")
    print(f"   OPTIMIZER_TYPE = 'convex'    # Convex optimization")

if __name__ == "__main__":
    main()