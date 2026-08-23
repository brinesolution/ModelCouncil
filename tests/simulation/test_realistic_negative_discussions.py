from pathlib import Path

from simulation.engine import SimulationConfig, SimulationEngine
from simulation.population.excel_repository import ExcelTraitRepository
from simulation.population.generator import generate_population
from simulation.product.knowledge import ProductKnowledge


TRAIT_ROOT = Path("data/traits")


def _run(product: ProductKnowledge, *, seed: int = 42, size: int = 260, rounds: int = 2):
    population = generate_population(
        size,
        seed=seed,
        traits=ExcelTraitRepository(TRAIT_ROOT),
    )
    return SimulationEngine().run(
        product,
        population,
        SimulationConfig(
            rounds=rounds,
            seed=seed,
            k=10,
            max_conversations_per_agent=2,
            initiator_rate=0.25,
            weak_tie_rate=0.08,
        ),
    )


def test_realistic_finance_subscription_has_skeptics_and_non_buyers_without_quota():
    result = _run(
        ProductKnowledge(
            name="LedgerWise Budget AI",
            category="Personal Finance Software",
            pitch=(
                "Budgeting service that connects bank accounts, processes transaction history and financial records, "
                "stores spending data, has a monthly subscription, requires an account, uses encryption, supports "
                "self-service deletion, and does not use transaction data for advertising. Automatic categorization "
                "can be imperfect and setup can be complex."
            ),
            price=399,
            currency="INR",
            billing_cadence="monthly",
        )
    )

    opinions = [agent.state.overall_opinion for agent in result.population]
    purchase = [agent.state.purchase_intent for agent in result.population]

    assert sum(value < 0.0 for value in opinions) / len(opinions) >= 0.08
    assert sum(value < 0.35 for value in purchase) / len(purchase) >= 0.04
    assert all(4 <= len(entry.result.messages) <= 8 for entry in result.conversations)


def test_bad_product_discussions_plainly_include_pass_or_no_buy_language():
    result = _run(
        ProductKnowledge(
            name="VoltRush X20",
            category="Portable Power Bank",
            pitch=(
                "Power bank with unreliable measured capacity, inconsistent charging, excessive heat, overheating, "
                "vague battery certification, sealed battery, not repairable, difficult returns, slow customer support, "
                "warranty exclusions, and misleading claims."
            ),
            price=2999,
            currency="INR",
            billing_cadence="one_time",
        ),
        seed=17,
        size=120,
        rounds=1,
    )

    visible = " ".join(
        str(turn["text"]).lower()
        for entry in result.conversations
        for turn in entry.result.transcript
    )
    assert any(
        phrase in visible
        for phrase in (
            "would not buy",
            "would pass",
            "not buying",
            "walk away",
            "likely to pass",
            "hold off",
        )
    )
