import Phaser from 'phaser';

import { TownEventBridge } from '../events';
import { NPCS } from '../npcs';
import type { NpcDefinition, NpcId, Vector2 } from '../types';
import {
  findNearestNpcInRange,
  movePlayer,
  TOWN_OBSTACLES,
  WORLD_HEIGHT,
  WORLD_WIDTH,
  type Obstacle,
} from '../world';

export const TOWN_SCENE_KEY = 'TownScene';

interface MovementKeys {
  w: Phaser.Input.Keyboard.Key;
  a: Phaser.Input.Keyboard.Key;
  s: Phaser.Input.Keyboard.Key;
  d: Phaser.Input.Keyboard.Key;
  up: Phaser.Input.Keyboard.Key;
  down: Phaser.Input.Keyboard.Key;
  left: Phaser.Input.Keyboard.Key;
  right: Phaser.Input.Keyboard.Key;
  interact: Phaser.Input.Keyboard.Key;
  confirm: Phaser.Input.Keyboard.Key;
}

interface BuildingStyle {
  wall: number;
  roof: number;
  trim: number;
  sign: string;
}

const BUILDING_STYLES: Record<string, BuildingStyle> = {
  bakery: { wall: 0xd9a066, roof: 0x9a3412, trim: 0xfde68a, sign: 'BAKERY' },
  'town-hall': {
    wall: 0xc7b299,
    roof: 0x475569,
    trim: 0xf8fafc,
    sign: 'TOWN HALL',
  },
  'record-shop': {
    wall: 0x6b8f9c,
    roof: 0x164e63,
    trim: 0x7dd3fc,
    sign: 'RECORDS',
  },
};

const PLAYER_START: Vector2 = { x: 480, y: 498 };

/**
 * One coherent, code-drawn pixel town. Movement and collision are pure helpers
 * from `world.ts`; this scene only translates keyboard state into movement and
 * publishes typed interaction events to React.
 */
export class TownScene extends Phaser.Scene {
  readonly bridge: TownEventBridge;

  private playerPosition: Vector2 = { ...PLAYER_START };
  private player!: Phaser.GameObjects.Container;
  private promptText!: Phaser.GameObjects.Text;
  private nearbyMarker!: Phaser.GameObjects.Graphics;
  private keys?: MovementKeys;
  private nearbyNpcId: NpcId | null = null;
  private isPanelOpen = false;
  private facing = 1;
  private unsubscribePanelClosed?: () => void;

  constructor(bridge: TownEventBridge = new TownEventBridge()) {
    super({ key: TOWN_SCENE_KEY });
    this.bridge = bridge;
  }

  create(): void {
    this.cameras.main.setBackgroundColor('#254b34');

    this.drawGround();
    this.drawObstacles();

    for (const npc of NPCS) {
      this.drawNpc(npc);
    }

    this.nearbyMarker = this.add
      .graphics()
      .lineStyle(2, 0xfde68a, 0.95)
      .strokeEllipse(0, 3, 38, 16)
      .setVisible(false);

    this.drawPlayer();
    this.createPrompt();
    this.bindKeyboard();

    this.unsubscribePanelClosed = this.bridge.on(
      'npc:panel-closed',
      this.handlePanelClosed,
    );

    this.events.once(Phaser.Scenes.Events.SHUTDOWN, this.handleShutdown, this);
    // Game.destroy() calls Systems.destroy() directly, which emits DESTROY
    // without a preceding SHUTDOWN. Listen for both so bridge handlers cannot
    // survive an unmount (or a Strict Mode provisional mount).
    this.events.once(Phaser.Scenes.Events.DESTROY, this.handleShutdown, this);
  }

  update(_time: number, delta: number): void {
    const keys = this.keys;

    if (!keys) {
      return;
    }

    const horizontal =
      Number(keys.d.isDown || keys.right.isDown) -
      Number(keys.a.isDown || keys.left.isDown);
    const vertical =
      Number(keys.s.isDown || keys.down.isDown) -
      Number(keys.w.isDown || keys.up.isDown);

    if (!this.isPanelOpen) {
      this.playerPosition = movePlayer(
        this.playerPosition,
        { x: horizontal, y: vertical },
        delta / 1000,
      );

      if (horizontal !== 0 && horizontal !== this.facing) {
        this.facing = horizontal;
        this.player.setScale(horizontal, 1);
      }

      this.player.setPosition(this.playerPosition.x, this.playerPosition.y);
      this.player.setDepth(this.playerPosition.y);
    }

    const nearbyNpc = findNearestNpcInRange(this.playerPosition);
    this.updateProximity(nearbyNpc);

    const wantsToTalk =
      Phaser.Input.Keyboard.JustDown(keys.interact) ||
      Phaser.Input.Keyboard.JustDown(keys.confirm);

    if (wantsToTalk && nearbyNpc && !this.isPanelOpen) {
      this.isPanelOpen = true;
      this.promptText.setVisible(false);
      this.nearbyMarker.setVisible(false);
      this.bridge.emit('npc:interact', {
        npcId: nearbyNpc.id,
        npcName: nearbyNpc.name,
      });
    }
  }

  private bindKeyboard(): void {
    const keyboard = this.input.keyboard;

    if (!keyboard) {
      return;
    }

    this.keys = keyboard.addKeys({
      w: Phaser.Input.Keyboard.KeyCodes.W,
      a: Phaser.Input.Keyboard.KeyCodes.A,
      s: Phaser.Input.Keyboard.KeyCodes.S,
      d: Phaser.Input.Keyboard.KeyCodes.D,
      up: Phaser.Input.Keyboard.KeyCodes.UP,
      down: Phaser.Input.Keyboard.KeyCodes.DOWN,
      left: Phaser.Input.Keyboard.KeyCodes.LEFT,
      right: Phaser.Input.Keyboard.KeyCodes.RIGHT,
      interact: Phaser.Input.Keyboard.KeyCodes.E,
      confirm: Phaser.Input.Keyboard.KeyCodes.ENTER,
    }) as unknown as MovementKeys;
  }

  private createPrompt(): void {
    this.promptText = this.add
      .text(WORLD_WIDTH / 2, WORLD_HEIGHT - 24, '', {
        fontFamily: 'Courier New, monospace',
        fontSize: '13px',
        color: '#fef3c7',
        backgroundColor: '#0f172aee',
        padding: { x: 12, y: 6 },
        align: 'center',
      })
      .setOrigin(0.5)
      .setDepth(1000)
      .setVisible(false);
  }

  private updateProximity(npc: NpcDefinition | null): void {
    const nextId = npc?.id ?? null;

    if (nextId !== this.nearbyNpcId) {
      this.nearbyNpcId = nextId;
      this.bridge.emit('npc:proximity', { npcId: nextId });
    }

    if (!npc || this.isPanelOpen) {
      this.promptText.setVisible(false);
      this.nearbyMarker.setVisible(false);
      return;
    }

    this.promptText
      .setText(`Press E or Enter to talk to ${npc.name}`)
      .setVisible(true);
    this.nearbyMarker
      .setPosition(npc.x, npc.y)
      .setDepth(npc.y - 1)
      .setVisible(true);
  }

  private handlePanelClosed = (): void => {
    this.isPanelOpen = false;
  };

  private handleShutdown(): void {
    this.unsubscribePanelClosed?.();
    this.unsubscribePanelClosed = undefined;
  }

  private drawGround(): void {
    const graphics = this.add.graphics();

    graphics.fillStyle(0x2f5d3a, 1).fillRect(0, 0, WORLD_WIDTH, WORLD_HEIGHT);

    // Deterministic grass tufts and tiles keep the map hand-made but varied.
    for (let row = 0; row < 18; row += 1) {
      for (let column = 0; column < 30; column += 1) {
        if ((row + column) % 3 === 0) {
          graphics
            .fillStyle(0x356a42, 0.7)
            .fillRect(column * 32 + 6, row * 32 + 8, 12, 6);
        }
        if ((row * 3 + column) % 7 === 0) {
          graphics
            .fillStyle(0x285031, 0.8)
            .fillRect(column * 32 + 20, row * 32 + 20, 6, 8);
        }
      }
    }

    // Dirt roads and the central cobbled plaza.
    graphics.fillStyle(0x9b7653, 1).fillRect(0, 330, WORLD_WIDTH, 58);
    graphics.fillStyle(0x8a6848, 1).fillRect(430, 68, 100, WORLD_HEIGHT - 68);
    graphics.fillStyle(0x7f6d58, 1).fillRect(392, 232, 176, 172);

    graphics.lineStyle(1, 0x6b5a47, 0.7);
    for (let y = 240; y < 404; y += 20) {
      graphics.lineBetween(392, y, 568, y);
    }
    for (let x = 400; x < 568; x += 20) {
      graphics.lineBetween(x, 232, x, 404);
    }

    // Walkways from each doorway to the road.
    graphics.fillStyle(0xb39064, 1);
    graphics.fillRect(160, 214, 36, 116);
    graphics.fillRect(462, 198, 36, 34);
    graphics.fillRect(778, 214, 34, 116);

    // Top hedge forms the visible edge of the playable area.
    graphics.fillStyle(0x1d3b28, 1).fillRect(0, 0, WORLD_WIDTH, 68);
    for (let x = 0; x < WORLD_WIDTH; x += 32) {
      const offset = (x / 32) % 2 === 0 ? 0 : 8;
      graphics
        .fillStyle(0x275237, 1)
        .fillRect(x, 20 + offset, 32, 24 - offset);
      graphics
        .fillStyle(0x1a3323, 1)
        .fillRect(x + 4, 52 + offset, 24, 12 - offset);
    }

    this.add
      .text(WORLD_WIDTH / 2, 34, 'TASTEVERSE  ·  MARKET SQUARE', {
        fontFamily: 'Courier New, monospace',
        fontSize: '16px',
        fontStyle: 'bold',
        color: '#fde68a',
        stroke: '#14261b',
        strokeThickness: 4,
      })
      .setOrigin(0.5);
  }

  private drawObstacles(): void {
    for (const obstacle of TOWN_OBSTACLES) {
      switch (obstacle.kind) {
        case 'building':
          this.drawBuilding(obstacle);
          break;
        case 'fountain':
          this.drawFountain(obstacle);
          break;
        case 'stall':
          this.drawStall(obstacle);
          break;
        case 'crates':
          this.drawCrates(obstacle);
          break;
        case 'tree':
          this.drawTree(obstacle);
          break;
        case 'bench':
          this.drawBench(obstacle);
          break;
      }
    }
  }

  private drawBuilding(obstacle: Obstacle): void {
    const style = BUILDING_STYLES[obstacle.id] ?? BUILDING_STYLES['town-hall'];
    const { x, y, width, height } = obstacle;
    const graphics = this.add.graphics();

    graphics
      .fillStyle(0x14261b, 0.35)
      .fillRect(x + 8, y + 8, width, height);
    graphics.fillStyle(style.wall, 1).fillRect(x, y, width, height);
    graphics
      .fillStyle(style.roof, 1)
      .fillRect(x - 8, y - 12, width + 16, 22);
    graphics
      .fillStyle(style.trim, 0.8)
      .fillRect(x - 8, y + 8, width + 16, 4);

    for (let windowX = x + 22; windowX <= x + width - 40; windowX += 54) {
      graphics.fillStyle(0x1e293b, 1).fillRect(windowX, y + 32, 22, 24);
      graphics.fillStyle(0x93c5fd, 1).fillRect(windowX + 3, y + 35, 16, 18);
      graphics.fillStyle(0xbfdbfe, 1).fillRect(windowX + 5, y + 37, 5, 6);
    }

    const doorX = x + width / 2 - 15;
    graphics.fillStyle(0x3f2a1d, 1).fillRect(doorX, y + height - 42, 30, 42);
    graphics.fillStyle(0xfbbf24, 1).fillRect(doorX + 23, y + height - 24, 3, 3);

    this.add
      .text(x + width / 2, y + 18, style.sign, {
        fontFamily: 'Courier New, monospace',
        fontSize: '12px',
        fontStyle: 'bold',
        color: '#f8fafc',
        backgroundColor: '#0f172acc',
        padding: { x: 6, y: 2 },
      })
      .setOrigin(0.5);
  }

  private drawFountain(obstacle: Obstacle): void {
    const { x, y, width, height } = obstacle;
    const graphics = this.add.graphics();

    graphics
      .fillStyle(0x14261b, 0.35)
      .fillRect(x + 4, y + 6, width, height);
    graphics.fillStyle(0x9ca3af, 1).fillRect(x, y + 12, width, height - 12);
    graphics.fillStyle(0xd1d5db, 1).fillRect(x - 6, y + 10, width + 12, 12);
    graphics.fillStyle(0x0e7490, 1).fillRect(x + 8, y + 18, width - 16, 24);
    graphics.fillStyle(0x22d3ee, 1).fillRect(x + 12, y + 20, width - 30, 5);
    graphics.fillStyle(0xe5e7eb, 1).fillRect(x + width / 2 - 5, y - 8, 10, 30);
    graphics.fillStyle(0xf3f4f6, 1).fillRect(x + width / 2 - 13, y - 14, 26, 8);
    graphics.fillStyle(0x67e8f9, 0.8).fillRect(x + 14, y + 26, 5, 8);
    graphics.fillStyle(0x67e8f9, 0.8).fillRect(x + width - 20, y + 24, 4, 10);
  }

  private drawStall(obstacle: Obstacle): void {
    const { x, y, width, height } = obstacle;
    const graphics = this.add.graphics();

    graphics
      .fillStyle(0x14261b, 0.35)
      .fillRect(x + 5, y + 6, width, height);
    graphics.fillStyle(0x854d0e, 1).fillRect(x + 8, y + 20, 6, height - 20);
    graphics
      .fillStyle(0x854d0e, 1)
      .fillRect(x + width - 14, y + 20, 6, height - 20);

    for (let stripe = 0; stripe < 7; stripe += 1) {
      graphics
        .fillStyle(stripe % 2 === 0 ? 0xfef3c7 : 0xdc2626, 1)
        .fillRect(x - 4 + stripe * 20, y, 20, 20);
    }

    graphics.fillStyle(0x78350f, 1).fillRect(x + 6, y + 32, width - 12, 14);
    graphics.fillStyle(0xfbbf24, 1).fillRect(x + 18, y + 36, 10, 8);
    graphics.fillStyle(0x22c55e, 1).fillRect(x + 36, y + 35, 12, 9);
    graphics.fillStyle(0xf97316, 1).fillRect(x + 56, y + 36, 10, 8);
    graphics.fillStyle(0xfef3c7, 1).fillRect(x + 76, y + 35, 14, 9);

    this.add
      .text(x + width / 2, y + 42, 'MARKET', {
        fontFamily: 'Courier New, monospace',
        fontSize: '9px',
        fontStyle: 'bold',
        color: '#fef3c7',
      })
      .setOrigin(0.5)
      .setDepth(1);
  }

  private drawCrates(obstacle: Obstacle): void {
    const { x, y, width, height } = obstacle;
    const graphics = this.add.graphics();

    graphics
      .fillStyle(0x14261b, 0.35)
      .fillRect(x + 4, y + 5, width, height);
    graphics.fillStyle(0x92400e, 1).fillRect(x, y + 16, width, height - 16);
    graphics.fillStyle(0xb45309, 1).fillRect(x + 2, y, 22, 20);
    graphics.fillStyle(0x78350f, 1).fillRect(x + 24, y + 2, 20, 18);
    graphics.lineStyle(2, 0xf59e0b, 0.8);
    graphics.lineBetween(x, y + 16, x + width, y + height);
    graphics.lineBetween(x + width, y + 16, x, y + height);
    graphics.lineBetween(x + 2, y + 2, x + 22, y + 18);
  }

  private drawTree(obstacle: Obstacle): void {
    const { x, y, width, height } = obstacle;
    const graphics = this.add.graphics();

    graphics
      .fillStyle(0x14261b, 0.35)
      .fillEllipse(x + width / 2 + 4, y + height + 4, 46, 14);
    graphics.fillStyle(0x78350f, 1).fillRect(x + 15, y + 18, 8, height - 18);
    graphics.fillStyle(0x14532d, 1).fillRect(x, y + 6, width, 24);
    graphics.fillStyle(0x166534, 1).fillRect(x + 3, y, width - 6, 22);
    graphics.fillStyle(0x22c55e, 1).fillRect(x + 8, y + 2, 12, 8);
    graphics.fillStyle(0x15803d, 1).fillRect(x - 2, y + 16, width + 4, 12);
    graphics.fillStyle(0x4ade80, 0.7).fillRect(x + 20, y + 10, 7, 6);
  }

  private drawBench(obstacle: Obstacle): void {
    const { x, y, width, height } = obstacle;
    const graphics = this.add.graphics();

    graphics
      .fillStyle(0x14261b, 0.3)
      .fillRect(x + 3, y + 4, width, height);
    graphics.fillStyle(0x78350f, 1).fillRect(x, y, width, 8);
    graphics.fillStyle(0xa16207, 1).fillRect(x, y + 8, width, 4);
    graphics.fillStyle(0x451a03, 1).fillRect(x + 8, y + 12, 5, 10);
    graphics.fillStyle(0x451a03, 1).fillRect(x + width - 13, y + 12, 5, 10);
  }

  private drawNpc(npc: NpcDefinition): void {
    const graphics = this.add.graphics();
    const { skin, hair, outfit, accent } = npc.colors;

    graphics
      .fillStyle(0x14261b, 0.35)
      .fillEllipse(0, 5, 30, 10);
    graphics.fillStyle(0x1e293b, 1).fillRect(-7, -12, 6, 16);
    graphics.fillStyle(0x334155, 1).fillRect(1, -12, 6, 16);
    graphics.fillStyle(outfit, 1).fillRect(-10, -34, 20, 24);
    graphics.fillStyle(skin, 1).fillRect(-6, -47, 12, 13);
    graphics.fillStyle(hair, 1).fillRect(-7, -50, 14, 6);

    switch (npc.look) {
      case 'apron':
        graphics.fillStyle(accent, 1).fillRect(-6, -29, 12, 16);
        graphics.fillStyle(hair, 1).fillRect(-11, -50, 6, 8);
        graphics.fillStyle(0xfca5a5, 1).fillRect(-8, -41, 3, 2);
        break;
      case 'cap':
        graphics.fillStyle(accent, 1).fillRect(-9, -52, 18, 5);
        graphics.fillStyle(accent, 1).fillRect(-9, -48, 23, 3);
        graphics.fillStyle(0xfef3c7, 1).fillRect(-10, -27, 20, 4);
        break;
      case 'scarf':
        graphics.fillStyle(hair, 1).fillRect(-13, -50, 26, 4);
        graphics.fillStyle(hair, 1).fillRect(-7, -46, 14, 3);
        graphics.fillStyle(accent, 1).fillRect(-10, -36, 20, 5);
        graphics.fillStyle(accent, 1).fillRect(6, -33, 4, 12);
        graphics.fillStyle(0xf5f5f4, 1).fillRect(-5, -41, 10, 4);
        break;
    }

    const container = this.add.container(npc.x, npc.y, graphics);
    const label = this.add
      .text(npc.x, npc.y - 68, npc.name, {
        fontFamily: 'Courier New, monospace',
        fontSize: '12px',
        fontStyle: 'bold',
        color: '#f8fafc',
        stroke: '#0f172a',
        strokeThickness: 4,
      })
      .setOrigin(0.5);

    container.setDepth(npc.y);
    label.setDepth(npc.y + 1);
  }

  private drawPlayer(): void {
    const graphics = this.add.graphics();

    graphics
      .fillStyle(0x14261b, 0.4)
      .fillEllipse(0, 6, 24, 9);
    graphics.fillStyle(0x1e293b, 1).fillRect(-6, -13, 5, 17);
    graphics.fillStyle(0x334155, 1).fillRect(1, -13, 5, 17);
    graphics.fillStyle(0xf59e0b, 1).fillRect(-8, -34, 16, 22);
    graphics.fillStyle(0x14b8a6, 1).fillRect(-8, -34, 16, 5);
    graphics.fillStyle(0x0f766e, 1).fillRect(5, -30, 4, 14);
    graphics.fillStyle(0xf1c27d, 1).fillRect(-5, -46, 10, 12);
    graphics.fillStyle(0x92400e, 1).fillRect(-7, -49, 14, 6);
    graphics.fillStyle(0x1e293b, 1).fillRect(-3, -41, 2, 2);
    graphics.fillStyle(0x1e293b, 1).fillRect(2, -41, 2, 2);

    this.player = this.add
      .container(this.playerPosition.x, this.playerPosition.y, graphics)
      .setDepth(this.playerPosition.y);
  }
}
