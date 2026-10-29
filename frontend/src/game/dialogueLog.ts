import type {
  DialogueEvidence,
  DialogueTransition,
  DialogueTurn,
} from '../api/types';
import type { NpcId } from './types';

export interface DialogueLogEntry {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  evidence: DialogueEvidence[];
  transition?: DialogueTransition;
}

export interface NpcDialogueLog {
  entries: DialogueLogEntry[];
  /** Bounded server-returned history, safe to send as the next request context. */
  turns: DialogueTurn[];
}

export type DialogueLogs = Partial<Record<NpcId, NpcDialogueLog>>;

export function emptyDialogueLog(): NpcDialogueLog {
  return { entries: [], turns: [] };
}
