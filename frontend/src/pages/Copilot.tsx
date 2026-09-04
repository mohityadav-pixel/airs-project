import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

import { AqiPill } from '@/components/AqiGauge'
import { PageHeader } from '@/components/PageHeader'
import { ProvenanceBadge } from '@/components/Provenance'
import { CitySelector, StationSelector } from '@/components/Selectors'
import { ErrorState } from '@/components/State'
import { api } from '@/lib/api'
import { relativeTime } from '@/lib/format'
import { useSelection } from '@/lib/selection'
import type { CopilotResponse } from '@/lib/types'

interface Turn {
  role: 'user' | 'assistant'
  content: string
  at: string
  grounding?: CopilotResponse['grounding']
}

const KIND_TAG: Record<string, { label: string; cls: string }> = {
  OBSERVED: { label: 'Measured', cls: 'text-good' },
  PREDICTED: { label: 'Forecast', cls: 'text-[#2a78d6]' },
  ESTIMATED: { label: 'Estimate', cls: 'text-usg' },
  SIMULATED: { label: 'Scenario', cls: 'text-[#8B5CF6]' },
}

function GroundingPanel({ facts }: { facts: string[] }) {
  return (
    <ul className="space-y-1.5">
      {facts.map((fact, i) => {
        const match = fact.match(/^\[(\w+)\]\s*(.*)$/)
        const tag = match ? KIND_TAG[match[1]] : undefined
        return (
          <li key={i} className="text-2xs leading-relaxed">
            {tag && (
              <span className={`mr-1.5 font-semibold uppercase tracking-wide ${tag.cls}`}>
                {tag.label}
              </span>
            )}
            <span className="text-muted">{match ? match[2] : fact}</span>
          </li>
        )
      })}
    </ul>
  )
}

export default function Copilot() {
  const { citySlug, stationId } = useSelection()
  const [turns, setTurns] = useState<Turn[]>([])
  const [draft, setDraft] = useState('')
  const [conversationId, setConversationId] = useState<number | null>(null)
  const [showGrounding, setShowGrounding] = useState(true)
  const endRef = useRef<HTMLDivElement>(null)

  const suggestions = useQuery({ queryKey: ['copilot-suggestions'],
    queryFn: api.copilotSuggestions, staleTime: 3_600_000 })
  const current = useQuery({ queryKey: ['current', citySlug, stationId],
    queryFn: () => api.current(citySlug, stationId), enabled: Boolean(citySlug) })

  const ask = useMutation({
    mutationFn: (question: string) => api.copilot({
      question, city_slug: citySlug, station_id: stationId,
      conversation_id: conversationId }),
    onSuccess: (data) => {
      setConversationId(data.conversation_id)
      setTurns((prev) => [...prev, { role: 'assistant', content: data.answer,
        at: data.generated_at, grounding: data.grounding }])
    },
  })

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [turns, ask.isPending])

  const send = (question: string) => {
    const trimmed = question.trim()
    if (!trimmed || ask.isPending) return
    setTurns((prev) => [...prev, { role: 'user', content: trimmed,
      at: new Date().toISOString() }])
    setDraft('')
    ask.mutate(trimmed)
  }

  const unavailable = suggestions.data && !suggestions.data.available
  const lastGrounding = [...turns].reverse()
    .find((t) => t.role === 'assistant')?.grounding

  return (
    <>
      <PageHeader title="AIRS Copilot"
                  description="Ask about the air. Answers are written from AIRS data only — every figure comes from the grounding panel, never from the model."
                  actions={<><CitySelector /><StationSelector /></>} />

      {unavailable && (
        <div className="card card-pad mb-4 border-usg/30">
          <p className="text-sm font-medium text-ink">Copilot is not configured</p>
          <p className="mt-1 text-sm text-muted">
            No Gemini API key is set on the server. Add <code
            className="font-mono text-xs">GEMINI_API_KEY</code> to the project's{' '}
            <code className="font-mono text-xs">.env</code> and restart the backend.
            Everything else in AIRS works without it.
          </p>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="card flex h-[640px] flex-col overflow-hidden">
          <div className="flex items-center justify-between border-b border-line
                          px-4 py-3">
            <div>
              <h2 className="text-sm font-semibold text-ink">Conversation</h2>
              <p className="text-2xs text-faint">
                {current.data
                  ? `Context: ${current.data.station.name}, updated ${
                      relativeTime(current.data.observed_at)}`
                  : 'Loading context…'}
              </p>
            </div>
            {current.data && <AqiPill aqi={current.data.aqi} />}
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
            {turns.length === 0 && (
              <div className="mx-auto max-w-md py-10 text-center">
                <p className="text-sm font-medium text-ink">
                  Ask AIRS about the air here
                </p>
                <p className="mt-1.5 text-sm text-muted">
                  The Copilot is given the current readings, the forecast and the
                  estimated source split for the selected station, and is not
                  permitted to state a number that is not in that data.
                </p>
              </div>
            )}

            {turns.map((turn, i) => (
              <div key={i}
                   className={turn.role === 'user' ? 'flex justify-end' : ''}>
                {turn.role === 'user' ? (
                  <p className="max-w-[85%] rounded-2xl rounded-br-md bg-brand px-3.5
                                py-2.5 text-sm text-white">
                    {turn.content}
                  </p>
                ) : (
                  <div className="max-w-[92%]">
                    <div className="rounded-2xl rounded-bl-md bg-raised px-3.5 py-3">
                      {turn.content.split('\n').filter(Boolean).map((para, j) => (
                        <p key={j} className="text-sm leading-relaxed text-ink
                                              [&:not(:first-child)]:mt-2.5">
                          {para}
                        </p>
                      ))}
                    </div>
                    <p className="mt-1 px-1 text-2xs text-faint">
                      AI-generated from AIRS data · {relativeTime(turn.at)}
                    </p>
                  </div>
                )}
              </div>
            ))}

            {ask.isPending && (
              <div className="max-w-[92%]">
                <div className="rounded-2xl rounded-bl-md bg-raised px-3.5 py-3">
                  <div className="space-y-2">
                    <div className="skeleton h-3 w-4/5" />
                    <div className="skeleton h-3 w-full" />
                    <div className="skeleton h-3 w-3/5" />
                  </div>
                </div>
              </div>
            )}

            {ask.isError && (
              <ErrorState error={ask.error} compact
                          onRetry={() => {
                            const lastUser = [...turns].reverse()
                              .find((t) => t.role === 'user')
                            if (lastUser) ask.mutate(lastUser.content)
                          }} />
            )}
            <div ref={endRef} />
          </div>

          <div className="border-t border-line px-4 py-3">
            {turns.length === 0 && suggestions.data?.questions && (
              <div className="mb-2.5 flex flex-wrap gap-1.5">
                {suggestions.data.questions.map((q) => (
                  <button key={q} type="button" onClick={() => send(q)}
                          disabled={unavailable}
                          className="chip hover:border-brand hover:text-brand
                                     disabled:opacity-50">
                    {q}
                  </button>
                ))}
              </div>
            )}
            <form onSubmit={(e) => { e.preventDefault(); send(draft) }}
                  className="flex gap-2">
              <label className="sr-only" htmlFor="copilot-input">Your question</label>
              <input id="copilot-input" value={draft}
                     onChange={(e) => setDraft(e.target.value)}
                     disabled={unavailable || ask.isPending}
                     placeholder="Why is the AQI high right now?"
                     className="input flex-1" />
              <button type="submit"
                      disabled={!draft.trim() || ask.isPending || unavailable}
                      className="btn-primary px-4">Ask</button>
            </form>
          </div>
        </div>

        <div className="card card-pad h-fit">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-ink">Grounding</h2>
            <button type="button" onClick={() => setShowGrounding((v) => !v)}
                    className="text-2xs text-brand">
              {showGrounding ? 'Hide' : 'Show'}
            </button>
          </div>
          <p className="mt-1 text-2xs leading-relaxed text-muted">
            Exactly what the model was given. If a figure is not on this list, the
            Copilot is not allowed to say it.
          </p>
          {showGrounding && (
            <div className="mt-3 border-t border-line pt-3">
              {lastGrounding ? (
                <GroundingPanel facts={lastGrounding.facts} />
              ) : (
                <p className="text-2xs text-faint">
                  Ask a question to see the data behind the answer.
                </p>
              )}
            </div>
          )}
          {current.data && (
            <div className="mt-4 border-t border-line pt-3">
              <ProvenanceBadge provenance={current.data.provenance} />
            </div>
          )}
        </div>
      </div>
    </>
  )
}
