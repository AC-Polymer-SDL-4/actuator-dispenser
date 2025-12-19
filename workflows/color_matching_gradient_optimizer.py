"""
Gradient Descent Optimizer for Color Matching

Uses scipy.optimize with gradient descent methods (L-BFGS-B) to find optimal color mixing ratios.
Maintains the same interface as the BayBE optimizer for easy integration.
"""

import numpy as np
import sys
from scipy.optimize import minimize, Bounds
from scipy.optimize import NonlinearConstraint
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class GradientDescentCampaign:
    def __init__(self, bounds, constraints, random_seed=42, use_sobol=True):
        self.bounds = bounds
        self.constraints = constraints
        self.random_seed = random_seed
        self.use_sobol = use_sobol  # True = Sobol, False = corner points
        self.results_data = []
        self.current_best = None
        self.current_best_score = float('inf')
        self.initial_recommendations = None  # Store BayBE initial recommendations
        np.random.seed(random_seed)
        
    def set_initial_recommendations(self, recommendations_df):
        """Set initial recommendations from BayBE for consistency"""
        self.initial_recommendations = recommendations_df
        
    def recommend(self, batch_size=1):
        """Generate recommendations using traditional gradient descent"""
        recommendations = []
        
        if len(self.results_data) == 0:
            # Use initial recommendations from BayBE if available
            if self.initial_recommendations is not None:
                logger.info("Using BayBE initial recommendations for consistency")
                return self.initial_recommendations
            else:
                # Fallback to custom initialization (shouldn't happen)
                logger.warning("No BayBE recommendations available, using fallback initialization")
                if self.use_sobol:
                    recommendations = self._generate_sobol_like_initialization(batch_size)
                else:
                    recommendations = self._generate_corner_points_initialization(batch_size)
        else:
            # Use traditional gradient descent - start from best points and follow sequential paths
            logger.info("Using traditional gradient descent for recommendations")
            
            for i in range(batch_size):
                if i == 0:
                    # First path: continue from best point's trajectory
                    rec = self._traditional_gradient_step_from_best()
                elif i == 1 and len(self.results_data) >= 2:
                    # Second path: continue from second-best point's trajectory  
                    rec = self._traditional_gradient_step_from_second_best()
                else:
                    # Additional paths: small random perturbations of current trajectories
                    rec = self._perturbed_gradient_step()
                
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
    
    def _generate_sobol_like_initialization(self, batch_size):
        """Generate space-filling initialization similar to Sobol sequences"""
        recommendations = []
        
        # Generate space-filling points using stratified sampling
        for i in range(batch_size):
            # Use stratified sampling across the simplex
            t = np.random.random(2)
            t = np.sort(t)
            
            r = t[0] * 1000
            y = (t[1] - t[0]) * 1000
            b = (1 - t[1]) * 1000
            
            # Add small perturbations
            perturbation = np.random.normal(0, 25, 3)
            point = np.array([r, y, b]) + perturbation
            
            # Project to feasible space
            point = np.maximum(0, point)
            if point.sum() > 0:
                point = point * (1000 / point.sum())
            
            # Round to discrete values
            point = np.round(point / 50) * 50
            
            # Ensure sum is exactly 1000
            total_actual = point.sum()
            if total_actual != 1000:
                diff = 1000 - total_actual
                max_idx = np.argmax(point)
                point[max_idx] += diff
                point[max_idx] = max(0, point[max_idx])
            
            recommendations.append(point.astype(int).tolist())
        
        return recommendations
    
    def _generate_corner_points_initialization(self, batch_size):
        """Generate corner points of the feasible region"""
        corners = [
            [1000, 0, 0],    # Pure R
            [0, 1000, 0],    # Pure Y  
            [0, 0, 1000],    # Pure B
            [500, 500, 0],   # R+Y mix
            [500, 0, 500],   # R+B mix
            [0, 500, 500],   # Y+B mix
            [333, 333, 334], # Equal mix
            [800, 100, 100], # R-heavy
            [100, 800, 100], # Y-heavy
            [100, 100, 800], # B-heavy
        ]
        
        recommendations = []
        for i in range(batch_size):
            if i < len(corners):
                base_corner = corners[i]
            else:
                # If we need more than available corners, add noise to existing ones
                base_corner = corners[i % len(corners)]
            
            # Add small random perturbation
            noise = np.random.normal(0, 25, 3)
            point = np.array(base_corner) + noise
            
            # Project to feasible space
            point = np.maximum(0, point)
            point = np.minimum(1000, point)
            
            # Normalize to sum to 1000
            if point.sum() > 0:
                point = point * (1000 / point.sum())
            
            # Round to discrete values
            point = np.round(point / 50) * 50
            
            recommendations.append(point.astype(int).tolist())
        
        return recommendations
    
    def _traditional_gradient_step_from_best(self):
        """Traditional gradient descent from best point using last actual step"""
        if self.current_best is None:
            return self._generate_random_valid_combination()
        
        # Find the trajectory leading to the best point
        best_trajectory = self._find_trajectory_to_best()
        
        if best_trajectory is not None:
            gradient_vector, step_confidence = best_trajectory
            # Adaptive step size based on confidence, but respecting 50μL minimum
            base_step_size = 150  # Increased base to account for discretization
            adaptive_step_size = base_step_size * step_confidence
            
            # Ensure step size is at least 50μL for meaningful discrete steps
            adaptive_step_size = max(50, adaptive_step_size)
            
            current = np.array(self.current_best)
            new_point = current + adaptive_step_size * gradient_vector  # Continue in same direction
            new_point = self._project_to_feasible(new_point)
            
            logger.info(f"Traditional gradient step from best point: step_size={adaptive_step_size:.0f}μL, confidence={step_confidence:.2f}")
            return new_point.tolist()
        else:
            # No clear trajectory - take small exploration step
            return self._small_exploration_step(self.current_best)
    
    def _traditional_gradient_step_from_second_best(self):
        """Traditional gradient descent from second-best point"""
        sorted_results = sorted(self.results_data, key=lambda x: x['output'])
        if len(sorted_results) < 2:
            return self._generate_random_valid_combination()
            
        second_best_result = sorted_results[1]
        second_best_point = [second_best_result['R'], second_best_result['Y'], second_best_result['B']]
        
        # Find trajectory leading to second-best point
        second_trajectory = self._find_trajectory_to_point(second_best_point)
        
        if second_trajectory is not None:
            gradient_vector, step_confidence = second_trajectory
            base_step_size = 100  # Slightly smaller for second-best path
            adaptive_step_size = base_step_size * step_confidence
            
            # Ensure minimum 50μL step for discrete system
            adaptive_step_size = max(50, adaptive_step_size)
            
            current = np.array(second_best_point)
            new_point = current + adaptive_step_size * gradient_vector
            new_point = self._project_to_feasible(new_point)
            
            logger.info(f"Traditional gradient step from second-best point: step_size={adaptive_step_size:.0f}μL")
            return new_point.tolist()
        else:
            return self._small_exploration_step(second_best_point)
    
    def _perturbed_gradient_step(self):
        """Small perturbations of existing good trajectories"""
        if self.current_best is None:
            return self._generate_random_valid_combination()
            
        # Take a small step around best point with some noise
        perturbation = np.random.normal(0, 50, 3)  # 50 microliter noise
        new_point = np.array(self.current_best) + perturbation
        new_point = self._project_to_feasible(new_point)
        
        logger.info(f"Perturbed step around best point")
        return new_point.tolist()
    
    def _find_trajectory_to_best(self):
        """Find the actual experimental trajectory that led to the best point"""
        if len(self.results_data) < 2:
            return None
            
        # Sort by experiment order to find the path to best point
        best_score = self.current_best_score
        best_point = self.current_best
        
        # Look for the experiment that achieved this best score
        best_experiment_idx = None
        for i, result in enumerate(self.results_data):
            result_point = [result['R'], result['Y'], result['B']]
            if (np.array(result_point) == np.array(best_point)).all():
                best_experiment_idx = i
                break
        
        if best_experiment_idx is None or best_experiment_idx == 0:
            return None
            
        # Find the previous experiment that led to this one
        prev_result = self.results_data[best_experiment_idx - 1]
        prev_point = np.array([prev_result['R'], prev_result['Y'], prev_result['B']])
        curr_point = np.array(best_point)
        
        # Calculate actual step taken
        step_vector = curr_point - prev_point
        step_size = np.linalg.norm(step_vector)
        
        # Check if step size is meaningful given 50μL discretization
        if step_size < 50:  # Less than minimum discrete step
            return None
            
        # Normalize to unit vector
        gradient_direction = step_vector / step_size
        
        # Calculate confidence based on score improvement
        score_improvement = prev_result['output'] - best_score
        # Scale confidence appropriately for discrete steps
        step_confidence = min(1.0, max(0.3, score_improvement / 10.0))  # Increased minimum confidence
        
        logger.info(f"Found trajectory: step_size={step_size:.1f}μL, improvement={score_improvement:.2f}")
        return gradient_direction, step_confidence
    
    def _find_trajectory_to_point(self, target_point):
        """Find trajectory to any specific point"""
        if len(self.results_data) < 2:
            return None
            
        # Find experiment that achieved this point
        target_experiment_idx = None
        for i, result in enumerate(self.results_data):
            result_point = [result['R'], result['Y'], result['B']]
            if (np.array(result_point) == np.array(target_point)).all():
                target_experiment_idx = i
                break
        
        if target_experiment_idx is None or target_experiment_idx == 0:
            return None
            
        # Calculate trajectory
        prev_result = self.results_data[target_experiment_idx - 1]
        prev_point = np.array([prev_result['R'], prev_result['Y'], prev_result['B']])
        curr_point = np.array(target_point)
        
        step_vector = curr_point - prev_point
        step_size = np.linalg.norm(step_vector)
        
        # Check if step size is meaningful for discrete system
        if step_size < 50:
            return None
            
        gradient_direction = step_vector / step_size
        
        # Confidence based on score of this point
        current_result = self.results_data[target_experiment_idx]
        score_improvement = prev_result['output'] - current_result['output']
        step_confidence = min(1.0, max(0.3, score_improvement / 10.0))  # Increased minimum for discrete steps
        
        return gradient_direction, step_confidence
    
    def _small_exploration_step(self, starting_point):
        """Take a small exploration step when no clear trajectory exists"""
        # For discrete system, use at least 50μL perturbation
        perturbation = np.random.normal(0, 100, 3)  # 100μL exploration (was 75)
        new_point = np.array(starting_point) + perturbation
        new_point = self._project_to_feasible(new_point)
        
        logger.info(f"Small exploration step from {starting_point} (100μL noise)")
        return new_point.tolist()
    
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

    def _generate_deterministic_initial_batch(self, batch_size):
        """Generate deterministic initial batch for fair comparison across optimizers"""
        # Only used when use_sobol=False for direct comparison
        recommendations = []
        
        # Generate deterministic initial points using simple grid + perturbation
        if batch_size >= 5:
            # For standard initial batch size of 5, use a structured approach
            base_points = [
                [500, 250, 250],  # Red-heavy
                [250, 500, 250],  # Yellow-heavy  
                [250, 250, 500],  # Blue-heavy
                [333, 333, 334],  # Balanced
                [400, 300, 300],  # Slightly red-heavy balanced
            ]
            
            # Take first batch_size points and add small deterministic perturbations
            for i in range(min(batch_size, len(base_points))):
                point = base_points[i].copy()
                
                # Add deterministic perturbation based on seed and index
                rng = np.random.RandomState(self.random_seed + i)
                perturbation = rng.normal(0, 50, 3)
                point = np.array(point) + perturbation
                
                # Project to feasible space
                point = self._project_to_feasible(point)
                recommendations.append(point.tolist())
            
            # If we need more points, generate additional ones
            for i in range(len(base_points), batch_size):
                point = self._generate_seeded_random_combination(self.random_seed + i + 100)
                recommendations.append(point)
                
        else:
            # For smaller batch sizes, use seeded random generation
            for i in range(batch_size):
                point = self._generate_seeded_random_combination(self.random_seed + i)
                recommendations.append(point)
        
        return recommendations
    
    def _generate_seeded_random_combination(self, seed):
        """Generate a random valid combination with a specific seed"""
        rng = np.random.RandomState(seed)
        
        # Generate random values that sum to 1000
        total = 1000
        
        # Method: Generate 2 random cuts in [0, total] and use the segments
        cuts = sorted(rng.uniform(0, total, 2))
        r = cuts[0]
        y = cuts[1] - cuts[0]
        b = total - cuts[1]
        
        point = np.array([r, y, b])
        point = self._project_to_feasible(point)
        
        return point.tolist()


def initialize_campaign(upper_bound, random_seed, random_recs=False):
    """Initialize gradient descent campaign
    
    Args:
        upper_bound: Not used, kept for compatibility
        random_seed: Random seed for reproducibility
        random_recs: Matches BayBE logic:
                     False = Use Sobol-like initialization (BayBE default behavior)
                     True = Use corner points initialization (RandomRecommender)
    """
    logger.info("Initializing Gradient Descent optimization campaign")
    
    # Define bounds for each parameter (0 to 1000 microliters)
    bounds = [(0, 1000), (0, 1000), (0, 1000)]
    
    # Define constraints (sum must equal 1000)
    constraints = {'type': 'eq', 'fun': lambda x: x.sum() - 1000}
    
    # Match BayBE's convention:
    # random_recs=False → Use Sobol-like (default intelligent initialization)
    # random_recs=True → Use corner points (more deterministic)
    use_sobol = not random_recs
    campaign = GradientDescentCampaign(bounds, constraints, random_seed, use_sobol)
    
    if use_sobol:
        logger.info("Using Sobol initialization (space-filling pseudo-random)")
    else:
        logger.info("Using corner points initialization (deterministic)")
    
    # Create dummy searchspace for compatibility
    searchspace = None  # Not used in gradient descent
    
    return campaign, searchspace


def get_initial_recommendations(campaign, size):
    """Get initial batch of recommendations using BayBE initialization for consistency"""
    logger.info(f"Getting initial batch of {size} recommendations from BayBE for consistency")
    
    # Import BayBE components to get identical initialization
    sys.path.append(r"C:\Users\owenm\anaconda3\Lib\site-packages")
    from baybe.targets import NumericalTarget, TargetMode
    from baybe.objectives import SingleTargetObjective
    from baybe import Campaign
    from baybe.parameters import NumericalDiscreteParameter
    from baybe.searchspace import SearchSpace
    from baybe.constraints import DiscreteSumConstraint, ThresholdCondition
    from baybe.utils.random import set_random_seed
    from baybe.recommenders import RandomRecommender
    
    # Create a temporary BayBE campaign with same settings
    set_random_seed(campaign.random_seed)
    
    target = NumericalTarget(name='output', mode=TargetMode.MIN, bounds=(0, 50))
    objective = SingleTargetObjective(target=target)
    
    parameters = [
        NumericalDiscreteParameter(name='R', values=np.array(range(0, 1000, 50))),
        NumericalDiscreteParameter(name='Y', values=np.array(range(0, 1000, 50))),
        NumericalDiscreteParameter(name='B', values=np.array(range(0, 1000, 50))),
    ]
    
    constraints = [DiscreteSumConstraint(
        parameters=["R", "Y", "B"],
        condition=ThresholdCondition(threshold=1000, operator="=")
    )]
    
    searchspace = SearchSpace.from_product(parameters=parameters, constraints=constraints)
    
    if campaign.use_sobol:
        baybe_campaign = Campaign(searchspace, objective)
    else:
        recommender = RandomRecommender()
        baybe_campaign = Campaign(searchspace, objective, recommender)
    
    # Get BayBE recommendations
    initial_suggestions = baybe_campaign.recommend(batch_size=size)
    
    # Store these in the gradient campaign for consistency
    campaign.set_initial_recommendations(initial_suggestions)
    
    return campaign, initial_suggestions


def get_new_recs_from_results(campaign, data, size):
    """Add results and get new recommendations"""
    logger.info(f"Adding measurements and generating {size} new recommendations")
    campaign.add_measurements(data)
    new_suggestions = campaign.recommend(batch_size=size)
    return campaign, new_suggestions