from itertools import combinations
from pathlib import Path

import numpy as np

from simulation.population.excel_repository import ExcelTraitRepository
from simulation.population.generator import generate_population
from simulation.product.fit import consumer_product_fit
from simulation.product.knowledge import ProductKnowledge
from simulation.product.semantic_profile import build_product_semantic_profile


TRAIT_ROOT = Path("data/traits")


def _product(name: str, category: str, pitch: str, price: float) -> ProductKnowledge:
    return ProductKnowledge(name=name, category=category, pitch=pitch, price=price, currency="INR")


PRODUCTS = {
    "education": _product("Tutor", "Education Technology", "Adaptive tutoring and study planning.", 499),
    "business_saas": _product("WorkSuite", "Business Productivity SaaS", "Project automation for work teams.", 899),
    "vpn": _product("VPN", "Cybersecurity Subscription", "Privacy and network security service.", 299),
    "meal": _product("Meal", "Food and Meal Planning Software", "Meal planning and grocery automation.", 499),
    "fitness": _product("Fitness", "Fitness Technology", "Workout planning and progress tracking.", 299),
    "fragrance": _product("Fragrance", "Luxury Fragrance", "Premium eau de parfum.", 4499),
    "earbuds": _product("Earbuds", "Consumer Audio Electronics", "Wireless earbuds for everyday audio.", 5999),
    "robot": _product("Robot", "Home Appliance Robotics", "Robot vacuum for household cleaning.", 17999),
}


def _need(agent, product: ProductKnowledge, seed: int = 1701) -> float:
    profile = build_product_semantic_profile(product)
    return consumer_product_fit(agent, product, profile, seed=seed).need


def test_same_population_need_is_not_a_universal_appetite_across_unrelated_categories():
    agents = generate_population(1000, seed=1701, traits=ExcelTraitRepository(TRAIT_ROOT))
    vectors = {
        name: np.asarray([_need(agent, product) for agent in agents], dtype=float)
        for name, product in PRODUCTS.items()
    }
    correlations = [
        float(np.corrcoef(vectors[a], vectors[b])[0, 1])
        for a, b in combinations(vectors, 2)
    ]

    assert float(np.mean(correlations)) < 0.60


def test_students_and_education_workers_have_higher_tutoring_need_than_unrelated_workers():
    agents = generate_population(1600, seed=1702, traits=ExcelTraitRepository(TRAIT_ROOT))
    needs = [(agent, _need(agent, PRODUCTS["education"], seed=1702)) for agent in agents]
    relevant = [value for agent, value in needs if agent.context.occupation.key in {"student", "education"}]
    unrelated = [
        value
        for agent, value in needs
        if agent.context.occupation.key in {"retail_operations", "skilled_trade", "healthcare"}
    ]

    assert relevant and unrelated
    assert float(np.mean(relevant)) > float(np.mean(unrelated)) + 0.08


def test_business_technology_and_entrepreneur_contexts_need_business_saas_more_than_students():
    agents = generate_population(1600, seed=1703, traits=ExcelTraitRepository(TRAIT_ROOT))
    needs = [(agent, _need(agent, PRODUCTS["business_saas"], seed=1703)) for agent in agents]
    relevant = [
        value
        for agent, value in needs
        if agent.context.occupation.key in {"business_services", "software_tech", "entrepreneur"}
    ]
    students = [value for agent, value in needs if agent.context.occupation.key == "student"]

    assert relevant and students
    assert float(np.mean(relevant)) > float(np.mean(students)) + 0.10


def test_family_time_pressure_and_convenience_raise_meal_planning_need():
    agents = generate_population(2200, seed=1704, traits=ExcelTraitRepository(TRAIT_ROOT))
    needs = [(agent, _need(agent, PRODUCTS["meal"], seed=1704)) for agent in agents]
    high_context = [
        value
        for agent, value in needs
        if "family" in agent.context.demographic.household_tendency.lower()
        and agent.context.occupation.time_pressure >= 0.70
        and agent.context.behaviour.convenience_preference >= 0.65
    ]
    low_context = [
        value
        for agent, value in needs
        if "single" in agent.context.demographic.household_tendency.lower()
        and agent.context.occupation.time_pressure <= 0.65
        and agent.context.behaviour.convenience_preference <= 0.60
    ]

    assert len(high_context) >= 20
    assert len(low_context) >= 20
    assert float(np.mean(high_context)) > float(np.mean(low_context)) + 0.10
