"""
Shared Initialization Functions for Color Matching Optimizers

This module provides unified initialization strategies that can be used by
BayBE, Gradient, and Convex optimizers to ensure consistent starting points.

Two initialization modes:
1. Corner Points: Deterministic points covering extremes and center
2. Sobol Sampling: Space-filling design using ax library
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)

def generate_corner_points_initialization(batch_size, random_seed):
    """
    Generate corner points initialization that all optimizers can use.
    
    Returns deterministic corner points of the feasible region:
    - Pure colors: [1000,0,0], [0,1000,0], [0,0,1000] 
    - Binary mixes: [500,500,0], [500,0,500], [0,500,500]
    - Equal mix: [333,333,334] (as requested, sums to 1000)
    - Additional points with small perturbations if needed
    
    Args:
        batch_size: Number of points to generate
        random_seed: Seed for consistent perturbations
        
    Returns:
        List of [R, Y, B] recommendations
    """
    np.random.seed(random_seed)  # For consistent perturbations
    
    # Core corner points (deterministic)
    corners = [
        [1000, 0, 0],     # Pure R
        [0, 1000, 0],     # Pure Y  
        [0, 0, 1000],     # Pure B
        [500, 500, 0],    # R+Y mix
        [500, 0, 500],    # R+B mix
        [0, 500, 500],    # Y+B mix
        [333, 333, 334],  # Equal mix (sums to 1000)
    ]
    
    recommendations = []
    
    for i in range(batch_size):
        if i < len(corners):
            # Use corner points directly
            point = corners[i].copy()
        else:
            # Generate additional points with perturbations around existing corners
            base_idx = (i - len(corners)) % len(corners)
            base_point = np.array(corners[base_idx])
            
            # Add small perturbation
            perturbation = np.random.normal(0, 50, 3)
            point = base_point + perturbation
            
            # Project to feasible space
            point = _project_to_feasible_space(point)
        
        recommendations.append(point)
    
    logger.info(f"Generated {len(recommendations)} corner point recommendations")
    return recommendations

def generate_sobol_initialization(batch_size, random_seed):
    """
    Generate Sobol sequence initialization using ax library for consistent seeding.
    
    This provides space-filling design like BayBE's default behavior.
    
    Args:
        batch_size: Number of points to generate
        random_seed: Seed for Sobol sequence
        
    Returns:
        List of [R, Y, B] recommendations
    """
    try:
        from ax.utils.sampling import sobol
        
        # Generate Sobol sequence in [0,1]^3
        sobol_points = sobol(n=batch_size, d=3, seed=random_seed)
        
        recommendations = []
        for point in sobol_points:
            # Scale to [0,1000] and ensure sum = 1000
            scaled_point = point * 1000
            
            # Normalize to sum to 1000
            if scaled_point.sum() > 0:
                scaled_point = scaled_point * (1000 / scaled_point.sum())
            else:
                scaled_point = np.array([333.33, 333.33, 333.34])
            
            # Project to feasible space and discretize
            final_point = _project_to_feasible_space(scaled_point)
            recommendations.append(final_point)
        
        logger.info(f"Generated {len(recommendations)} Sobol sequence recommendations")
        return recommendations
        
    except ImportError:
        logger.warning("ax library not available, falling back to corner points")
        return generate_corner_points_initialization(batch_size, random_seed)

def _project_to_feasible_space(point):
    """
    Project point to feasible region: non-negative, sum=1000, discrete values.
    Shared utility function for all optimizers.
    
    Args:
        point: [R, Y, B] values (can be float)
        
    Returns:
        [R, Y, B] values as integers summing to 1000
    """
    point = np.array(point)
    
    # Ensure non-negative
    point = np.maximum(0, point)
    
    # Normalize to sum to 1000
    if point.sum() > 0:
        point = point * (1000 / point.sum())
    else:
        point = np.array([333.33, 333.33, 333.34])  # Default uniform
    
    # Round to discrete values (multiples of 50)
    point = np.round(point / 50) * 50
    
    # Final adjustment to ensure exact sum
    diff = 1000 - point.sum()
    if diff != 0:
        # Add difference to component with largest value
        max_idx = np.argmax(point)
        point[max_idx] += diff
        point[max_idx] = max(0, point[max_idx])  # Ensure non-negative
    
    return point.astype(int).tolist()