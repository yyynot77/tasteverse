/** Shared game types used by the Phaser scene and the React UI. */

export type NpcId = 'mara' | 'jun' | 'theo';

/** Payload emitted by Phaser when the player talks to a nearby NPC. */
export interface NpcInteraction {
  npcId: NpcId;
  npcName: string;
}

export interface Vector2 {
  x: number;
  y: number;
}

export interface NpcColors {
  skin: number;
  hair: number;
  outfit: number;
  accent: number;
}

export type NpcLook = 'apron' | 'cap' | 'scarf';

export interface NpcDefinition {
  readonly id: NpcId;
  readonly name: string;
  readonly role: string;
  readonly greeting: string;
  readonly x: number;
  readonly y: number;
  readonly look: NpcLook;
  readonly colors: NpcColors;
}
