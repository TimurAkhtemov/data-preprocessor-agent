import { useState } from 'react'
import {
  ArrowUpRight,
  Check,
  ChevronDown,
  Code2,
  FlaskConical,
  LoaderCircle,
  Play,
  WifiOff,
  X,
} from 'lucide-react'
import type { Finding, Investigation, OllamaStatus } from '@/types/api'
import { Button } from './ui/button'
import { ChartRenderer } from './ChartRenderer'

// Matches the backend InvestigationRequest.question minimum length.
const MIN_QUESTION_LENGTH = 3

export function InvestigationTrace({ investigation }: { investigation: Investigation }) {
  return (
    <details className="trace">
      <summary>
        <Code2 size={15} />
        View investigation trace<span>{investigation.trace.length} actions</span>
        <ChevronDown size={15} />
      </summary>
      <div className="trace-steps">
        {investigation.trace.map((step) => (
          <div className="trace-step" key={step.number}>
            <div className="row-between">
              <strong>
                Step {step.number} · {step.action.replaceAll('_', ' ')}
              </strong>
              {step.error ? (
                <X size={15} className="high" />
              ) : (
                <Check size={15} className="connected" />
              )}
            </div>
            <p>{step.reason}</p>
            {step.code && (
              <pre className="python-code">
                <code>{step.code}</code>
              </pre>
            )}
            {step.result_summary && (
              <>
                <h4>Computed result</h4>
                <pre>{step.result_summary}</pre>
              </>
            )}
            {step.error && <p className="inline-error">{step.error}</p>}
          </div>
        ))}
      </div>
    </details>
  )
}
export function InvestigationResult({
  investigation,
  dark,
}: {
  investigation?: Investigation
  dark: boolean
}) {
  if (!investigation) return null
  const f = investigation.final_finding
  return (
    <div className="investigation-result">
      {f && (
        <>
          <div className="row-between">
            <span className={`severity ${f.severity}`}>
              <i className="status-dot" />
              {f.severity}
            </span>
            <span className="confidence">{Math.round(f.confidence * 100)}% model confidence</span>
          </div>
          <h2>{f.title}</h2>
          <p className="result-summary">{f.summary}</p>
          <h3>Evidence</h3>
          <ul className="evidence-bullets">
            {f.evidence.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
          <div className="recommendation">
            <h3>Recommendation</h3>
            <p>{f.recommended_action}</p>
          </div>
        </>
      )}
      {investigation.charts.map((chart, i) => (
        <section className="agent-chart" key={i}>
          <div className="panel-heading">
            <h3>{chart.spec.title}</h3>
            <span className="source-label">Agent visualization</span>
          </div>
          <ChartRenderer chart={chart} dark={dark} />
          <p className="chart-reason">
            <strong>Why this helps</strong> {chart.reason}
          </p>
        </section>
      ))}
      {!!investigation.trace.length && <InvestigationTrace investigation={investigation} />}
    </div>
  )
}
export function Investigator({
  findings,
  status,
  investigations,
  active,
  start,
  dark,
  maxSteps,
}: {
  findings: Finding[]
  status: OllamaStatus | null
  investigations: Investigation[]
  active: Investigation | null
  start: (question: string, finding?: Finding) => Promise<void>
  dark: boolean
  maxSteps: number
}) {
  const [question, setQuestion] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const available = status?.connected && status.model_available
  const shown =
    active || investigations.find((i) => i.investigation_id === selectedId) || investigations.at(-1)
  const ready = question.trim().length >= MIN_QUESTION_LENGTH
  const submit = async (q: string, f?: Finding) => {
    if (q.trim().length < MIN_QUESTION_LENGTH || submitting || active || !available) return
    setSubmitting(true)
    setSelectedId(null)
    try {
      await start(q, f)
    } finally {
      setSubmitting(false)
    }
  }
  return (
    <>
      <div className="section-heading">
        <div>
          <h2>Investigate this dataset</h2>
          <p>Ask a question. Inspect the calculations. Follow the evidence.</p>
        </div>
        <span className="bounded-label">
          <FlaskConical size={14} />
          Up to {maxSteps} analytical steps
        </span>
      </div>
      {!available && (
        <div className="unavailable-panel">
          <WifiOff size={20} />
          <div>
            <h3>Local AI investigator unavailable</h3>
            <p>
              {status?.message || 'Checking the local model connection.'} Profiling and column
              exploration remain available.
            </p>
            <p className="muted">
              Configured model: <code>{status?.model || 'Checking…'}</code>
            </p>
            <details>
              <summary>Connection help</summary>
              <p>
                Start Ollama and install the configured model, or set OLLAMA_MODEL to an installed
                model and restart the backend.
              </p>
            </details>
          </div>
        </div>
      )}
      <form
        className="investigator-input"
        onSubmit={(e) => {
          e.preventDefault()
          void submit(question)
        }}
      >
        <label htmlFor="question">What would you like to understand?</label>
        <textarea
          id="question"
          placeholder="Are the extreme age values concentrated in one source system?"
          maxLength={2000}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={!!active || submitting}
          onKeyDown={(e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
              e.preventDefault()
              void submit(question)
            }
          }}
        />
        <div className="input-footer">
          <span>Analyses run locally. Your source stays unchanged.</span>
          <Button type="submit" disabled={!available || !!active || submitting || !ready}>
            {active || submitting ? <LoaderCircle className="spin" /> : <Play size={14} />}
            {active ? 'Investigation in progress' : 'Run investigation'}
          </Button>
        </div>
      </form>
      {!active && (
        <div className="suggestion-row">
          <span>Start with a finding</span>
          {findings
            .filter((f) => f.source === 'profiler')
            .slice(0, 3)
            .map((f) => (
              <button
                disabled={!available || submitting}
                key={f.id}
                onClick={() => {
                  setQuestion(`Investigate: ${f.title}`)
                  void submit(
                    `Investigate: ${f.title}. Test possible explanations with computed evidence.`,
                    f,
                  )
                }}
              >
                {f.title}
                <ArrowUpRight size={13} />
              </button>
            ))}
        </div>
      )}
      {active && (
        <div className="investigation-progress" role="status">
          <div className="row-between">
            <h3>
              <LoaderCircle size={16} className="spin" />
              {active.current_activity}
            </h3>
            <span>
              {active.max_steps - active.steps_remaining} / {active.max_steps}
            </span>
          </div>
          <p>{active.question}</p>
          <div className="step-track">
            {Array.from({ length: active.max_steps }, (_, i) => (
              <span
                key={i}
                className={i < active.max_steps - active.steps_remaining ? 'done' : ''}
              />
            ))}
          </div>
          {active.trace.map((step) => (
            <div className="progress-step" key={step.number}>
              {step.error ? <X size={14} className="high" /> : <Check size={14} />}
              <span>{step.reason}</span>
            </div>
          ))}
        </div>
      )}
      {investigations.length > 1 && !active && (
        <div className="history-selector">
          <label htmlFor="history">This session</label>
          <select
            id="history"
            value={shown?.investigation_id}
            onChange={(e) => setSelectedId(e.target.value)}
          >
            {[...investigations].reverse().map((i) => (
              <option key={i.investigation_id} value={i.investigation_id}>
                {i.question} · {i.status}
              </option>
            ))}
          </select>
        </div>
      )}
      {shown?.error && (
        <div className="error-banner" role="alert">
          <X size={18} />
          <div>
            <strong>Investigation could not be completed</strong>
            <p>{shown.error.message}</p>
            {shown.error.details && (
              <details>
                <summary>Technical details</summary>
                <pre>{shown.error.details}</pre>
              </details>
            )}
          </div>
        </div>
      )}
      {shown && <InvestigationResult investigation={shown} dark={dark} />}
      {!shown && available && (
        <div className="investigator-empty">
          <FlaskConical size={24} />
          <h3>Every explanation starts with evidence</h3>
          <p>
            The investigator can compare groups, test unusual patterns, and request a chart. You can
            inspect every Python action and its result.
          </p>
        </div>
      )}
    </>
  )
}
