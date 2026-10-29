import { useId, useState, type FormEvent } from 'react';

import { startGame } from '../api/client';
import type { StartGameResponse } from '../api/types';
import { parseInterests, type InterestDraft } from '../game/interests';
import ErrorNotice from './ErrorNotice';

interface StartScreenProps {
  onStarted: (result: StartGameResponse) => void;
}

const EMPTY_DRAFT: InterestDraft = { movies: '', music: '', food: '' };

function StartScreen({ onStarted }: StartScreenProps) {
  const formId = useId();
  const [draft, setDraft] = useState<InterestDraft>(EMPTY_DRAFT);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [requestError, setRequestError] = useState<unknown>(null);
  const [pending, setPending] = useState(false);

  const update = (field: keyof InterestDraft, value: string) => {
    setDraft((current) => ({ ...current, [field]: value }));
    setValidationError(null);
  };

  const submit = async () => {
    const parsed = parseInterests(draft);

    if (!parsed.ok) {
      setValidationError(parsed.error);
      return;
    }

    setValidationError(null);
    setRequestError(null);
    setPending(true);

    try {
      const result = await startGame(parsed.playerInterests);
      onStarted(result);
    } catch (error) {
      setRequestError(error);
    } finally {
      setPending(false);
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void submit();
  };

  const interestFields: Array<{
    field: keyof InterestDraft;
    label: string;
    prompt: string;
    placeholder: string;
    accent: string;
  }> = [
    {
      field: 'movies',
      label: 'Movies',
      prompt: 'What do you rewatch?',
      placeholder: 'Inception, Spirited Away',
      accent: 'text-tomato',
    },
    {
      field: 'music',
      label: 'Music',
      prompt: 'What is on repeat?',
      placeholder: 'jazz, city pop, Fela Kuti',
      accent: 'text-moss',
    },
    {
      field: 'food',
      label: 'Food',
      prompt: 'What do you crave?',
      placeholder: 'ramen, warm bread, mango',
      accent: 'text-mustard-dark',
    },
  ];

  return (
    <div className="festival-page min-h-screen text-ink">
      <a href="#start-form" className="skip-link">
        Skip to interest form
      </a>

      <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-4 py-5 sm:px-7 sm:py-7">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-ink pb-4">
          <div className="flex items-center gap-3">
            <span className="brand-block" aria-hidden="true">
              TV
            </span>
            <div>
              <p className="font-mono text-[10px] font-bold uppercase tracking-[0.28em] text-tomato">
                TasteVerse presents
              </p>
              <p className="font-display text-xl font-bold leading-tight sm:text-2xl">
                The Market Square Festival
              </p>
            </div>
          </div>
          <p className="stamp">Field journal · No. 07</p>
        </header>

        <main className="grid flex-1 items-center gap-8 py-8 lg:grid-cols-[1.02fr_0.98fr] lg:gap-12 lg:py-12">
          <section aria-labelledby="start-heading" className="relative">
            <p className="font-mono text-xs font-bold uppercase tracking-[0.24em] text-tomato">
              One night · three neighbours · one plan
            </p>
            <h1
              id="start-heading"
              className="mt-4 max-w-2xl font-display text-5xl font-bold leading-[0.96] tracking-[-0.04em] sm:text-6xl lg:text-7xl"
            >
              Your taste
              <span className="block text-tomato">opens the town.</span>
            </h1>
            <p className="mt-6 max-w-xl text-base leading-7 text-ink/80 sm:text-lg">
              The festival needs a night to remember. Bring what you love —
              films, music, food — then walk the square, trade stories with
              Mara, Jun, and Theo, and turn the conversation into a plan.
            </p>

            <div className="mt-8 grid max-w-xl grid-cols-3 gap-2 sm:gap-3">
              {[
                ['01', 'Bring your taste'],
                ['02', 'Meet all three'],
                ['03', 'Plan the night'],
              ].map(([number, label], index) => (
                <div
                  key={number}
                  className={`border-t-2 border-ink pt-2 ${
                    index === 1 ? 'translate-y-2' : ''
                  }`}
                >
                  <p className="font-mono text-[10px] font-bold tracking-widest text-tomato">
                    {number}
                  </p>
                  <p className="mt-1 text-xs font-semibold leading-5 sm:text-sm">
                    {label}
                  </p>
                </div>
              ))}
            </div>

            <div className="mt-10 max-w-xl border-l-4 border-mustard pl-4">
              <p className="text-sm leading-6 text-ink/70">
                Everything is saved in this browser with the server-signed
                state. Leave the square and come back whenever you like.
              </p>
            </div>
          </section>

          <section
            aria-labelledby="start-form-title"
            className="paper-panel relative px-5 py-6 sm:px-7 sm:py-7"
          >
            <span className="tape -top-3 left-8" aria-hidden="true" />
            <p className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-tomato">
              Admission · one field journal
            </p>
            <h2
              id="start-form-title"
              className="mt-1 font-display text-3xl font-bold leading-tight"
            >
              Fill your first page
            </h2>
            <p className="mt-2 text-sm leading-6 text-ink/75">
              Add at least one taste. Separate several with commas. Up to five
              per shelf.
            </p>

            <form
              id="start-form"
              noValidate
              onSubmit={handleSubmit}
              className="mt-5 space-y-4"
              aria-describedby={`${formId}-help`}
            >
              {interestFields.map((item, index) => (
                <div key={item.field}>
                  <label
                    htmlFor={`${formId}-${item.field}`}
                    className="flex items-baseline justify-between gap-3"
                  >
                    <span className="font-mono text-xs font-bold uppercase tracking-[0.16em]">
                      {item.label}
                    </span>
                    <span
                      className={`text-[11px] font-semibold ${item.accent}`}
                    >
                      {item.prompt}
                    </span>
                  </label>
                  <input
                    id={`${formId}-${item.field}`}
                    type="text"
                    value={draft[item.field]}
                    onChange={(event) =>
                      update(item.field, event.target.value)
                    }
                    autoFocus={index === 0}
                    maxLength={420}
                    className="journal-input mt-1 w-full"
                    placeholder={item.placeholder}
                    autoComplete="off"
                    spellCheck={false}
                  />
                </div>
              ))}

              <p id={`${formId}-help`} className="text-xs leading-5 text-ink/60">
                These become your conversation starters. No account or API key
                is needed in the browser.
              </p>

              {validationError ? (
                <p
                  role="alert"
                  className="border-l-4 border-tomato bg-tomato/10 px-3 py-2 text-sm font-semibold text-tomato-dark"
                >
                  {validationError}
                </p>
              ) : null}

              {requestError ? (
                <ErrorNotice
                  error={requestError}
                  context="start"
                  onRetry={() => void submit()}
                  retryLabel="Retry start"
                />
              ) : null}

              <button
                type="submit"
                disabled={pending}
                className="group flex min-h-12 w-full items-center justify-between gap-4 border-2 border-ink bg-ink px-4 py-3 text-left font-mono text-sm font-bold uppercase tracking-[0.14em] text-paper-light shadow-[5px_5px_0_#c0412b] transition hover:-translate-y-0.5 hover:bg-tomato focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-tomato disabled:cursor-wait disabled:opacity-70 disabled:hover:translate-y-0"
              >
                <span>{pending ? 'Opening the gate…' : 'Enter the town'}</span>
                <span
                  aria-hidden="true"
                  className="text-xl transition-transform group-hover:translate-x-1"
                >
                  →
                </span>
              </button>

            </form>
          </section>
        </main>

        <footer className="flex flex-wrap items-center justify-between gap-2 border-t-2 border-ink/30 pt-4 font-mono text-[10px] uppercase tracking-[0.14em] text-ink/55">
          <p>A small town · a big question</p>
          <p>React + Phaser · signed server state</p>
        </footer>
      </div>
    </div>
  );
}

export default StartScreen;
