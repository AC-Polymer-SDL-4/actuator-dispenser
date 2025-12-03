"""
Gradient Descent Optimizer for Color Matching

Uses scipy.optimize with gradient descent methods (L-BFGS-B) to find optimal color mixing ratios.
Maintains the same interface as the BayBE optimizer for easy integration.
"""

import numpy as np
from scipy.optimize import minimize, Bounds
from scipy.optimize import NonlinearConstraint
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class GradientDescentCampaign:
    def __init__(self, bounds, constraints, random_seed=42):
        self.bounds = bounds
        self.constraints = constraints
        self.random_seed = random_seed
        self.results_data = []
        self.current_best = None
        self.current_best_score = float('inf')
        np.random.seed(random_seed)
        
    def recommend(self, batch_size=1):
        """Generate recommendations using gradient descent or random sampling"""
        recommendations = []
        
        if len(self.results_data) == 0:
            # Initial random recommendations
            logger.info("Generating initial random recommendations")
            for _ in range(batch_size):
                # Generate random valid combinations
                rec = self._generate_random_valid_combination()
                recommendations.append(rec)
        else:
            # Use gradient descent from current best + some exploration
            logger.info("Using gradient descent for recommendations")
            
            for i in range(batch_size):
                if i == 0 and self.current_best is not None:
                    # First recommendation: optimize from current best
                    rec = self._optimize_from_point(self.current_best)
                else:
                    # Additional recommendations: optimize from perturbed points
                    if self.current_best is not None:
                        start_point = self._perturb_point(self.current_best)
                    else:
                        start_point = self._generate_random_valid_combination()
                    rec = self._optimize_from_point(start_point)
                
                recommendations.append(rec)
        
        # Convert to DataFrame format expected by workflow
        df_data = []
        for rec in recommendations:
            df_data.append({
                'R': rec[0],
                'Y': rec[1], 
                'B': rec[2],
                'Water': 1000 - sum(rec) if sum(rec) < 1000 else 0
            })
        
        return pd.DataFrame(df_data)
    
    def add_measurements(self, measurements_df):
        """Add experimental results and update best solution"""
        logger.info(f"Adding {len(measurements_df)} measurements")
        
        for _, row in measurements_df.iterrows():
            result = {
                'R': row['R'],
                'Y': row['Y'],
                'B': row['B'],
                'Water': row.get('Water', 0),
                'output': row['output']  # Color difference score
            }
            self.results_data.append(result)
            
            # Update current best
            if result['output'] < self.current_best_score:
                self.current_best_score = result['output']
                self.current_best = [result['R'], result['Y'], result['B']]
                logger.info(f"New best solution found: {self.current_best} with score {self.current_best_score:.4f}")
    
    def _generate_random_valid_combination(self):
        """Generate random RGB combination that satisfies constraints"""
        # Generate random values that sum to <= 1000
        total = 1000
        
        # Method: Generate 2 random cuts in [0, total] and use the segments
        cuts = sorted(np.random.uniform(0, total, 2))
        r = cuts[0]
        y = cuts[1] - cuts[0]
        b = total - cuts[1]
        
        # Round to nearest 50 (to match discrete parameter space)
        r = round(r / 50) * 50
        y = round(y / 50) * 50
        b = round(b / 50) * 50
        
        # Ensure sum is exactly 1000
        total_actual = r + y + b
        if total_actual != 1000:
            diff = 1000 - total_actual
            # Add difference to largest component
            max_idx = np.argmax([r, y, b])
            if max_idx == 0:
                r += diff
            elif max_idx == 1:
                y += diff
            else:
                b += diff
        
        # Clamp to bounds
        r = max(0, min(1000, r))
        y = max(0, min(1000, y))
        b = max(0, min(1000, b))
        
        return [r, y, b]
    
    def _perturb_point(self, point, noise_scale=100):
        """Add noise to a point while maintaining constraints"""
        perturbed = np.array(point) + np.random.normal(0, noise_scale, 3)
        
        # Project back to feasible space
        perturbed = np.maximum(0, perturbed)  # Non-negative
        
        # Normalize to sum to 1000
        if perturbed.sum() > 0:
            perturbed = perturbed * (1000 / perturbed.sum())
        else:
            perturbed = self._generate_random_valid_combination()
            
        # Round to discrete values
        perturbed = np.round(perturbed / 50) * 50
        
        return perturbed.tolist()
    
    def _optimize_from_point(self, start_point):
        """Run gradient descent optimization from a starting point"""
        
        # Define objective function (we'll use a surrogate since we don't have the true function)
        def surrogate_objective(x):
            # Use Gaussian Process-like interpolation from existing data
            if len(self.results_data) == 0:
                return 0.0  # No data yet
            
            distances = []
            values = []
            for result in self.results_data:
                point = np.array([result['R'], result['Y'], result['B']])
                dist = np.linalg.norm(x - point)
                distances.append(dist)
                values.append(result['output'])
            
            # Weighted average based on distance (inverse distance weighting)
            distances = np.array(distances)
            values = np.array(values)
            
            # Avoid division by zero
            distances = np.maximum(distances, 1e-6)
            weights = 1.0 / distances
            weights = weights / weights.sum()
            
            return np.dot(weights, values)
        
        # Constraint: sum must equal 1000
        def constraint_func(x):
            return x.sum() - 1000
        
        # Set up optimization problem
        bounds = Bounds([0, 0, 0], [1000, 1000, 1000])
        constraint = NonlinearConstraint(constraint_func, 0, 0)
        
        x0 = np.array(start_point)
        
        try:
            result = minimize(
                surrogate_objective,
                x0,
                method='SLSQP',  # Good for constraints
                bounds=bounds,
                constraints=constraint,
                options={'ftol': 1e-6, 'disp': False}
            )
            
            if result.success:
                optimized = result.x
            else:
                logger.warning("Optimization failed, using starting point")
                optimized = x0
                
        except Exception as e:
            logger.warning(f"Optimization error: {e}, using starting point")
            optimized = x0
        
        # Round to discrete values and ensure constraints
        optimized = np.round(optimized / 50) * 50
        optimized = np.maximum(0, optimized)
        
        # Ensure sum is exactly 1000
        if optimized.sum() != 1000:
            optimized = optimized * (1000 / optimized.sum())
            optimized = np.round(optimized / 50) * 50
        
        return optimized.tolist()


def initialize_campaign(upper_bound, random_seed, random_recs=False):
    """Initialize gradient descent campaign"""
    logger.info("Initializing Gradient Descent optimization campaign")
    
    # Define bounds for each parameter (0 to 1000 microliters)
    bounds = [(0, 1000), (0, 1000), (0, 1000)]
    
    # Define constraints (sum must equal 1000)
    constraints = {'type': 'eq', 'fun': lambda x: x.sum() - 1000}
    
    campaign = GradientDescentCampaign(bounds, constraints, random_seed)
    
    # Create dummy searchspace for compatibility
    searchspace = None  # Not used in gradient descent
    
    return campaign, searchspace


def get_initial_recommendations(campaign, size):
    """Get initial batch of recommendations"""
    logger.info(f"Generating initial batch of {size} recommendations using gradient descent")
    initial_suggestions = campaign.recommend(batch_size=size)
    return campaign, initial_suggestions


def get_new_recs_from_results(campaign, data, size):
    """Add results and get new recommendations"""
    logger.info(f"Adding measurements and generating {size} new recommendations")
    campaign.add_measurements(data)
    new_suggestions = campaign.recommend(batch_size=size)
    return campaign, new_suggestions