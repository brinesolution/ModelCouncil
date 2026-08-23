from simulation.conversation.discussion_policy import discussion_turn_novelty


def test_later_turns_have_diminishing_but_nonzero_novelty():
    values = [discussion_turn_novelty(index) for index in range(8)]

    assert values[0] == 1.0
    assert values == sorted(values, reverse=True)
    assert values[-1] >= 0.45
    assert values[1] < values[0]
