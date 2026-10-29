import Phaser from 'phaser';

export const TOWN_SCENE_KEY = 'TownScene';

/**
 * Minimal Phaser 3 scene placeholder.
 *
 * It proves the canvas and scene loop are alive without adding map assets,
 * NPCs, collisions, or game rules from later tasks.
 */
export class TownScene extends Phaser.Scene {
  constructor() {
    super({ key: TOWN_SCENE_KEY });
  }

  create(): void {
    const { width, height } = this.scale;

    this.cameras.main.setBackgroundColor('#0f172a');

    const grid = this.add.graphics();
    grid.lineStyle(1, 0x334155, 0.35);
    for (let x = 0; x <= width; x += 48) {
      grid.lineBetween(x, 0, x, height);
    }
    for (let y = 0; y <= height; y += 48) {
      grid.lineBetween(0, y, width, y);
    }

    this.add
      .text(width / 2, height / 2 - 58, 'TASTEVERSE', {
        fontFamily: 'Inter, system-ui, sans-serif',
        fontSize: '32px',
        fontStyle: 'bold',
        color: '#fbbf24',
      })
      .setOrigin(0.5);

    this.add
      .text(width / 2, height / 2 - 14, 'Town scene placeholder', {
        fontFamily: 'Inter, system-ui, sans-serif',
        fontSize: '18px',
        color: '#e2e8f0',
      })
      .setOrigin(0.5);

    this.add
      .text(
        width / 2,
        height / 2 + 22,
        'Map, NPCs, and interactions arrive in Task 03',
        {
          fontFamily: 'Inter, system-ui, sans-serif',
          fontSize: '13px',
          color: '#94a3b8',
        },
      )
      .setOrigin(0.5);

    const marker = this.add.circle(width / 2, height / 2 + 82, 9, 0xfbbf24);
    this.tweens.add({
      targets: marker,
      alpha: 0.35,
      yoyo: true,
      repeat: -1,
      duration: 900,
      ease: 'Sine.easeInOut',
    });

    this.add
      .text(width / 2, height / 2 + 110, 'Phaser 3 · 960 × 540', {
        fontFamily: 'Inter, system-ui, sans-serif',
        fontSize: '11px',
        color: '#64748b',
      })
      .setOrigin(0.5);
  }
}
