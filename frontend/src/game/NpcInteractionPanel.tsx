import { NPC_BY_ID } from './npcs';
import type { NpcInteraction } from './types';

interface NpcInteractionPanelProps {
  interaction: NpcInteraction;
  onClose: () => void;
}

function NpcInteractionPanel({
  interaction,
  onClose,
}: NpcInteractionPanelProps) {
  const npc = NPC_BY_ID[interaction.npcId];

  return (
    <div className="absolute inset-0 z-20 flex items-end justify-center bg-slate-950/45 p-4 sm:items-center">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="npc-dialog-title"
        aria-describedby="npc-dialog-description"
        className="w-full max-w-sm rounded-2xl border border-amber-200/30 bg-slate-900/95 p-5 text-left shadow-2xl shadow-black/50 backdrop-blur"
      >
        <p className="text-[10px] font-semibold tracking-[0.2em] text-amber-300 uppercase">
          {npc.role}
        </p>
        <h2
          id="npc-dialog-title"
          className="mt-1 text-2xl font-semibold text-white"
        >
          {interaction.npcName}
        </h2>
        <p
          id="npc-dialog-description"
          className="mt-3 text-sm leading-6 text-slate-300"
        >
          {npc.greeting}
        </p>
        <p className="mt-3 text-xs leading-5 text-slate-500">
          Conversation generation is not part of this task. This panel is the
          typed React–Phaser interaction boundary.
        </p>
        <button
          type="button"
          autoFocus
          onClick={onClose}
          className="mt-5 w-full rounded-xl bg-amber-400 px-4 py-2.5 text-sm font-bold text-slate-950 transition hover:bg-amber-300 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-200"
        >
          Close conversation
        </button>
        <p className="mt-2 text-center text-[10px] text-slate-500">
          Press Escape to close
        </p>
      </div>
    </div>
  );
}

export default NpcInteractionPanel;
