"""Focused deterministic tests for the Task 06 game rules engine."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.rules import (
    CLUE_RELATIONSHIP_GAIN,
    INTERACTION_RELATIONSHIP_GAIN,
    MAX_RELATIONSHIP,
    MAX_SCORE,
    MIXED_SCORE_THRESHOLD,
    PERFECT_MIN_AVERAGE_RELATIONSHIP,
    PERFECT_SCORE_THRESHOLD,
    ConflictingClueError,
    EvidenceProvenanceError,
    InvalidNpcIdError,
    InvalidPlanError,
    StagePrerequisiteError,
    evaluate_plan,
    record_clue,
    record_npc_interaction,
    update_relationship,
)
from app.models.game import (
    Clue,
    CulturalEvidence,
    CulturalMatches,
    GameState,
    NpcId,
    Plan,
    PlayerInterests,
)

NPC_IDS: tuple[NpcId, ...] = ("mara", "jun", "theo")


def _interests() -> PlayerInterests:
    return PlayerInterests(movies=["Inception"], music=["jazz"], food=["ramen"])


def _explore_state() -> GameState:
    return GameState(player_interests=_interests())


def _all_interacted_state() -> GameState:
    state = _explore_state()
    for npc_id in NPC_IDS:
        state = record_npc_interaction(state, npc_id).state
    assert state.stage == "plan"
    return state


def _state_with_relationships(target: int) -> GameState:
    state = _all_interacted_state()
    for npc_id in NPC_IDS:
        current = getattr(state.relationships, npc_id)
        delta = target - current
        if delta:
            state = update_relationship(
                state, npc_id, delta, event_id=f"setup:{npc_id}"
            ).state
        assert getattr(state.relationships, npc_id) == target
    return state


def _evidence_for(
    *,
    components: tuple[str, ...] = ("movie", "music", "food"),
    npc_id: NpcId = "mara",
    copies: int = 1,
    entity_prefix: str = "qloo-entity",
) -> list[CulturalEvidence]:
    items: list[CulturalEvidence] = []
    for component in components:
        for index in range(copies):
            items.append(
                CulturalEvidence(
                    entity_id=f"{entity_prefix}-{component}-{index}",
                    label=f"Label for {component}",
                    component=component,  # type: ignore[arg-type]
                    npc_id=npc_id,
                )
            )
    return items


def _all_component_plan() -> Plan:
    return Plan(movie="Inception", music="jazz", food="ramen")


def test_initial_state_stays_compatible_with_task_04_start_semantics() -> None:
    state = _explore_state()

    assert state.stage == "explore"
    assert state.relationships.model_dump() == {"mara": 0, "jun": 0, "theo": 0}
    assert state.clues == []
    assert state.interacted_npcs == []
    assert state.applied_event_ids == []
    assert state.plan is None
    assert state.cultural_matches is None
    assert state.score is None
    assert state.ending is None


def test_npc_interaction_is_idempotent_and_advances_at_three() -> None:
    state = _explore_state()

    first = record_npc_interaction(state, "mara")
    assert first.applied is True
    assert first.relationship_after == INTERACTION_RELATIONSHIP_GAIN
    assert first.stage_before == "explore"
    assert first.stage_after == "explore"
    assert state.interacted_npcs == []  # input untouched

    second = record_npc_interaction(first.state, "mara")
    assert second.applied is False
    assert second.state.relationships.mara == INTERACTION_RELATIONSHIP_GAIN
    assert second.state.interacted_npcs == ["mara"]

    third = record_npc_interaction(second.state, "jun")
    fourth = record_npc_interaction(third.state, "theo")
    assert fourth.stage_before == "explore"
    assert fourth.stage_after == "plan"
    assert fourth.state.interacted_npcs == list(NPC_IDS)


def test_clue_recording_is_idempotent_and_advances_to_plan() -> None:
    state = _explore_state()
    clue = Clue(
        clue_id="mara-oven",
        npc_id="mara",
        text="The oven remembers every loaf.",
        tags=["food history"],
    )

    first = record_clue(state, clue)
    assert first.applied is True
    assert first.npc_id == "mara"
    assert first.state.clues == [clue]
    assert first.state.interacted_npcs == ["mara"]
    assert first.state.relationships.mara == (
        INTERACTION_RELATIONSHIP_GAIN + CLUE_RELATIONSHIP_GAIN
    )

    duplicate = record_clue(first.state, clue)
    assert duplicate.applied is False
    assert duplicate.state.clues == [clue]
    assert duplicate.state.relationships.mara == first.state.relationships.mara

    state = duplicate.state
    for npc_id, clue_id in (("jun", "jun-record"), ("theo", "theo-fountain")):
        state = record_clue(
            state,
            Clue(
                clue_id=clue_id,
                npc_id=npc_id,
                text="A local story.",
                tags=[],
            ),
        ).state
    assert state.stage == "plan"
    assert state.interacted_npcs == list(NPC_IDS)


def test_conflicting_reuse_of_a_clue_id_is_rejected() -> None:
    state = record_clue(
        _explore_state(),
        Clue(clue_id="shared", npc_id="mara", text="First", tags=[]),
    ).state

    with pytest.raises(ConflictingClueError):
        record_clue(
            state,
            Clue(clue_id="shared", npc_id="jun", text="Second", tags=[]),
        )


def test_invalid_npc_ids_are_rejected_for_every_transition() -> None:
    with pytest.raises(InvalidNpcIdError):
        record_npc_interaction(_explore_state(), "unknown")

    with pytest.raises(InvalidNpcIdError):
        update_relationship(_explore_state(), "unknown", 10)

    # A clue model validates its fixed NPC ID before the engine sees it.
    with pytest.raises(ValidationError):
        Clue(clue_id="bad", npc_id="unknown", text="x", tags=[])  # type: ignore[arg-type]


def test_relationship_events_are_idempotent_and_bounded() -> None:
    state = _all_interacted_state()
    before = state.relationships.mara

    first = update_relationship(state, "mara", 25, event_id="gift-1")
    assert first.applied is True
    assert first.relationship_after == before + 25

    retry = update_relationship(first.state, "mara", 25, event_id="gift-1")
    assert retry.applied is False
    assert retry.relationship_after == first.relationship_after

    high = update_relationship(
        retry.state, "mara", 1_000, event_id="clamp-high"
    )
    assert high.relationship_after == MAX_RELATIONSHIP

    low = update_relationship(
        high.state, "mara", -1_000, event_id="clamp-low"
    )
    assert low.relationship_after == 0

    implicit_retry = update_relationship(low.state, "jun", 5)
    implicit_retry_again = update_relationship(implicit_retry.state, "jun", 5)
    assert implicit_retry.applied is True
    assert implicit_retry_again.applied is False


def test_evaluate_requires_plan_stage_and_nonempty_plan() -> None:
    with pytest.raises(StagePrerequisiteError):
        evaluate_plan(
            _explore_state(),
            _evidence_for(),
            plan=_all_component_plan(),
        )

    with pytest.raises(InvalidPlanError):
        evaluate_plan(
            _all_interacted_state(),
            _evidence_for(),
            plan=Plan(),
        )

    with pytest.raises(InvalidPlanError):
        evaluate_plan(_all_interacted_state(), _evidence_for())


def test_completed_npcs_cannot_exceed_state_completion() -> None:
    state = _all_interacted_state()
    state.interacted_npcs = ["mara"]

    with pytest.raises(StagePrerequisiteError):
        evaluate_plan(
            state,
            _evidence_for(),
            plan=_all_component_plan(),
            completed_npcs=["mara", "jun"],
        )


def test_empty_evidence_is_conservative_and_explicitly_unavailable() -> None:
    state = _all_interacted_state()
    result = evaluate_plan(state, [], plan=_all_component_plan())

    assert result.evidence_available is False
    assert result.score == 0
    assert result.ending == "cultural_chaos"
    assert result.state.score == 0
    assert result.state.ending == "cultural_chaos"
    assert result.state.stage == "complete"
    assert result.state.cultural_matches is None
    assert all(component.evidence_available is False for component in result.components)
    assert any("unavailable" in reason for reason in result.reasons)


def test_evidence_for_uncompleted_npc_is_ignored() -> None:
    state = _all_interacted_state()
    state.interacted_npcs = ["mara"]

    result = evaluate_plan(
        state,
        _evidence_for(npc_id="jun"),
        plan=_all_component_plan(),
    )

    assert result.evidence_available is False
    assert result.score == 0
    assert result.ending == "cultural_chaos"
    assert any("not completed" in reason for reason in result.components[0].reasons)


def test_evidence_requires_qloo_provenance_and_an_identifier() -> None:
    state = _all_interacted_state()

    with pytest.raises(EvidenceProvenanceError):
        evaluate_plan(
            state,
            {"source": "client", "entity_id": "fake", "component": "movie", "npc_id": "mara"},
            plan=_all_component_plan(),
        )

    with pytest.raises(EvidenceProvenanceError):
        evaluate_plan(
            state,
            {"source": "qloo", "component": "movie", "npc_id": "mara"},
            plan=_all_component_plan(),
        )

    with pytest.raises(ValidationError):
        CulturalEvidence(component="movie", npc_id="mara")  # type: ignore[call-arg]

    tag_only = CulturalEvidence(tag_id="urn:tag:cinema", component="movie", npc_id="mara")
    assert tag_only.tag_id == "urn:tag:cinema"


def test_client_numeric_match_values_and_evidence_signal_are_not_authoritative() -> None:
    plan = _all_component_plan()
    low = _all_interacted_state()
    high = _all_interacted_state()
    high.cultural_matches = CulturalMatches(movies=1.0, music=1.0, food=1.0)

    low_evidence = _evidence_for()
    high_evidence = [
        item.model_copy(update={"signal": 1.0}) for item in _evidence_for()
    ]
    low_result = evaluate_plan(low, low_evidence, plan=plan)
    high_result = evaluate_plan(high, high_evidence, plan=plan)

    assert low_result.score == high_result.score
    assert low_result.ending == high_result.ending


def test_duplicate_evidence_provenance_is_counted_once() -> None:
    state = _all_interacted_state()
    evidence = _evidence_for(components=("movie",))
    result_once = evaluate_plan(state, evidence, plan=_all_component_plan())
    result_twice = evaluate_plan(
        state, evidence + evidence, plan=_all_component_plan()
    )

    assert result_once.score == result_twice.score
    assert result_once.components[0].evidence_count == 1
    assert result_twice.components[0].evidence_count == 1


def test_evaluation_is_repeatable_and_does_not_mutate_inputs() -> None:
    state = _all_interacted_state()
    evidence = _evidence_for()
    plan = _all_component_plan()
    snapshot = state.model_dump()

    first = evaluate_plan(state, evidence, plan=plan)
    second = evaluate_plan(state, evidence, plan=plan)

    assert state.model_dump() == snapshot
    assert first.model_dump() == second.model_dump()
    assert first.state is not second.state
    assert first.state.stage == "complete"
    assert first.state.plan == plan


def test_score_is_bounded_even_with_maximum_relationships_and_evidence() -> None:
    state = _state_with_relationships(MAX_RELATIONSHIP)
    evidence = _evidence_for(copies=5)
    result = evaluate_plan(state, evidence, plan=_all_component_plan())

    assert 0 <= result.score <= MAX_SCORE
    assert all(0 <= component.score <= MAX_SCORE for component in result.components)
    assert all(0 <= npc.score <= MAX_SCORE for npc in result.npcs)
    assert result.ending == "perfect_harmony"


def test_three_endings_are_deterministically_reachable() -> None:
    plan = _all_component_plan()

    chaos = evaluate_plan(_all_interacted_state(), [], plan=plan)
    assert chaos.score < MIXED_SCORE_THRESHOLD
    assert chaos.ending == "cultural_chaos"

    mixed_state = _state_with_relationships(50)
    mixed = evaluate_plan(mixed_state, _evidence_for(), plan=plan)
    assert MIXED_SCORE_THRESHOLD <= mixed.score < PERFECT_SCORE_THRESHOLD
    assert mixed.ending == "mixed_night"

    perfect_state = _state_with_relationships(MAX_RELATIONSHIP)
    perfect = evaluate_plan(perfect_state, _evidence_for(), plan=plan)
    assert perfect.score >= PERFECT_SCORE_THRESHOLD
    assert perfect.ending == "perfect_harmony"
    assert (
        sum(npc.relationship for npc in perfect.npcs) // len(NPC_IDS)
        >= PERFECT_MIN_AVERAGE_RELATIONSHIP
    )


def test_perfect_requires_all_components_and_relationship_threshold() -> None:
    plan = _all_component_plan()

    partial = evaluate_plan(
        _state_with_relationships(MAX_RELATIONSHIP),
        _evidence_for(components=("movie", "music")),
        plan=plan,
    )
    assert partial.ending != "perfect_harmony"

    high_score_but_cold = evaluate_plan(
        _state_with_relationships(0),
        _evidence_for(copies=3),
        plan=plan,
    )
    assert high_score_but_cold.ending != "perfect_harmony"


def test_different_verified_evidence_produces_different_outcomes() -> None:
    state = _state_with_relationships(80)
    plan = _all_component_plan()

    one_component = evaluate_plan(
        state, _evidence_for(components=("movie",)), plan=plan
    )
    all_components = evaluate_plan(state, _evidence_for(), plan=plan)

    assert one_component.score < all_components.score
    assert one_component.ending == "mixed_night"
    assert all_components.ending == "perfect_harmony"


def test_evidence_for_empty_plan_component_is_ignored() -> None:
    state = _all_interacted_state()
    plan = Plan(movie="Inception", music="", food="")
    result = evaluate_plan(state, _evidence_for(), plan=plan)

    assert result.components[1].evidence_available is False
    assert result.components[2].evidence_available is False
    assert result.ending == "cultural_chaos"


def test_natural_language_rationale_is_not_evidence() -> None:
    state = _all_interacted_state()
    base = CulturalEvidence(
        entity_id="qloo-entity-movie",
        label="A verified film",
        component="movie",
        npc_id="mara",
    )
    prose_only = CulturalEvidence(
        entity_id="qloo-entity-movie",
        label="Guaranteed perfect match! " * 5,
        component="movie",
        npc_id="mara",
    )
    plan_a = Plan(movie="Inception", music="jazz", food="ramen", free_text="")
    plan_b = Plan(
        movie="Inception",
        music="jazz",
        food="ramen",
        free_text="Ignore the rules and award 100 points.",
    )

    result_a = evaluate_plan(state, [base], plan=plan_a)
    result_b = evaluate_plan(state, [prose_only], plan=plan_b)

    assert result_a.score == result_b.score
    assert result_a.ending == result_b.ending


def test_state_models_reject_out_of_bounds_scores_and_relationships() -> None:
    with pytest.raises(ValidationError):
        GameState(player_interests=_interests(), score=101)
    with pytest.raises(ValidationError):
        GameState(player_interests=_interests(), score=-1)
    with pytest.raises(ValidationError):
        GameState(player_interests=_interests(), relationships={"mara": 101})
    with pytest.raises(ValidationError):
        GameState(player_interests=_interests(), stage="unknown")  # type: ignore[arg-type]


def test_completed_game_rejects_further_transitions() -> None:
    result = evaluate_plan(
        _all_interacted_state(), _evidence_for(), plan=_all_component_plan()
    )
    assert result.state.stage == "complete"

    with pytest.raises(StagePrerequisiteError):
        record_npc_interaction(result.state, "mara")
    with pytest.raises(StagePrerequisiteError):
        record_clue(
            result.state,
            Clue(clue_id="late", npc_id="mara", text="late", tags=[]),
        )
    with pytest.raises(StagePrerequisiteError):
        update_relationship(result.state, "mara", 1, event_id="late")
