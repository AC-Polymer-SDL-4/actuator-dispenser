"""
Convex Optimization for Color Matching

Uses convex optimization techniques (CVXPY) to find optimal color mixing ratios.
Assumes the color space forms a convex set and uses convex hull analysis.
Maintains the same interface as the BayBE optimizer for easy integration.
"""

import numpy as np
import pandas as pd
import logging
from scipy.spatial import ConvexHull
import cvxpy as cp
from scipy.optimize import linprog

logger = logging.getLogger(__name__)

class ConvexOptimizationCampaign:
    def __init__(self, random_seed=42):
        self.random_seed = random_seed
        self.results_data = []
        self.convex_hull_points = None
        self.color_targets = {}  # Store target RGB values
        np.random.seed(random_seed)
        
    def set_target_color(self, target_rgb):
        """Set the target color for optimization"""
        self.target_rgb = np.array(target_rgb)
        logger.info(f"Target color set to RGB: {target_rgb}")
    
    def recommend(self, batch_size=1):
        """Generate recommendations using convex optimization"""
        recommendations = []
        
        if len(self.results_data) < 4:
            # Need at least 4 points to form initial convex hull
            logger.info("Generating initial random recommendations for convex hull")
            for _ in range(batch_size):
                rec = self._generate_corner_point()
                recommendations.append(rec)
        else:
            # Use convex optimization
            logger.info("Using convex optimization for recommendations")
            
            # Update convex hull with current data
            self._update_convex_hull()
            
            for i in range(batch_size):
                if i == 0:
                    # First recommendation: solve convex optimization problem
                    rec = self._solve_convex_problem()
                else:
                    # Additional recommendations: explore boundary
                    rec = self._explore_convex_boundary()
                
                recommendations.append(rec)
        
        # Convert to DataFrame format
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
        """Add experimental results"""
        logger.info(f"Adding {len(measurements_df)} measurements to convex model")
        
        for _, row in measurements_df.iterrows():
            result = {
                'R': row['R'],
                'Y': row['Y'], 
                'B': row['B'],
                'Water': row.get('Water', 0),
                'output': row['output'],
                'rgb_achieved': row.get('rgb_achieved', None)  # Actual RGB values achieved
            }
            self.results_data.append(result)
    
    def _generate_corner_point(self):
        """Generate corner points of the feasible region for initial sampling"""
        corners = [
            [1000, 0, 0],    # Pure R
            [0, 1000, 0],    # Pure Y  
            [0, 0, 1000],    # Pure B
            [500, 500, 0],   # R+Y mix
            [500, 0, 500],   # R+B mix
            [0, 500, 500],   # Y+B mix
            [333, 333, 334], # Equal mix
        ]
        
        # Return a random corner with some noise
        base_corner = corners[np.random.randint(len(corners))]
        
        # Add small random perturbation
        noise = np.random.normal(0, 50, 3)
        perturbed = np.array(base_corner) + noise
        
        # Project to feasible space
        perturbed = np.maximum(0, perturbed)
        perturbed = np.minimum(1000, perturbed)
        
        # Normalize to sum to 1000
        if perturbed.sum() > 0:
            perturbed = perturbed * (1000 / perturbed.sum())
        
        # Round to nearest 50
        perturbed = np.round(perturbed / 50) * 50
        
        return perturbed.astype(int).tolist()
    
    def _update_convex_hull(self):
        """Update convex hull based on current experimental data"""
        if len(self.results_data) < 4:
            return
            
        # Extract points in parameter space (R, Y, B)
        points = []
        for result in self.results_data:
            points.append([result['R'], result['Y'], result['B']])
        
        points = np.array(points)
        
        try:
            # Compute convex hull in 3D parameter space
            hull = ConvexHull(points)
            self.convex_hull_points = points[hull.vertices]
            logger.info(f"Updated convex hull with {len(self.convex_hull_points)} vertices")
        except Exception as e:
            logger.warning(f"Could not compute convex hull: {e}")
            self.convex_hull_points = points
    
    def _solve_convex_problem(self):
        """Solve convex optimization problem to minimize color difference"""
        
        try:
            # Define optimization variables
            x = cp.Variable(3, name="RGB_volumes")  # R, Y, B volumes
            
            # If we have RGB data, use it for better modeling
            if len(self.results_data) > 0 and any('rgb_achieved' in result and result['rgb_achieved'] is not None for result in self.results_data):
                return self._solve_rgb_convex_problem(x)
            else:
                return self._solve_surrogate_convex_problem(x)
                
        except Exception as e:
            logger.warning(f"Convex optimization failed: {e}, falling back to linear programming")
            return self._solve_linear_approximation()
    
    def _solve_rgb_convex_problem(self, x):
        """Solve when we have actual RGB color data"""
        
        # Build linear model: RGB_color = A * x + b
        # where x = [R_vol, Y_vol, B_vol] and RGB_color = [R, G, B] values
        
        volumes = []
        colors = []
        
        for result in self.results_data:
            if 'rgb_achieved' in result and result['rgb_achieved'] is not None:
                volumes.append([result['R'], result['Y'], result['B']])
                colors.append(result['rgb_achieved'])
        
        if len(volumes) < 3:
            # Not enough data for linear model
            return self._solve_surrogate_convex_problem(x)
        
        volumes = np.array(volumes)
        colors = np.array(colors)
        
        # Fit linear model RGB = A * volumes
        # Use least squares: A = (volumes^T * volumes)^(-1) * volumes^T * colors
        try:
            A = np.linalg.lstsq(volumes, colors, rcond=None)[0]
            
            # Predicted RGB for our mixture
            predicted_rgb = A.T @ x  # Shape: (3,)
            
            # Objective: minimize Euclidean distance to target
            if hasattr(self, 'target_rgb'):
                objective = cp.Minimize(cp.norm(predicted_rgb - self.target_rgb, 2))
            else:
                # If no target set, minimize total color intensity (go towards neutral)
                objective = cp.Minimize(cp.norm(predicted_rgb, 2))
            
            # Constraints
            constraints = [
                x >= 0,           # Non-negative volumes
                x <= 1000,        # Maximum volume bounds
                cp.sum(x) == 1000  # Total volume constraint
            ]
            
            # Solve
            problem = cp.Problem(objective, constraints)
            problem.solve(solver=cp.ECOS)
            
            if problem.status == cp.OPTIMAL:
                solution = x.value
                solution = np.round(solution / 50) * 50  # Round to discrete values
                return solution.astype(int).tolist()
            else:
                logger.warning(f"Convex problem not optimal: {problem.status}")
                return self._solve_surrogate_convex_problem(x)
                
        except Exception as e:
            logger.warning(f"RGB convex optimization failed: {e}")
            return self._solve_surrogate_convex_problem(x)
    
    def _solve_surrogate_convex_problem(self, x):
        """Solve using surrogate model of color difference"""
        
        # Build quadratic surrogate model from existing data
        volumes = np.array([[r['R'], r['Y'], r['B']] for r in self.results_data])
        scores = np.array([r['output'] for r in self.results_data])
        
        if len(volumes) < 3:
            return self._generate_corner_point()
        
        try:
            # Fit quadratic model: score = x^T Q x + c^T x + d
            # For simplicity, use quadratic form with current best point
            best_idx = np.argmin(scores)
            best_point = volumes[best_idx]
            
            # Objective: minimize distance from best known point (convex)
            objective = cp.Minimize(cp.norm(x - best_point, 2))
            
            # Constraints
            constraints = [
                x >= 0,
                x <= 1000,
                cp.sum(x) == 1000
            ]
            
            problem = cp.Problem(objective, constraints)
            problem.solve(solver=cp.ECOS)
            
            if problem.status == cp.OPTIMAL:
                solution = x.value
                solution = np.round(solution / 50) * 50
                return solution.astype(int).tolist()
            else:
                return self._solve_linear_approximation()
                
        except Exception as e:
            logger.warning(f"Surrogate convex optimization failed: {e}")
            return self._solve_linear_approximation()
    
    def _solve_linear_approximation(self):
        """Fallback to linear programming approximation"""
        
        if len(self.results_data) == 0:
            return self._generate_corner_point()
        
        # Find best known point and return nearby point
        scores = [r['output'] for r in self.results_data]
        best_idx = np.argmin(scores)
        best_result = self.results_data[best_idx]
        
        # Generate point near best with linear programming
        best_point = np.array([best_result['R'], best_result['Y'], best_result['B']])
        
        # Add small perturbation
        perturbation = np.random.normal(0, 25, 3)
        new_point = best_point + perturbation
        
        # Project to feasible space
        new_point = np.maximum(0, new_point)
        new_point = np.minimum(1000, new_point)
        
        # Normalize to sum to 1000
        if new_point.sum() > 0:
            new_point = new_point * (1000 / new_point.sum())
        
        # Round to discrete values
        new_point = np.round(new_point / 50) * 50
        
        return new_point.astype(int).tolist()
    
    def _explore_convex_boundary(self):
        """Explore the boundary of the convex hull"""
        
        if self.convex_hull_points is None or len(self.convex_hull_points) < 3:
            return self._generate_corner_point()
        
        # Generate random convex combination of hull vertices
        n_vertices = len(self.convex_hull_points)
        weights = np.random.dirichlet(np.ones(n_vertices))
        
        # Convex combination
        new_point = np.zeros(3)
        for i, weight in enumerate(weights):
            new_point += weight * self.convex_hull_points[i]
        
        # Round to discrete values
        new_point = np.round(new_point / 50) * 50
        
        # Ensure constraints
        new_point = np.maximum(0, new_point)
        if new_point.sum() > 0:
            new_point = new_point * (1000 / new_point.sum())
        
        return new_point.astype(int).tolist()


def initialize_campaign(upper_bound, random_seed, random_recs=False):
    """Initialize convex optimization campaign"""
    logger.info("Initializing Convex Optimization campaign")
    
    campaign = ConvexOptimizationCampaign(random_seed)
    
    # Create dummy searchspace for compatibility
    searchspace = None
    
    return campaign, searchspace


def get_initial_recommendations(campaign, size):
    """Get initial batch of recommendations"""
    logger.info(f"Generating initial batch of {size} recommendations using convex optimization")
    initial_suggestions = campaign.recommend(batch_size=size)
    return campaign, initial_suggestions


def get_new_recs_from_results(campaign, data, size):
    """Add results and get new recommendations"""
    logger.info(f"Adding measurements and generating {size} new recommendations")
    campaign.add_measurements(data)
    new_suggestions = campaign.recommend(batch_size=size)
    return campaign, new_suggestions