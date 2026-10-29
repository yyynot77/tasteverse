/**
 * Wire types for the TasteVerse backend.
 *
 * These mirror the Pydantic models in `backend/app/models` exactly. They are
 * intentionally kept as plain types: the backend owns validation and signed
 * state, while the frontend only renders and forwards these values.
 */

import type { NpcId } from '../game/types';

export type GameStage = 'explore' | 'plan' | 'complete';
export type PlanComponent = 'movie' | 'music' | 'food';
export type Ending = 'perfect_harmony' | 'mixed_night' | 'cultural_chaos';
export type EvidenceStatus = 'available' | 'partial' | 'unavailable';
export type InterpretationStatus = 'not_needed' | 'applied' | 'fallback';

export interface PlayerInterests {
  movies: string[];
  music: string[];
  food: string[];
}

export interface NpcRelationships {
  mara: number;
  jun: number;
  theo: number;
}

export interface Clue {
  clue_id: string;
  npc_id: NpcId;
  text: string;
  tags: string[];
}

export interface Plan {
  movie: string;
  music: string;
  food: string;
  free_text: string;
}

export interface CulturalMatches {
  movies: number | null;
  music: number | null;
  food: number | null;
}

export interface GameState {
  player_interests: PlayerInterests;
  session_id: string;
  state_version: number;
  stage: GameStage;
  relationships: NpcRelationships;
  clues: Clue[];
  interacted_npcs: NpcId[];
  applied_event_ids: string[];
  plan: Plan | null;
  cultural_matches: CulturalMatches | null;
  score: number | null;
  ending: Ending | null;
}

export interface StartGameResponse {
  state: GameState;
  state_token: string;
}

export interface DialogueTurn {
  role: 'user' | 'assistant';
  content: string;
}

export interface DialogueEvidence {
  source: 'qloo';
  entity_id: string;
  label: string;
  query_type: string;
  signal: number | null;
}

export type ToolStatus = 'ok' | 'empty' | 'error' | 'rejected';

export interface DialogueToolTrace {
  tool: string;
  status: ToolStatus;
  result_count: number;
  error_code: string | null;
}

export interface DialogueTransition {
  npc_id: NpcId;
  applied: boolean;
  relationship_before: number;
  relationship_after: number;
  stage_before: GameStage;
  stage_after: GameStage;
  reasons: string[];
}

export interface DialogueResponse {
  reply: string;
  evidence: DialogueEvidence[];
  tool_trace: DialogueToolTrace[];
  tool_calls_executed: number;
  transition: DialogueTransition;
  state: GameState;
  state_token: string;
  conversation: DialogueTurn[];
}

export interface CulturalEvidence {
  source: 'qloo';
  entity_id: string | null;
  tag_id: string | null;
  label: string;
  query_type: string;
  component: PlanComponent;
  npc_id: NpcId;
  signal: number | null;
}

export interface PlanComponentScore {
  component: PlanComponent;
  plan_value: string;
  evidence_count: number;
  evidence_available: boolean;
  score: number;
  npc_ids: NpcId[];
  reasons: string[];
}

export interface PlanNpcScore {
  npc_id: NpcId;
  relationship: number;
  clue_count: number;
  evidence_count: number;
  score: number;
  reasons: string[];
}

export interface NpcReaction {
  npc_id: NpcId;
  name: string;
  relationship: number;
  npc_score: number;
  reaction: string;
}

export interface PlanEvaluateResponse {
  analysis: string;
  evidence: CulturalEvidence[];
  evidence_status: EvidenceStatus;
  interpretation_status: InterpretationStatus;
  components: PlanComponentScore[];
  npcs: PlanNpcScore[];
  reactions: NpcReaction[];
  reasons: string[];
  score: number;
  ending: Ending;
  state: GameState;
  state_token: string;
}

export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    retryable: boolean;
  };
}
