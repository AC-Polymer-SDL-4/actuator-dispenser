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
            # Use gradient-based exploration from multiple starting points
            logger.info("Using gradient-based exploration for recommendations")
            
            for i in range(batch_size):
                if i == 0 and self.current_best is not None:
                    # First recommendation: gradient step from current best
                    rec = self._gradient_step_from_best()
                else:
                    # Additional recommendations: explore different regions
                    if len(self.results_data) >= 3:
                        # Use gradient from different good points
                        rec = self._explore_gradient_direction()
                    else:
                        # Still exploring randomly with some bias toward good regions
                        rec = self._biased_random_exploration()
                
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
    
    def _gradient_step_from_best(self):
        """Take a gradient step from the current best solution"""
        if self.current_best is None:
            return self._generate_random_valid_combination()
        
        # Compute approximate gradient from nearby points
        gradient = self._compute_local_gradient(self.current_best)
        
        # Take a step in the negative gradient direction (minimize)
        step_size = 150  # Adjust as needed
        current = np.array(self.current_best)
        new_point = current - step_size * gradient
        
        # Project back to feasible space
        new_point = self._project_to_feasible(new_point)
        
        logger.info(f"Gradient step from {self.current_best} to {new_point.tolist()}")
        return new_point.tolist()
    
    def _explore_gradient_direction(self):
        """Explore in gradient directions from different good points"""
        # Find second and third best points
        sorted_results = sorted(self.results_data, key=lambda x: x['output'])
        
        if len(sorted_results) >= 2:
            # Use second or third best as starting point
            start_idx = min(1 + np.random.randint(0, min(2, len(sorted_results)-1)), len(sorted_results)-1)
            start_result = sorted_results[start_idx]
            start_point = [start_result['R'], start_result['Y'], start_result['B']]
            
            # Compute gradient and take step
            gradient = self._compute_local_gradient(start_point)
            step_size = 100 + np.random.uniform(0, 100)  # Variable step size
            
            current = np.array(start_point)
            new_point = current - step_size * gradient
            new_point = self._project_to_feasible(new_point)
            
            logger.info(f"Gradient exploration from point {start_idx} with step {step_size:.1f}")
            return new_point.tolist()
        else:
            return self._biased_random_exploration()
    
    def _biased_random_exploration(self):
        """Random exploration biased toward good regions"""
        if self.current_best is None:
            return self._generate_random_valid_combination()
        
        # Generate point around current best with larger variance
        noise_scale = 200  # Larger than perturbation
        biased_point = self._perturb_point(self.current_best, noise_scale)
        
        logger.info(f"Biased random exploration around best point")
        return biased_point
    
    def _compute_local_gradient(self, point):
        """Compute approximate gradient using finite differences"""
        if len(self.results_data) < 2:
            return np.random.normal(0, 0.1, 3)  # Random direction if insufficient data
        
        point = np.array(point)
        gradient = np.zeros(3)
        epsilon = 50  # Step size for finite difference
        
        for i in range(3):
            # Create perturbed points
            point_plus = point.copy()
            point_minus = point.copy()
            
            point_plus[i] = min(1000, point_plus[i] + epsilon)
            point_minus[i] = max(0, point_minus[i] - epsilon)
            
            # Ensure constraints are satisfied
            point_plus = self._project_to_feasible(point_plus)
            point_minus = self._project_to_feasible(point_minus)
            
            # Estimate function values at these points
            f_plus = self._estimate_function_value(point_plus)
            f_minus = self._estimate_function_value(point_minus)
            
            # Finite difference gradient
            gradient[i] = (f_plus - f_minus) / (2 * epsilon)
        
        # Normalize gradient
        grad_norm = np.linalg.norm(gradient)
        if grad_norm > 1e-6:
            gradient = gradient / grad_norm
        else:
            gradient = np.random.normal(0, 0.1, 3)  # Random if flat
        
        return gradient
    
    def _estimate_function_value(self, point):
        """Estimate function value using inverse distance weighting with exploration bonus"""
        if len(self.results_data) == 0:
            return 0.0
        
        distances = []
        values = []
        for result in self.results_data:
            result_point = np.array([result['R'], result['Y'], result['B']])
            dist = np.linalg.norm(point - result_point)
            distances.append(dist)
            values.append(result['output'])
        
        distances = np.array(distances)
        values = np.array(values)
        
        # Find minimum distance to add exploration bonus
        min_dist = np.min(distances)
        exploration_bonus = -0.1 * min_dist  # Bonus for exploring new areas
        
        # Inverse distance weighting with minimum distance threshold
        distances = np.maximum(distances, 10.0)  # Avoid division by zero
        weights = 1.0 / (distances ** 2)  # Stronger locality
        weights = weights / weights.sum()
        
        estimated_value = np.dot(weights, values) + exploration_bonus
        return estimated_value
    
    def _project_to_feasible(self, point):
        """Project point to feasible region (non-negative, sum=1000, discrete)"""
        point = np.maximum(0, point)  # Non-negative
        
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
        
        return point


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