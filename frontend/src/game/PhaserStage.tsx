import { useEffect, useRef, useState } from 'react';
import Phaser from 'phaser';

import { TownScene } from './scenes/TownScene';

function PhaserStage() {
  const hostRef = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const host = hostRef.current;

    if (!host) {
      return;
    }

    const game = new Phaser.Game({
      type: Phaser.AUTO,
      parent: host,
      width: 960,
      height: 540,
      backgroundColor: '#0f172a',
      scene: [TownScene],
      scale: {
        mode: Phaser.Scale.FIT,
        autoCenter: Phaser.Scale.CENTER_BOTH,
      },
      render: {
        antialias: true,
      },
    });

    setReady(true);

    return () => {
      game.destroy(true);
    };
  }, []);

  return (
    <div className="relative h-full w-full">
      <div
        ref={hostRef}
        data-testid="phaser-stage"
        aria-label="TasteVerse town scene placeholder"
        className="h-full w-full"
      />
      <span
        data-testid="scene-status"
        className="pointer-events-none absolute bottom-3 left-3 z-10 inline-flex items-center gap-2 rounded-full border border-white/10 bg-slate-950/80 px-3 py-1 text-[10px] font-semibold tracking-wide text-slate-300 backdrop-blur"
      >
        <span
          aria-hidden="true"
          className={`h-1.5 w-1.5 rounded-full ${
            ready ? 'bg-emerald-300' : 'bg-amber-300'
          }`}
        />
        {ready ? 'Phaser scene initialized' : 'Initializing Phaser scene…'}
      </span>
    </div>
  );
}

export default PhaserStage;
