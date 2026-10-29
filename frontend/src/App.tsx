import { useState } from 'react';

import PhaserStage from './game/PhaserStage';

const scaffoldFacts = [
  { label: 'React + Vite', detail: 'Typed UI shell' },
  { label: 'Phaser 3', detail: 'Scene placeholder' },
  { label: 'FastAPI', detail: 'Health endpoint ready' },
];

function App() {
  const [started, setStarted] = useState(false);

  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-950 text-slate-100">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -left-32 top-[-10rem] h-[28rem] w-[28rem] rounded-full bg-amber-400/10 blur-3xl"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-40 bottom-[-12rem] h-[32rem] w-[32rem] rounded-full bg-cyan-400/10 blur-3xl"
      />

      <div className="relative mx-auto flex min-h-screen w-full max-w-6xl flex-col px-6 py-8 sm:px-8">
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-5">
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-amber-400 font-black text-slate-950">
              TV
            </span>
            <div>
              <p className="text-sm font-semibold tracking-[0.22em] uppercase">
                TasteVerse
              </p>
              <p className="text-xs text-slate-400">Taste, culture, connection</p>
            </div>
          </div>
          <span className="rounded-full border border-amber-300/30 bg-amber-300/10 px-3 py-1 text-xs font-medium text-amber-200">
            Task 01 · Runnable scaffold
          </span>
        </header>

        <main className="grid flex-1 items-center gap-10 py-12 lg:grid-cols-[1.05fr_0.95fr] lg:gap-14">
          <section aria-labelledby="hero-heading">
            <p className="mb-5 flex items-center gap-2 text-xs font-semibold tracking-[0.24em] text-amber-300 uppercase">
              <span className="h-px w-8 bg-amber-300" aria-hidden="true" />
              A small town, a big question
            </p>
            <h1
              id="hero-heading"
              className="max-w-xl text-5xl font-semibold tracking-tight text-white sm:text-6xl"
            >
              TasteVerse
              <span className="mt-3 block bg-gradient-to-r from-amber-200 via-orange-300 to-rose-300 bg-clip-text text-2xl font-normal text-transparent sm:text-3xl">
                What if your taste could open doors?
              </span>
            </h1>
            <p className="mt-6 max-w-xl text-base leading-7 text-slate-300 sm:text-lg">
              Step into a cultural adventure where movies, music, and food become
              conversation. Explore the town, meet its people, and discover what
              your taste says about you.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-4">
              {started ? (
                <button
                  type="button"
                  onClick={() => setStarted(false)}
                  className="rounded-xl border border-white/15 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:border-amber-300/50 hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-300"
                >
                  Return to start
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setStarted(true)}
                  className="group inline-flex items-center gap-3 rounded-xl bg-amber-400 px-5 py-3 text-sm font-bold text-slate-950 shadow-lg shadow-amber-400/20 transition hover:bg-amber-300 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-200"
                >
                  Enter the town
                  <span
                    aria-hidden="true"
                    className="transition-transform group-hover:translate-x-0.5"
                  >
                    →
                  </span>
                </button>
              )}
              <span className="text-xs text-slate-400">
                No external services are called in this task.
              </span>
            </div>

            {started ? (
              <div
                role="status"
                className="mt-8 max-w-xl rounded-2xl border border-emerald-300/25 bg-emerald-300/5 p-4"
              >
                <p className="flex items-center gap-2 text-sm font-semibold text-emerald-200">
                  <span
                    aria-hidden="true"
                    className="h-2 w-2 rounded-full bg-emerald-300"
                  />
                  Scaffold active
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-300">
                  The Phaser placeholder scene is initialized and running. NPCs,
                  quests, and API-backed clues arrive in later tasks.
                </p>
              </div>
            ) : null}

            <dl className="mt-10 grid max-w-xl gap-3 sm:grid-cols-3">
              {scaffoldFacts.map((fact) => (
                <div
                  key={fact.label}
                  className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-3"
                >
                  <dt className="text-xs font-semibold text-white">{fact.label}</dt>
                  <dd className="mt-1 text-xs text-slate-400">{fact.detail}</dd>
                </div>
              ))}
            </dl>
          </section>

          <section
            aria-label="Phaser scene preview"
            className="rounded-3xl border border-white/10 bg-slate-900/70 p-3 shadow-2xl shadow-black/40 backdrop-blur"
          >
            <div className="flex items-center justify-between gap-3 px-2 pb-3 pt-1">
              <div className="flex items-center gap-2">
                <span
                  aria-hidden="true"
                  className="h-2 w-2 rounded-full bg-emerald-300"
                />
                <span className="text-xs font-semibold tracking-wide text-slate-200">
                  TownScene
                </span>
              </div>
              <span className="rounded-md border border-white/10 px-2 py-1 text-[10px] font-semibold tracking-widest text-slate-400 uppercase">
                Phaser 3
              </span>
            </div>

            <div className="h-[300px] overflow-hidden rounded-2xl border border-white/10 bg-slate-950 sm:h-[380px]">
              <PhaserStage />
            </div>

            <div className="flex items-center justify-between gap-3 px-2 pb-1 pt-3">
              <p className="text-xs text-slate-400">
                Placeholder scene · no assets or game rules yet
              </p>
              <span className="text-[10px] font-semibold tracking-widest text-slate-500 uppercase">
                960 × 540
              </span>
            </div>
          </section>
        </main>

        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-5 text-xs text-slate-500">
          <p>TasteVerse scaffold · Phase P0</p>
          <p>Local-only health check: GET /health</p>
        </footer>
      </div>
    </div>
  );
}

export default App;
