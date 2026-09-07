import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

import { api, ApiError } from '@/lib/api'
import { useSelection } from '@/lib/selection'
import type { CopilotResponse } from '@/lib/types'

interface Turn {
  role: 'user' | 'assistant'
  content: string
  grounding?: CopilotResponse['grounding']
}

/**
 * The floating assistant. Health and safety questions are what citizens
 * actually ask an air-quality site, so those lead the suggestions; the
 * pollution-science questions sit behind them.
 *
 * It answers from the same grounded AIRS data as the full Copilot page — the
 * model is handed the current readings, the forecast and the source estimate
 * for the selected city and is not permitted to state a figure that is not in
 * them. "Show the data behind this" reveals exactly what it was given.
 */
const STARTERS = [
  'How can I stay safe in this air today?',
  'Is it safe to go for a run right now?',
  'What should I do to protect my skin and eyes?',
  'Is it safe for my child to play outside?',
  'Why is the air bad here today?',
  'Will it get better tonight?',
]

export function ChatWidget() {
  const { citySlug, city } = useSelection()
  const [open, setOpen] = useState(false)
  const [turns, setTurns] = useState<Turn[]>([])
  const [draft, setDraft] = useState('')
  const [conversationId, setConversationId] = useState<number | null>(null)
  const [showFacts, setShowFacts] = useState<number | null>(null)
  const endRef = useRef<HTMLDivElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)

  const suggestions = useQuery({ queryKey: ['copilot-suggestions'],
    queryFn: api.copilotSuggestions, staleTime: 3_600_000, retry: 0 })

  const ask = useMutation({
    mutationFn: (question: string) => api.copilot({
      question, city_slug: citySlug, conversation_id: conversationId }),
    onSuccess: (data) => {
      setConversationId(data.conversation_id)
      setTurns((prev) => [...prev, { role: 'assistant', content: data.answer,
                                     grounding: data.grounding }])
    },
  })

  useEffect(() => {
    if (open) endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [turns, ask.isPending, open])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])

  const send = (question: string) => {
    const trimmed = question.trim()
    if (!trimmed || ask.isPending) return
    setTurns((prev) => [...prev, { role: 'user', content: trimmed }])
    setDraft('')
    ask.mutate(trimmed)
  }

  const unavailable = suggestions.data && !suggestions.data.available

  return (
    <>
      {/* Launcher */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label={open ? 'Close the AIRS assistant' : 'Ask the AIRS assistant'}
        className="fixed bottom-5 right-5 z-[60] flex h-14 w-14 items-center
                   justify-center rounded-full bg-brand text-white shadow-lift
                   transition-transform hover:scale-105 active:scale-95
                   sm:bottom-6 sm:right-6"
        style={{ boxShadow: '0 10px 30px -8px rgb(var(--c-brand) / 0.6)' }}
      >
        {open ? (
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none"
               stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"
               aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
        ) : (
          <svg viewBox="0 0 24 24" width="24" height="24" fill="none"
               stroke="currentColor" strokeWidth="1.9" strokeLinecap="round"
               strokeLinejoin="round" aria-hidden="true">
            <path d="M21 11.5a8.4 8.4 0 0 1-9 8.4 9.5 9.5 0 0 1-2.8-.4L3 21l1.6-4.6
                     A8.3 8.3 0 0 1 3.6 11.5 8.4 8.4 0 0 1 12 3.1a8.4 8.4 0 0 1 9 8.4z" />
            <path d="M8.5 11.5h.01M12 11.5h.01M15.5 11.5h.01" />
          </svg>
        )}
        {!open && turns.length === 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-3.5 w-3.5">
            <span className="absolute inline-flex h-full w-full animate-pulse-ring
                             rounded-full bg-accent opacity-70" />
            <span className="relative inline-flex h-3.5 w-3.5 rounded-full
                             bg-accent ring-2 ring-white" />
          </span>
        )}
      </button>

      {/* Panel */}
      {open && (
        <div ref={panelRef} role="dialog" aria-label="AIRS assistant"
             className="fixed bottom-24 right-4 z-[60] flex max-h-[min(34rem,75vh)]
                        w-[calc(100vw-2rem)] animate-float-in flex-col
                        overflow-hidden rounded-3xl border border-line bg-surface
                        shadow-lift sm:right-6 sm:w-[24rem]">
          <header className="flex items-center gap-3 border-b border-line
                             bg-brand-soft px-4 py-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-full
                             bg-brand text-white">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none"
                   stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="M4 12h9a3 3 0 1 0-3-3" strokeLinecap="round" />
                <path d="M4 17h6" strokeLinecap="round" />
              </svg>
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-bold text-brand-deep">AIRS Assistant</p>
              <p className="truncate text-2xs text-brand-deep/70">
                {city ? `Answering for ${city.name}` : 'Pick a city to begin'}
              </p>
            </div>
          </header>

          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
            {turns.length === 0 && (
              <div>
                <p className="text-sm leading-relaxed text-muted">
                  Ask me anything about the air here — how to stay safe, whether
                  to exercise, protecting your skin and breathing, or why the air
                  is the way it is today.
                </p>
                <div className="mt-3 flex flex-col gap-1.5">
                  {(unavailable ? [] : STARTERS).map((q) => (
                    <button key={q} type="button" onClick={() => send(q)}
                            className="rounded-xl border border-line bg-raised
                                       px-3 py-2 text-left text-xs text-ink
                                       transition-colors hover:border-brand/50
                                       hover:text-brand">
                      {q}
                    </button>
                  ))}
                </div>
                {unavailable && (
                  <p className="mt-3 rounded-xl bg-raised p-3 text-xs text-muted">
                    The assistant needs a Gemini API key. Add{' '}
                    <code className="font-mono text-2xs">GEMINI_API_KEY</code> to
                    the project's <code className="font-mono text-2xs">.env</code>{' '}
                    and restart the backend. Everything else on this page works
                    without it.
                  </p>
                )}
              </div>
            )}

            {turns.map((turn, i) => (
              <div key={i} className={turn.role === 'user' ? 'flex justify-end' : ''}>
                {turn.role === 'user' ? (
                  <p className="max-w-[85%] rounded-2xl rounded-br-md bg-brand
                                px-3.5 py-2 text-sm text-white">{turn.content}</p>
                ) : (
                  <div className="max-w-[92%]">
                    <div className="rounded-2xl rounded-bl-md bg-raised px-3.5 py-2.5">
                      {turn.content.split('\n').filter(Boolean).map((para, j) => (
                        <p key={j} className="text-sm leading-relaxed text-ink
                                              [&:not(:first-child)]:mt-2">
                          {para}
                        </p>
                      ))}
                    </div>
                    {turn.grounding && (
                      <>
                        <button type="button"
                                onClick={() => setShowFacts(showFacts === i ? null : i)}
                                className="mt-1 px-1 text-2xs text-brand underline
                                           underline-offset-2">
                          {showFacts === i ? 'Hide the data behind this'
                                           : 'Show the data behind this'}
                        </button>
                        {showFacts === i && (
                          <ul className="mt-1.5 space-y-1 rounded-xl bg-raised p-2.5">
                            {turn.grounding.facts.map((fact, k) => (
                              <li key={k} className="text-2xs leading-relaxed
                                                     text-muted">
                                {fact.replace(/^\[(\w+)\]\s*/, (_, tag) =>
                                  `${String(tag).toLowerCase()} · `)}
                              </li>
                            ))}
                          </ul>
                        )}
                      </>
                    )}
                  </div>
                )}
              </div>
            ))}

            {ask.isPending && (
              <div className="max-w-[92%] space-y-2 rounded-2xl rounded-bl-md
                              bg-raised px-3.5 py-3">
                <div className="skeleton h-3 w-4/5" />
                <div className="skeleton h-3 w-full" />
                <div className="skeleton h-3 w-2/5" />
              </div>
            )}

            {ask.isError && (
              <p role="alert" className="rounded-xl border border-accent/30
                                         bg-accent-soft px-3 py-2 text-xs text-accent">
                {ask.error instanceof ApiError ? ask.error.message
                  : 'The assistant could not answer just now.'}
              </p>
            )}
            <div ref={endRef} />
          </div>

          <form onSubmit={(e) => { e.preventDefault(); send(draft) }}
                className="flex items-center gap-2 border-t border-line p-2.5">
            <label htmlFor="chat-widget-input" className="sr-only">
              Ask the AIRS assistant
            </label>
            <input id="chat-widget-input" value={draft}
                   onChange={(e) => setDraft(e.target.value)}
                   disabled={ask.isPending || unavailable}
                   placeholder="Ask about safety, health, the air…"
                   className="input flex-1 rounded-full py-2 text-sm" />
            <button type="submit" aria-label="Send"
                    disabled={!draft.trim() || ask.isPending || unavailable}
                    className="flex h-9 w-9 shrink-0 items-center justify-center
                               rounded-full bg-brand text-white transition-colors
                               hover:bg-brand-deep disabled:opacity-40">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none"
                   stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"
                   strokeLinejoin="round" aria-hidden="true">
                <path d="M4 12h15M13 6l6 6-6 6" />
              </svg>
            </button>
          </form>

          <p className="border-t border-line bg-raised px-4 py-1.5 text-center
                        text-[10px] leading-tight text-faint">
            AI answers use AIRS data only. General guidance, not medical advice.
          </p>
        </div>
      )}
    </>
  )
}
