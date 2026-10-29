"""Deterministic, side-effect-free game rules for TasteVerse.

The engine is deliberately small and explicit:

* :func:`record_npc_interaction` records that the player met an NPC.
* :func:`record_clue` records a clue and its owning NPC.
* :func:`update_relationship` applies one relationship event.
* :func:`evaluate_plan` scores a submitted plan from verified Qloo evidence.

Every function accepts a :class:`~app.models.game.GameState` and returns a typed
transition containing a new state. Inputs are never mutated. No randomness,
wall-clock time, LLM output, natural-language rationale, or client-supplied
numeric match value can change a score. Only structural provenance (a Qloo
entity/tag ID linked to a plan component and NPC), completion state, and the
server-owned relationships contribute.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.models.game import (
    Clue,
    CulturalEvidence,
    CulturalMatches,
    Ending,
    GameState,
    GameStage,
    NpcId,
    Plan,
    PlanComponent,
)

# ---------------------------------------------------------------------------
# Public constants. Keeping them named and module-level makes the thresholds
# auditable and lets tests assert on the same values the engine uses.
# ---------------------------------------------------------------------------

NPC_IDS: Final[tuple[NpcId, ...]] = ("mara", "jun", "theo")
PLAN_COMPONENTS: Final[tuple[PlanComponent, ...]] = ("movie", "music", "food")
GAME_STAGES: Final[tuple[GameStage, ...]] = ("explore", "plan", "complete")

PERFECT_HARMONY: Final[Ending] = "perfect_harmony"
MIXED_NIGHT: Final[Ending] = "mixed_night"
CULTURAL_CHAOS: Final[Ending] = "cultural_chaos"
ENDINGS: Final[tuple[Ending, ...]] = (
    PERFECT_HARMONY,
    MIXED_NIGHT,
    CULTURAL_CHAOS,
)

MIN_RELATIONSHIP: Final[int] = 0
MAX_RELATIONSHIP: Final[int] = 100
MIN_SCORE: Final[int] = 0
MAX_SCORE: Final[int] = 100

INTERACTION_RELATIONSHIP_GAIN: Final[int] = 8
CLUE_RELATIONSHIP_GAIN: Final[int] = 10

# Component score = base + depth bonus + relationship bonus.
COMPONENT_BASE_SCORE: Final[int] = 55
COMPONENT_EXTRA_EVIDENCE_BONUS: Final[int] = 10
MAX_COUNTED_EVIDENCE_PER_COMPONENT: Final[int] = 3
COMPONENT_RELATIONSHIP_MAX_BONUS: Final[int] = 20

# Overall score weights must sum to 100.
COMPONENT_WEIGHT: Final[int] = 65
RELATIONSHIP_WEIGHT: Final[int] = 25
COMPLETION_WEIGHT: Final[int] = 10
WEIGHT_TOTAL: Final[int] = (
    COMPONENT_WEIGHT + RELATIONSHIP_WEIGHT + COMPLETION_WEIGHT
)
ROUNDING_OFFSET: Final[int] = WEIGHT_TOTAL // 2

# Exactly three stable endings are selected from these transparent rules.
PERFECT_SCORE_THRESHOLD: Final[int] = 75
PERFECT_MIN_AVERAGE_RELATIONSHIP: Final[int] = 50
MIXED_SCORE_THRESHOLD: Final[int] = 40

# NPC score is relationship plus bounded interaction evidence.
CLUE_NPC_SCORE_WEIGHT: Final[int] = 5
EVIDENCE_NPC_SCORE_WEIGHT: Final[int] = 5
MAX_NPC_CLUES_COUNTED: Final[int] = 5
MAX_NPC_EVIDENCE_COUNTED: Final[int] = 5


# ---------------------------------------------------------------------------
# Typed errors
# ---------------------------------------------------------------------------


class RulesError(ValueError):
    """Base error for a rejected deterministic transition."""

    code: str = "rules_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code

    def to_dict(self) -> dict[str, Any]:
        """Return a safe error shape suitable for an API envelope."""

        return {"code": self.code, "message": str(self)}


class InvalidNpcIdError(RulesError):
    """Raised when a transition names an NPC outside the fixed cast."""

    code = "invalid_npc_id"


class StagePrerequisiteError(RulesError):
    """Raised when an action is not legal in the current stage."""

    code = "stage_prerequisite"


class ConflictingClueError(RulesError):
    """Raised when a clue ID is reused with different clue contents."""

    code = "conflicting_clue"


class InvalidPlanError(RulesError):
    """Raised when a plan cannot be scored."""

    code = "invalid_plan"


class EvidenceProvenanceError(RulesError):
    """Raised when evidence is not a structured, provenance-bearing item."""

    code = "evidence_provenance"


# ---------------------------------------------------------------------------
# Transition result models
# ---------------------------------------------------------------------------


class _TransitionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClueTransition(_TransitionModel):
    """Typed result of recording one clue."""

    state: GameState
    clue_id: str
    npc_id: NpcId
    applied: bool
    relationship_before: int
    relationship_after: int
    stage_before: GameStage
    stage_after: GameStage
    reasons: list[str] = Field(default_factory=list)


class InteractionTransition(_TransitionModel):
    """Typed result of recording one NPC interaction."""

    state: GameState
    npc_id: NpcId
    applied: bool
    relationship_before: int
    relationship_after: int
    stage_before: GameStage
    stage_after: GameStage
    reasons: list[str] = Field(default_factory=list)


class RelationshipTransition(_TransitionModel):
    """Typed result of applying one relationship event."""

    state: GameState
    npc_id: NpcId
    event_id: str
    applied: bool
    delta: int
    relationship_before: int
    relationship_after: int
    reasons: list[str] = Field(default_factory=list)


class ComponentScore(_TransitionModel):
    """Explainable score for one movie/music/food plan component."""

    component: PlanComponent
    plan_value: str
    evidence_count: int = Field(ge=0)
    evidence_available: bool
    score: int = Field(ge=MIN_SCORE, le=MAX_SCORE)
    npc_ids: list[NpcId] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class NpcScore(_TransitionModel):
    """Explainable score and evidence summary for one NPC."""

    npc_id: NpcId
    relationship: int = Field(ge=MIN_RELATIONSHIP, le=MAX_RELATIONSHIP)
    clue_count: int = Field(ge=0)
    evidence_count: int = Field(ge=0)
    score: int = Field(ge=MIN_SCORE, le=MAX_SCORE)
    reasons: list[str] = Field(default_factory=list)


class PlanEvaluationTransition(_TransitionModel):
    """Typed result of evaluating a submitted plan and selecting an ending."""

    state: GameState
    score: int = Field(ge=MIN_SCORE, le=MAX_SCORE)
    ending: Ending
    evidence_available: bool
    components: list[ComponentScore]
    npcs: list[NpcScore]
    reasons: list[str] = Field(default_factory=list)


# Friendly aliases for callers that prefer result/outcome naming.
ClueRecordResult = ClueTransition
InteractionResult = InteractionTransition
RelationshipResult = RelationshipTransition
PlanEvaluationResult = PlanEvaluationTransition
PlanEvaluation = PlanEvaluationTransition


# ---------------------------------------------------------------------------
# Small pure helpers
# ---------------------------------------------------------------------------


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _state_copy(state: GameState) -> GameState:
    if not isinstance(state, GameState):
        raise RulesError("state must be a GameState.")
    return state.model_copy(deep=True)


def _validate_npc_id(npc_id: str) -> NpcId:
    if not isinstance(npc_id, str) or npc_id not in NPC_IDS:
        raise InvalidNpcIdError(f"Unknown NPC id: {npc_id!r}.")
    return npc_id  # type: ignore[return-value]


def _validate_event_id(event_id: str | None) -> str | None:
    if event_id is None:
        return None
    if not isinstance(event_id, str) or not event_id.strip():
        raise RulesError("event_id must be a non-empty string.")
    return event_id.strip()


def _require_active(state: GameState) -> None:
    if state.stage == "complete":
        raise StagePrerequisiteError(
            "The game is complete; no further transitions are allowed."
        )


def _append_event(state: GameState, event_id: str) -> None:
    if event_id not in state.applied_event_ids:
        state.applied_event_ids.append(event_id)


def _bump_state_version(state: GameState) -> None:
    """Record that a real transition occurred for signed-envelope freshness."""

    state.state_version += 1


def _advance_to_plan_when_ready(state: GameState) -> None:
    if state.stage == "explore" and set(NPC_IDS).issubset(state.interacted_npcs):
        state.stage = "plan"


def _get_relationship(state: GameState, npc_id: NpcId) -> int:
    return int(getattr(state.relationships, npc_id))


def _set_relationship(state: GameState, npc_id: NpcId, value: int) -> None:
    bounded = _clamp(value, MIN_RELATIONSHIP, MAX_RELATIONSHIP)
    setattr(state.relationships, npc_id, bounded)


def _coerce_clue(clue: Clue | Mapping[str, Any]) -> Clue:
    if isinstance(clue, Clue):
        return clue.model_copy(deep=True)
    if isinstance(clue, Mapping):
        try:
            return Clue.model_validate(clue)
        except ValidationError as exc:
            raise RulesError("Clue is invalid.", code="invalid_clue") from exc
    raise RulesError("clue must be a Clue or mapping.", code="invalid_clue")


def _coerce_plan(plan: Plan | Mapping[str, Any] | None) -> Plan:
    if isinstance(plan, Plan):
        return plan.model_copy(deep=True)
    if isinstance(plan, Mapping):
        try:
            return Plan.model_validate(plan)
        except ValidationError as exc:
            raise InvalidPlanError("Plan is invalid.") from exc
    if plan is None:
        raise InvalidPlanError("A plan is required before evaluation.")
    raise InvalidPlanError("plan must be a Plan or mapping.")


def _coerce_evidence(item: Any) -> CulturalEvidence:
    if isinstance(item, CulturalEvidence):
        return item
    if isinstance(item, Mapping):
        try:
            return CulturalEvidence.model_validate(item)
        except ValidationError as exc:
            raise EvidenceProvenanceError(
                "Evidence must be a Qloo entity/tag linked to a plan component "
                "and NPC."
            ) from exc
    raise EvidenceProvenanceError(
        "Evidence must be a structured CulturalEvidence item."
    )


def _normalise_evidence(
    evidence: Sequence[CulturalEvidence | Mapping[str, Any]] | None,
) -> list[CulturalEvidence]:
    if evidence is None:
        return []
    if isinstance(evidence, (CulturalEvidence, Mapping)):
        raw_items: list[Any] = [evidence]
    elif isinstance(evidence, Sequence) and not isinstance(
        evidence, (str, bytes, bytearray)
    ):
        raw_items = list(evidence)
    else:
        raise EvidenceProvenanceError("evidence must be a sequence of items.")

    normalised: list[CulturalEvidence] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for raw in raw_items:
        item = _coerce_evidence(raw)
        source = item.source
        entity_id = (item.entity_id or "").strip()
        tag_id = (item.tag_id or "").strip()
        if source != "qloo" or (not entity_id and not tag_id):
            raise EvidenceProvenanceError(
                "Evidence requires Qloo provenance and a non-empty entity/tag ID."
            )
        key = (source, entity_id, tag_id, item.component, item.npc_id)
        if key in seen:
            continue
        seen.add(key)
        normalised.append(item)
    return normalised


def _completion_set(
    state: GameState, completed_npcs: Sequence[str] | None
) -> set[NpcId]:
    state_completed = set(state.interacted_npcs)
    if completed_npcs is None:
        return state_completed

    if isinstance(completed_npcs, (str, bytes, bytearray)):
        raise RulesError("completed_npcs must be a sequence of NPC ids.")

    supplied: set[NpcId] = set()
    for value in completed_npcs:
        supplied.add(_validate_npc_id(value))
    if not supplied.issubset(state_completed):
        raise StagePrerequisiteError(
            "Completed NPCs must already be recorded in the game state."
        )
    return supplied


def _relationship_average(relationships: dict[NpcId, int]) -> int:
    total = sum(relationships[npc_id] for npc_id in NPC_IDS)
    return total // len(NPC_IDS)


def determine_ending(
    *,
    score: int,
    relationship_average: int,
    all_components_evidenced: bool,
) -> Ending:
    """Select one of the three stable endings from transparent thresholds."""

    bounded_score = _clamp(int(score), MIN_SCORE, MAX_SCORE)
    bounded_relationship = _clamp(
        int(relationship_average), MIN_RELATIONSHIP, MAX_RELATIONSHIP
    )
    if (
        bounded_score >= PERFECT_SCORE_THRESHOLD
        and bounded_relationship >= PERFECT_MIN_AVERAGE_RELATIONSHIP
        and all_components_evidenced
    ):
        return "perfect_harmony"
    if bounded_score >= MIXED_SCORE_THRESHOLD:
        return "mixed_night"
    return "cultural_chaos"


# ---------------------------------------------------------------------------
# Transitions
# ---------------------------------------------------------------------------


def record_npc_interaction(
    state: GameState,
    npc_id: str,
    *,
    event_id: str | None = None,
) -> InteractionTransition:
    """Record that the player interacted with one fixed NPC.

    The interaction is idempotent per NPC: a second call never counts the
    relationship gain twice. Meeting all three NPCs advances ``explore`` to
    ``plan``. A supplied ``event_id`` is also checked for idempotence.
    """

    next_state = _state_copy(state)
    validated_npc = _validate_npc_id(npc_id)
    _require_active(next_state)
    event_key = _validate_event_id(event_id) or f"interaction:{validated_npc}"

    before = _get_relationship(next_state, validated_npc)
    stage_before = next_state.stage
    reasons: list[str] = []

    if validated_npc in next_state.interacted_npcs:
        reasons.append(
            f"{validated_npc} interaction was already recorded; no gain applied."
        )
        return InteractionTransition(
            state=next_state,
            npc_id=validated_npc,
            applied=False,
            relationship_before=before,
            relationship_after=before,
            stage_before=stage_before,
            stage_after=next_state.stage,
            reasons=reasons,
        )

    if event_key in next_state.applied_event_ids:
        reasons.append(
            f"Event {event_key!r} was already applied; no gain applied."
        )
        return InteractionTransition(
            state=next_state,
            npc_id=validated_npc,
            applied=False,
            relationship_before=before,
            relationship_after=before,
            stage_before=stage_before,
            stage_after=next_state.stage,
            reasons=reasons,
        )

    _append_event(next_state, event_key)
    next_state.interacted_npcs.append(validated_npc)
    _set_relationship(
        next_state,
        validated_npc,
        before + INTERACTION_RELATIONSHIP_GAIN,
    )
    after = _get_relationship(next_state, validated_npc)
    _bump_state_version(next_state)
    _advance_to_plan_when_ready(next_state)
    reasons.append(
        f"Recorded interaction with {validated_npc}; relationship "
        f"{before} -> {after}."
    )
    if next_state.stage != stage_before:
        reasons.append(f"Stage advanced from {stage_before} to {next_state.stage}.")

    return InteractionTransition(
        state=next_state,
        npc_id=validated_npc,
        applied=True,
        relationship_before=before,
        relationship_after=after,
        stage_before=stage_before,
        stage_after=next_state.stage,
        reasons=reasons,
    )


# Descriptive aliases used by dialogue/API code in later tasks.
record_interacted_npc = record_npc_interaction
record_interaction = record_npc_interaction
interact_with_npc = record_npc_interaction
mark_npc_interacted = record_npc_interaction


def record_clue(
    state: GameState,
    clue: Clue | Mapping[str, Any],
    *,
    event_id: str | None = None,
) -> ClueTransition:
    """Record one NPC-owned clue exactly once.

    Duplicate identical clue IDs are a no-op. Reusing a clue ID for different
    content is rejected. The first clue for an NPC also marks that NPC as
    interacted and grants the interaction gain, so clue-first and
    interaction-first flows cannot double-count the same discovery.
    """

    next_state = _state_copy(state)
    _require_active(next_state)
    validated_clue = _coerce_clue(clue)
    validated_npc = _validate_npc_id(validated_clue.npc_id)
    event_key = _validate_event_id(event_id) or f"clue:{validated_clue.clue_id}"

    before = _get_relationship(next_state, validated_npc)
    stage_before = next_state.stage
    reasons: list[str] = []

    existing = next(
        (item for item in next_state.clues if item.clue_id == validated_clue.clue_id),
        None,
    )
    if existing is not None:
        if existing == validated_clue:
            reasons.append(
                f"Clue {validated_clue.clue_id!r} was already recorded; "
                "no gain applied."
            )
            return ClueTransition(
                state=next_state,
                clue_id=validated_clue.clue_id,
                npc_id=validated_npc,
                applied=False,
                relationship_before=before,
                relationship_after=before,
                stage_before=stage_before,
                stage_after=next_state.stage,
                reasons=reasons,
            )
        raise ConflictingClueError(
            f"Clue ID {validated_clue.clue_id!r} is already owned by different "
            "content."
        )

    if event_key in next_state.applied_event_ids:
        reasons.append(
            f"Event {event_key!r} was already applied; no gain applied."
        )
        return ClueTransition(
            state=next_state,
            clue_id=validated_clue.clue_id,
            npc_id=validated_npc,
            applied=False,
            relationship_before=before,
            relationship_after=before,
            stage_before=stage_before,
            stage_after=next_state.stage,
            reasons=reasons,
        )

    _append_event(next_state, event_key)
    next_state.clues.append(validated_clue)

    newly_interacted = validated_npc not in next_state.interacted_npcs
    if newly_interacted:
        next_state.interacted_npcs.append(validated_npc)

    gain = CLUE_RELATIONSHIP_GAIN
    if newly_interacted:
        gain += INTERACTION_RELATIONSHIP_GAIN
    _set_relationship(next_state, validated_npc, before + gain)
    after = _get_relationship(next_state, validated_npc)
    _bump_state_version(next_state)
    _advance_to_plan_when_ready(next_state)

    reasons.append(
        f"Recorded clue {validated_clue.clue_id!r} owned by {validated_npc}; "
        f"relationship {before} -> {after}."
    )
    if newly_interacted:
        reasons.append(f"Marked {validated_npc} as interacted.")
    if next_state.stage != stage_before:
        reasons.append(f"Stage advanced from {stage_before} to {next_state.stage}.")

    return ClueTransition(
        state=next_state,
        clue_id=validated_clue.clue_id,
        npc_id=validated_npc,
        applied=True,
        relationship_before=before,
        relationship_after=after,
        stage_before=stage_before,
        stage_after=next_state.stage,
        reasons=reasons,
    )


def update_relationship(
    state: GameState,
    npc_id: str,
    delta: int,
    *,
    event_id: str | None = None,
) -> RelationshipTransition:
    """Apply one bounded relationship event to one NPC.

    Supplying a stable ``event_id`` makes the event idempotent: the same event
    can be retried after a network failure without counting twice. If omitted,
    a deterministic ``relationship:<npc>:<delta>`` key is used, so retrying the
    same change is also safe.
    """

    next_state = _state_copy(state)
    validated_npc = _validate_npc_id(npc_id)
    _require_active(next_state)
    if isinstance(delta, bool) or not isinstance(delta, int):
        raise RulesError("delta must be an integer.", code="invalid_delta")
    event_key = _validate_event_id(event_id) or (
        f"relationship:{validated_npc}:{delta}"
    )

    before = _get_relationship(next_state, validated_npc)
    if event_key in next_state.applied_event_ids:
        return RelationshipTransition(
            state=next_state,
            npc_id=validated_npc,
            event_id=event_key,
            applied=False,
            delta=delta,
            relationship_before=before,
            relationship_after=before,
            reasons=[
                f"Event {event_key!r} was already applied; no gain applied."
            ],
        )

    _append_event(next_state, event_key)
    _set_relationship(next_state, validated_npc, before + delta)
    after = _get_relationship(next_state, validated_npc)
    _bump_state_version(next_state)
    reasons = [
        f"Applied relationship event {event_key!r} to {validated_npc}; "
        f"relationship {before} -> {after}."
    ]
    if after == before and delta != 0:
        reasons.append("Relationship was clamped at its 0-100 bound.")

    return RelationshipTransition(
        state=next_state,
        npc_id=validated_npc,
        event_id=event_key,
        applied=True,
        delta=delta,
        relationship_before=before,
        relationship_after=after,
        reasons=reasons,
    )


# Descriptive alias for event-driven callers.
record_relationship_change = update_relationship


def evaluate_plan(
    state: GameState,
    evidence: Sequence[CulturalEvidence | Mapping[str, Any]] | None,
    *,
    plan: Plan | Mapping[str, Any] | None = None,
    completed_npcs: Sequence[str] | None = None,
) -> PlanEvaluationTransition:
    """Evaluate a submitted plan from verified evidence and completion state.

    Preconditions:
    * the state is in the ``plan`` stage;
    * a plan with at least one non-empty component is supplied (or already in
      state);
    * evidence items are structured Qloo provenance records.

    Evidence for a component with no plan selection, or for an NPC that has not
    been completed, is ignored and explained. If no usable evidence remains the
    score is conservatively zero and ``evidence_available`` is false; the engine
    never invents a Qloo success. Numeric ``signal`` values, labels, free text,
    and ``state.cultural_matches`` are display data and never scoring inputs.
    """

    next_state = _state_copy(state)
    if next_state.stage != "plan":
        raise StagePrerequisiteError(
            "Plan evaluation requires stage 'plan'; "
            f"current stage is {next_state.stage!r}."
        )

    submitted_plan = _coerce_plan(plan if plan is not None else next_state.plan)
    if not any(
        getattr(submitted_plan, component).strip()
        for component in PLAN_COMPONENTS
    ):
        raise InvalidPlanError("Plan must contain at least one non-empty component.")

    evidence_items = _normalise_evidence(evidence)
    completed = _completion_set(next_state, completed_npcs)
    relationships = {
        npc_id: _get_relationship(next_state, npc_id) for npc_id in NPC_IDS
    }

    components: list[ComponentScore] = []
    usable_by_component: dict[PlanComponent, list[CulturalEvidence]] = {
        component: [] for component in PLAN_COMPONENTS
    }

    for component in PLAN_COMPONENTS:
        plan_value = getattr(submitted_plan, component).strip()
        component_reasons: list[str] = []
        matching = [
            item for item in evidence_items if item.component == component
        ]

        if not plan_value:
            component_reasons.append(
                f"{component}: no plan selection; component scores 0."
            )
            components.append(
                ComponentScore(
                    component=component,
                    plan_value="",
                    evidence_count=0,
                    evidence_available=False,
                    score=0,
                    npc_ids=[],
                    reasons=component_reasons,
                )
            )
            continue

        usable: list[CulturalEvidence] = []
        for item in matching:
            if item.npc_id not in completed:
                component_reasons.append(
                    f"{component}: ignored Qloo evidence for {item.npc_id} "
                    "because that NPC is not completed."
                )
                continue
            usable.append(item)
            usable_by_component[component].append(item)

        if not usable:
            component_reasons.append(
                f"{component}: verified Qloo evidence unavailable; "
                "component scores 0."
            )
            components.append(
                ComponentScore(
                    component=component,
                    plan_value=plan_value,
                    evidence_count=0,
                    evidence_available=False,
                    score=0,
                    npc_ids=[],
                    reasons=component_reasons,
                )
            )
            continue

        counted = usable[:MAX_COUNTED_EVIDENCE_PER_COMPONENT]
        linked_npcs: list[NpcId] = []
        for item in counted:
            if item.npc_id not in linked_npcs:
                linked_npcs.append(item.npc_id)
        linked_relationships = [
            relationships[npc_id] for npc_id in linked_npcs
        ]
        linked_average = sum(linked_relationships) // len(linked_relationships)
        relationship_bonus = (
            linked_average * COMPONENT_RELATIONSHIP_MAX_BONUS // MAX_RELATIONSHIP
        )
        depth_bonus = (
            len(counted) - 1
        ) * COMPONENT_EXTRA_EVIDENCE_BONUS
        component_score = _clamp(
            COMPONENT_BASE_SCORE + depth_bonus + relationship_bonus,
            MIN_SCORE,
            MAX_SCORE,
        )
        component_reasons.append(
            f"{component}: {len(counted)} verified Qloo item(s) across "
            f"{len(linked_npcs)} NPC(s); base {COMPONENT_BASE_SCORE} + "
            f"depth {depth_bonus} + relationship {relationship_bonus} "
            f"= {component_score}."
        )
        components.append(
            ComponentScore(
                component=component,
                plan_value=plan_value,
                evidence_count=len(counted),
                evidence_available=True,
                score=component_score,
                npc_ids=linked_npcs,
                reasons=component_reasons,
            )
        )

    evidence_available = any(item.evidence_available for item in components)
    relationship_average = _relationship_average(relationships)
    completion_percent = (
        len(completed.intersection(NPC_IDS)) * MAX_SCORE // len(NPC_IDS)
    )

    if evidence_available:
        component_average = sum(item.score for item in components) // len(
            components
        )
        weighted_total = (
            component_average * COMPONENT_WEIGHT
            + relationship_average * RELATIONSHIP_WEIGHT
            + completion_percent * COMPLETION_WEIGHT
        )
        # Integer, half-up rounding keeps scores deterministic on every platform.
        overall_score = _clamp(
            (weighted_total + ROUNDING_OFFSET) // WEIGHT_TOTAL,
            MIN_SCORE,
            MAX_SCORE,
        )
    else:
        component_average = 0
        overall_score = 0

    all_components_evidenced = all(
        item.evidence_available for item in components
    )
    ending = determine_ending(
        score=overall_score,
        relationship_average=relationship_average,
        all_components_evidenced=all_components_evidenced,
    )

    npc_scores: list[NpcScore] = []
    for npc_id in NPC_IDS:
        clue_count = sum(1 for clue in next_state.clues if clue.npc_id == npc_id)
        evidence_count = sum(
            1
            for component_items in usable_by_component.values()
            for item in component_items
            if item.npc_id == npc_id
        )
        npc_score = _clamp(
            relationships[npc_id]
            + min(clue_count, MAX_NPC_CLUES_COUNTED) * CLUE_NPC_SCORE_WEIGHT
            + min(evidence_count, MAX_NPC_EVIDENCE_COUNTED)
            * EVIDENCE_NPC_SCORE_WEIGHT,
            MIN_SCORE,
            MAX_SCORE,
        )
        npc_scores.append(
            NpcScore(
                npc_id=npc_id,
                relationship=relationships[npc_id],
                clue_count=clue_count,
                evidence_count=evidence_count,
                score=npc_score,
                reasons=[
                    f"{npc_id}: relationship {relationships[npc_id]}/100; "
                    f"{clue_count} clue(s); {evidence_count} usable Qloo "
                    f"evidence item(s); NPC score {npc_score}."
                ],
            )
        )

    reasons: list[str] = [
        "Scores use only verified provenance, completion state, and "
        "server-owned relationships; labels, free text, and numeric signal "
        "values are ignored."
    ]
    if not evidence_available:
        reasons.append(
            "Cultural evidence unavailable; score conservatively set to 0 and "
            "ending selected as cultural_chaos."
        )
    else:
        reasons.append(
            f"Overall score {overall_score} = component average "
            f"{component_average} x {COMPONENT_WEIGHT}% + relationship average "
            f"{relationship_average} x {RELATIONSHIP_WEIGHT}% + completion "
            f"{completion_percent} x {COMPLETION_WEIGHT}%."
        )
    reasons.append(
        f"Ending {ending!r} selected (perfect >= {PERFECT_SCORE_THRESHOLD} "
        f"with relationship average >= {PERFECT_MIN_AVERAGE_RELATIONSHIP} and "
        f"all components evidenced; mixed >= {MIXED_SCORE_THRESHOLD})."
    )

    next_state.plan = submitted_plan
    next_state.score = overall_score
    next_state.ending = ending
    next_state.stage = "complete"
    _bump_state_version(next_state)
    if evidence_available:
        next_state.cultural_matches = CulturalMatches(
            movies=components[0].score / MAX_SCORE,
            music=components[1].score / MAX_SCORE,
            food=components[2].score / MAX_SCORE,
        )
    else:
        next_state.cultural_matches = None

    return PlanEvaluationTransition(
        state=next_state,
        score=overall_score,
        ending=ending,
        evidence_available=evidence_available,
        components=components,
        npcs=npc_scores,
        reasons=reasons,
    )


# Convenience names for later API/dialogue integration.
evaluate_submitted_plan = evaluate_plan
score_plan = evaluate_plan
compute_ending = determine_ending
