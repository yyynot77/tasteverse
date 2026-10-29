import {
  useRef,
  useState,
  type FormEvent,
} from 'react';

import { sendDialogue } from '../api/client';
import type {
  DialogueResponse,
  DialogueTurn,
  GameState,
} from '../api/types';
import {
  emptyDialogueLog,
  type DialogueLogEntry,
  type NpcDialogueLog,
} from '../game/dialogueLog';
import { NPC_BY_ID } from '../game/npcs';
import type { NpcInteraction } from '../game/types';
import ErrorNotice from './ErrorNotice';

interface DialoguePanelProps {
  interaction: NpcInteraction;
  gameState: GameState;
  stateToken: string;
  log: NpcDialogueLog | undefined;
  onLogChange: (npcId: NpcInteraction['npcId'], log: NpcDialogueLog) => void;
  onStateUpdate: (state: GameState, stateToken: string) => void;
  onClose: () => void;
  onRestart: () => void;
}

interface DialogueAttempt {
  message: string;
  conversation: DialogueTurn[];
}

function EvidenceBlock({
  evidence,
}: {
  evidence: DialogueResponse['evidence'];
}) {
  return (
    <div className="mt-3 border-t-2 border-ink/15 pt-2">
      <p className="font-mono text-[10px] font-bold uppercase tracking-[0.16em] text-moss">
        Real Qloo evidence · {evidence.length}
      </p>
      {evidence.length === 0 ? (
        <p className="mt-1 text-xs leading-5 text-ink/55">
          No verified Qloo entity was returned for this turn. NPC prose is not
          evidence.
        </p>
      ) : (
        <ul className="mt-2 space-y-1.5">
          {evidence.map((item) => (
            <li
              key={item.entity_id}
              className="border-l-2 border-moss/60 bg-moss/5 px-2 py-1.5"
            >
              <p className="text-xs font-bold">
                {item.label || 'Unlabelled Qloo entity'}
              </p>
              <p className="mt-0.5 break-all font-mono text-[10px] text-ink/50">
                {item.query_type || 'qloo'} · {item.entity_id}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function DialogueEntryView({ entry }: { entry: DialogueLogEntry }) {
  if (entry.role === 'user') {
    return (
      <div className="ml-8 border-r-2 border-tomato/50 pr-3 text-right">
        <p className="font-mono text-[9px] font-bold uppercase tracking-[0.16em] text-tomato">
          You
        </p>
        <p className="mt-1 text-sm leading-6">{entry.content}</p>
      </div>
    );
  }

  return (
    <div className="mr-3 border-l-2 border-moss/50 pl-3">
      <p className="font-mono text-[9px] font-bold uppercase tracking-[0.16em] text-moss">
        Resident
      </p>
      <p className="mt-1 text-sm leading-6">{entry.content}</p>
      {entry.transition ? (
        <p className="mt-2 inline-block border border-ink/20 bg-mustard/15 px-2 py-1 font-mono text-[10px] font-bold uppercase tracking-wide">
          {entry.transition.applied
            ? `Rapport ${entry.transition.relationship_before} → ${entry.transition.relationship_after}`
            : 'Already recorded · no extra rapport'}
          {entry.transition.stage_after !== entry.transition.stage_before
            ? ` · stage: ${entry.transition.stage_after}`
            : ''}
        </p>
      ) : null}
      <EvidenceBlock evidence={entry.evidence} />
    </div>
  );
}

function DialoguePanel({
  interaction,
  gameState,
  stateToken,
  log,
  onLogChange,
  onStateUpdate,
  onClose,
  onRestart,
}: DialoguePanelProps) {
  const npc = NPC_BY_ID[interaction.npcId];
  const currentLog = log ?? emptyDialogueLog();
  const [message, setMessage] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [lastAttempt, setLastAttempt] = useState<DialogueAttempt | null>(null);
  const sequence = useRef(currentLog.entries.length);

  const runAttempt = async (attempt: DialogueAttempt) => {
    setPending(true);
    setError(null);

    try {
      const response = await sendDialogue(
        interaction.npcId,
        gameState,
        stateToken,
        attempt.message,
        attempt.conversation,
      );

      const turns =
        response.conversation.length > 0
          ? response.conversation
          : [
              ...attempt.conversation,
              { role: 'user' as const, content: attempt.message },
              { role: 'assistant' as const, content: response.reply },
            ];

      sequence.current += 1;
      const userEntry: DialogueLogEntry = {
        id: `${interaction.npcId}-user-${sequence.current}`,
        role: 'user',
        content: attempt.message,
        evidence: [],
      };
      sequence.current += 1;
      const replyEntry: DialogueLogEntry = {
        id: `${interaction.npcId}-reply-${sequence.current}`,
        role: 'assistant',
        content: response.reply,
        evidence: response.evidence,
        transition: response.transition,
      };

      onStateUpdate(response.state, response.state_token);
      onLogChange(interaction.npcId, {
        entries: [...currentLog.entries, userEntry, replyEntry],
        turns,
      });
      setMessage('');
      setLastAttempt(null);
    } catch (requestError) {
      setError(requestError);
    } finally {
      setPending(false);
    }
  };

  const submitMessage = () => {
    const trimmed = message.trim();

    if (!trimmed || pending) {
      return;
    }

    const attempt: DialogueAttempt = {
      message: trimmed,
      conversation: currentLog.turns.slice(-8),
    };

    setLastAttempt(attempt);
    void runAttempt(attempt);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    submitMessage();
  };

  const metCount = gameState.interacted_npcs.length;
  const hasMetNpc = gameState.interacted_npcs.includes(interaction.npcId);

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-ink/55 p-2 backdrop-blur-[2px] sm:absolute sm:inset-0 sm:z-30 sm:items-center sm:p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="npc-dialog-title"
        aria-describedby="npc-dialog-description"
        className="paper-panel flex max-h-full w-full max-w-lg flex-col overflow-hidden p-0"
      >
        <div className="flex items-start justify-between gap-3 border-b-2 border-ink bg-paper-light px-4 py-3 sm:px-5">
          <div>
            <p className="font-mono text-[9px] font-bold uppercase tracking-[0.2em] text-tomato">
              {npc.role} · {hasMetNpc ? 'met' : 'not yet met'} · {metCount}/3
              residents
            </p>
            <h2
              id="npc-dialog-title"
              className="mt-0.5 font-display text-2xl font-bold leading-tight"
            >
              {interaction.npcName}
            </h2>
            <p
              id="npc-dialog-description"
              className="mt-1 max-w-sm text-xs leading-5 text-ink/65"
            >
              Ask about their corner of the festival. Real Qloo evidence will
              appear separately from their reply.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="min-h-10 shrink-0 border-2 border-ink bg-paper px-2.5 py-1.5 font-mono text-[10px] font-bold uppercase tracking-wider shadow-[2px_2px_0_#2b2620] transition hover:bg-mustard focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-tomato"
          >
            Close
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4 sm:px-5">
          {currentLog.entries.length === 0 ? (
            <div className="border-l-4 border-mustard bg-mustard/10 px-3 py-3">
              <p className="font-mono text-[9px] font-bold uppercase tracking-[0.16em] text-mustard-dark">
                The first page
              </p>
              <p className="mt-1 text-sm leading-6">{npc.greeting}</p>
            </div>
          ) : (
            <div className="space-y-5">
              {currentLog.entries.map((entry) => (
                <DialogueEntryView key={entry.id} entry={entry} />
              ))}
            </div>
          )}

          {pending ? (
            <p
              role="status"
              className="mt-4 flex items-center gap-2 font-mono text-[11px] font-bold uppercase tracking-wider text-ink/60"
            >
              <span className="h-2 w-2 animate-pulse rounded-full bg-moss" />
              {interaction.npcName} is thinking…
            </p>
          ) : null}

          {error ? (
            <div className="mt-4">
              <ErrorNotice
                error={error}
                context="dialogue"
                onRetry={
                  lastAttempt
                    ? () => void runAttempt(lastAttempt)
                    : undefined
                }
                onRestart={onRestart}
              />
            </div>
          ) : null}
        </div>

        <form
          onSubmit={handleSubmit}
          className="border-t-2 border-ink bg-paper-light px-4 py-3 sm:px-5"
        >
          <label
            htmlFor={`dialogue-${interaction.npcId}`}
            className="font-mono text-[10px] font-bold uppercase tracking-[0.16em]"
          >
            Say something to {interaction.npcName}
          </label>
          <div className="mt-1 flex gap-2">
            <input
              id={`dialogue-${interaction.npcId}`}
              type="text"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              maxLength={500}
              autoFocus
              autoComplete="off"
              placeholder="Ask what they would put on the festival bill…"
              className="journal-input min-w-0 flex-1"
            />
            <button
              type="submit"
              disabled={pending || message.trim().length === 0}
              className="shrink-0 border-2 border-ink bg-tomato px-3 py-2 font-mono text-[11px] font-bold uppercase tracking-wider text-paper-light shadow-[3px_3px_0_#2b2620] transition hover:bg-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-tomato disabled:cursor-not-allowed disabled:opacity-50"
            >
              Send
            </button>
          </div>
          <div className="mt-2 flex items-center justify-between gap-2">
            <p className="text-[10px] text-ink/50">
              Press Escape or Close to return to the square.
            </p>
            <span className="font-mono text-[10px] text-ink/40">
              {message.length}/500
            </span>
          </div>
        </form>
      </div>
    </div>
  );
}

export default DialoguePanel;
