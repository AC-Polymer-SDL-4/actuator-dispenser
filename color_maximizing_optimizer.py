import sys
sys.path.append(r"C:\Users\owenm\anaconda3\Lib\site-packages")
from baybe.targets import NumericalTarget, TargetMode, TargetTransformation
from baybe.objectives import SingleTargetObjective
from baybe import Campaign
from baybe.parameters import NumericalDiscreteParameter, NumericalContinuousParameter
from baybe.searchspace import SearchSpace
import numpy as np
from baybe.constraints import DiscreteSumConstraint, ThresholdCondition
from baybe.utils.random import set_random_seed
from baybe.recommenders import RandomRecommender

def initialize_campaign(upper_bound, random_seed, random_recs=False):
    set_random_seed(random_seed) 

    target = NumericalTarget(
        name='output',
        mode=TargetMode.MAX,  # MAXIMIZE color difference instead of minimize
        bounds=(0, upper_bound),
    )

    objective = SingleTargetObjective(target=target)#

    # Components that can be varied (excluding fixed metal salt)
    # Total volume constraint: HCl + citric_acid + ascorbic_acid + PVA1 + PVA2 + PVA3 + NaOH + Water = 800 uL
    # (since 200 uL is fixed metal salt, remaining is 800 uL to reach 1000 uL total)
    
    parameters = [
        NumericalDiscreteParameter(
            name='HCl',
            values=np.array(range(50, 401, 50))  # 50-400 uL in 50 uL steps
        ),
        NumericalDiscreteParameter(
            name='citric_acid',
            values=np.array(range(50, 401, 50))  # 50-400 uL in 50 uL steps
        ),
        NumericalDiscreteParameter(
            name='ascorbic_acid',
            values=np.array(range(50, 401, 50))  # 50-400 uL in 50 uL steps
        ),
        NumericalDiscreteParameter(
            name='PVA_1',
            values=np.array(range(50, 401, 50))  # 50-400 uL in 50 uL steps
        ),
        NumericalDiscreteParameter(
            name='PVA_2',
            values=np.array(range(50, 401, 50))  # 50-400 uL in 50 uL steps
        ),
        NumericalDiscreteParameter(
            name='PVA_3',
            values=np.array(range(50, 401, 50))  # 50-400 uL in 50 uL steps
        ),
        NumericalDiscreteParameter(
            name='NaOH',
            values=np.array(range(50, 401, 50))  # 50-400 uL in 50 uL steps
        ),
        NumericalDiscreteParameter(
            name='Water',
            values=np.array(range(50, 801, 50))  # 50-400 uL in 50 uL steps
        ),
    ]

    # Constraint: all components must sum to exactly 800 uL (to get 1000 uL total with 200 uL metal salt)
    constraints = [DiscreteSumConstraint(
            parameters=["HCl", "citric_acid", "ascorbic_acid", "PVA_1", "PVA_2", "PVA_3", "NaOH", "Water"],
            condition=ThresholdCondition(
                threshold=800,
                operator="="))]

    searchspace = SearchSpace.from_product(parameters=parameters, constraints=constraints)
    
    if not random_recs:
        campaign = Campaign(searchspace, objective)
    else:
        recommender = RandomRecommender()
        campaign = Campaign(searchspace, objective, recommender)
    return campaign, searchspace

def get_initial_recommendations(campaign, size):
    initial_suggestions = campaign.recommend(batch_size=size)
    return campaign, initial_suggestions

def get_new_recs_from_results(campaign, data, size):
    campaign.add_measurements(data)
    new_suggestions = campaign.recommend(batch_size=size)
    return campaign, new_suggestions