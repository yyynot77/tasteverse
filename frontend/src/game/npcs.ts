import type { NpcDefinition, NpcId } from './types';

/**
 * The three fixed town residents. Positions are in scene pixels and each
 * resident has a distinct silhouette, palette, and role so they are easy to
 * tell apart at 960x540.
 */
export const NPCS: readonly NpcDefinition[] = [
  {
    id: 'mara',
    name: 'Mara',
    role: 'Baker',
    greeting:
      'The ovens are still warm. Smell that? Every loaf here starts with a story.',
    x: 178,
    y: 270,
    look: 'apron',
    colors: {
      skin: 0xf1c27d,
      hair: 0x3f2a1d,
      outfit: 0xd97706,
      accent: 0xfff3d6,
    },
  },
  {
    id: 'jun',
    name: 'Jun',
    role: 'Record shop owner',
    greeting:
      'You can learn a lot about a town from the records it keeps. Listen closely.',
    x: 792,
    y: 272,
    look: 'cap',
    colors: {
      skin: 0xd9a066,
      hair: 0x1f2937,
      outfit: 0x0f766e,
      accent: 0x38bdf8,
    },
  },
  {
    id: 'theo',
    name: 'Theo',
    role: 'Town storyteller',
    greeting:
      'Sit by the fountain a while. Every face in this square has a favourite film.',
    x: 480,
    y: 430,
    look: 'scarf',
    colors: {
      skin: 0xe0ac69,
      hair: 0xd6d3d1,
      outfit: 0x6d28d9,
      accent: 0xb45309,
    },
  },
];

export const NPC_BY_ID: Record<NpcId, NpcDefinition> = Object.fromEntries(
  NPCS.map((npc) => [npc.id, npc]),
) as Record<NpcId, NpcDefinition>;
