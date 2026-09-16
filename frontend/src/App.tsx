import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ArrowRight,
  ArrowUpFromLine,
  Check,
  CircleHelp,
  FileSpreadsheet,
  HardDrive,
  LoaderCircle,
  Moon,
  Plus,
  ShieldCheck,
  Sun,
  X,
} from 'lucide-react'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import * as TabsPrimitive from '@radix-ui/react-tabs'
import { Button } from '@/components/ui/button'
import { Overview } from '@/components/Overview'
import { FindingsView, FindingDetails } from '@/components/Findings'
import { Columns } from '@/components/Columns'
import { Investigator } from '@/components/Investigator'
import { api, ApiError } from '@/api/client'
import type { Dataset, Finding, Investigation, OllamaStatus } from '@/types/api'
import { number } from '@/lib/utils'

export default function App() {
  const [dataset, setDataset] = useState<Dataset | null>(null)
  const [status, setStatus] = useState<OllamaStatus | null>(null)
  const [backendOnline, setBackendOnline] = useState(true)
  const [booting, setBooting] = useState(true)
  const [dark, setDark] = useState(document.documentElement.classList.contains('dark'))
  const [tab, setTab] = useState('overview')
  const [busy, setBusy] = useState(false)
  const [uploadName, setUploadName] = useState('')
  const [phase, setPhase] = useState('Receiving upload')
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const [finding, setFinding] = useState<Finding | null>(null)
  const [active, setActive] = useState<Investigation | null>(null)
  const [starting, setStarting] = useState(false)
  const [limits, setLimits] = useState({ max_upload_mb: 250, agent_max_steps: 5 })
  const fileInput = useRef<HTMLInputElement>(null)
  const asError = (e: unknown) =>
    e instanceof ApiError
      ? e
      : new ApiError('ERROR', e instanceof Error ? e.message : 'An unexpected error occurred.')
  const updateInvestigation = useCallback((value: Investigation) => {
    setActive(value.status === 'running' ? value : null)
    setDataset((d) =>
      d
        ? {
            ...d,
            investigations: [
              ...d.investigations.filter((i) => i.investigation_id !== value.investigation_id),
              value,
            ],
            active_investigation_id: value.status === 'running' ? value.investigation_id : null,
          }
        : d,
    )
  }, [])
  const refreshStatus = useCallback(async () => {
    try {
      const [s, h] = await Promise.all([api.status(), api.health()])
      setStatus(s)
      setLimits(h)
      setBackendOnline(true)
    } catch {
      setBackendOnline(false)
      setStatus(null)
    }
  }, [])
  useEffect(() => {
    let alive = true
    api
      .current()
      .then((d) => {
        if (alive) {
          setDataset(d)
          const running = d?.investigations.find((i) => i.status === 'running')
          if (running) {
            setActive(running)
            setTab('investigator')
          }
        }
      })
      .catch((e) => {
        if (alive) {
          setError(asError(e))
          setBackendOnline(false)
        }
      })
      .finally(() => {
        if (alive) setBooting(false)
      })
    void refreshStatus()
    const timer = setInterval(refreshStatus, 15_000)
    return () => {
      alive = false
      clearInterval(timer)
    }
  }, [refreshStatus])
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
  }, [dark])
  useEffect(() => {
    const media = matchMedia('(prefers-color-scheme: dark)')
    const onChange = () => {
      if (!localStorage.getItem('di-theme')) setDark(media.matches)
    }
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [])
  const activeId = active?.investigation_id
  useEffect(() => {
    if (!activeId) return
    let alive = true
    let timer: ReturnType<typeof setTimeout>
    const poll = async () => {
      try {
        const i = await api.investigation(activeId)
        if (alive) {
          updateInvestigation(i)
          setBackendOnline(true)
        }
      } catch (e) {
        if (!alive) return
        const failure = asError(e)
        if (failure.code === 'INVESTIGATION_NOT_FOUND' || failure.code === 'NO_DATASET') {
          // The backend answered but no longer knows this investigation: it restarted
          // and its in-memory session is gone. Stop polling and resync the dataset.
          setBackendOnline(true)
          setError(
            new ApiError(
              'INVESTIGATION_LOST',
              'The local backend restarted, so this investigation ended without a result. Load the dataset again to continue.',
            ),
          )
          setActive(null)
          setDataset((d) =>
            d
              ? {
                  ...d,
                  investigations: d.investigations.filter(
                    (i) => i.investigation_id !== activeId,
                  ),
                  active_investigation_id: null,
                }
              : d,
          )
          api
            .current()
            .then(setDataset)
            .catch(() => {})
          return
        }
        setBackendOnline(false)
        setError(failure)
      }
      if (alive) timer = setTimeout(poll, 1000)
    }
    timer = setTimeout(poll, 500)
    return () => {
      alive = false
      clearTimeout(timer)
    }
  }, [activeId, updateInvestigation])
  useEffect(() => {
    if (!busy) return
    const timer = setInterval(() => {
      api
        .progress()
        .then((p) => setPhase(p.phase))
        .catch(() => {})
    }, 500)
    return () => clearInterval(timer)
  }, [busy])
  const upload = async (file?: File) => {
    if (busy || active || starting) return
    setError(null)
    if (file && !/\.(csv|parquet)$/i.test(file.name)) {
      setError(new ApiError('UNSUPPORTED_FILE', 'Choose a CSV or Parquet file.'))
      return
    }
    if (file && file.size > limits.max_upload_mb * 1024 * 1024) {
      setError(
        new ApiError('FILE_TOO_LARGE', `Files must be ${limits.max_upload_mb} MB or smaller.`),
      )
      return
    }
    setBusy(true)
    setUploadName(file?.name || 'suspicious_customers.csv')
    setPhase('Receiving upload')
    try {
      const d = await (file ? api.upload(file) : api.demo())
      setDataset(d)
      setActive(null)
      setFinding(null)
      setTab('overview')
      setBackendOnline(true)
    } catch (e) {
      setError(asError(e))
    } finally {
      setBusy(false)
      if (fileInput.current) fileInput.current.value = ''
    }
  }
  const start = async (question: string, selected?: Finding) => {
    if (active || starting) return
    setStarting(true)
    setError(null)
    setTab('investigator')
    setFinding(null)
    try {
      const i = await api.investigate(
        question,
        selected?.source === 'profiler' ? selected.id : undefined,
      )
      updateInvestigation(i)
    } catch (e) {
      setError(asError(e))
      void refreshStatus()
    } finally {
      setStarting(false)
    }
  }
  const investigateFinding = (f: Finding) => {
    void start(
      `Investigate: ${f.title}. Test possible explanations and report the computed evidence.`,
      f,
    )
  }
  const findings: Finding[] = [
    ...(dataset?.profile.findings || []),
    ...(dataset?.investigations.flatMap((i) => (i.final_finding ? [i.final_finding] : [])) || []),
  ].sort(
    (a, b) =>
      ({ high: 0, medium: 1, low: 2 })[a.severity] - { high: 0, medium: 1, low: 2 }[b.severity],
  )
  const canInvestigate =
    !!status?.connected && status.model_available && backendOnline && !active && !starting && !busy
  const common = {
    findings,
    onSelect: setFinding,
    onInvestigate: investigateFinding,
    canInvestigate,
  }
  return (
    <div className="app">
      <header className="app-header">
        <div className="header-inner">
          <a
            className="product-mark"
            href="/"
            onClick={(e) => {
              e.preventDefault()
              setTab('overview')
            }}
          >
            Dataset Investigator<span className="local-badge">Local</span>
          </a>
          <div className="header-actions">
            <div className="model-status" title={status?.message}>
              <span>
                <i
                  className={`status-dot ${status?.connected && status.model_available ? 'connected' : ''}`}
                />
                {!backendOnline
                  ? 'Backend disconnected'
                  : status?.connected
                    ? status.model_available
                      ? 'Ollama connected'
                      : 'Model unavailable'
                    : 'Ollama unavailable'}
              </span>
              <small>{status?.model || 'Checking connection…'}</small>
            </div>
            <span className="header-divider" />
            <Button
              variant="ghost"
              size="icon"
              aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'}
              onClick={() => {
                setDark(!dark)
                localStorage.setItem('di-theme', !dark ? 'dark' : 'light')
              }}
            >
              {dark ? <Sun /> : <Moon />}
            </Button>
          </div>
        </div>
      </header>
      <input
        ref={fileInput}
        type="file"
        accept=".csv,.parquet"
        className="sr-only"
        aria-label="Upload dataset file"
        onChange={(e) => {
          const f = e.target.files?.[0]
          if (f) void upload(f)
        }}
      />
      {error && (
        <div className="global-error error-banner" role="alert">
          <X size={18} />
          <div>
            <strong>{error.message}</strong>
            {error.details != null && (
              <details>
                <summary>Technical details</summary>
                <pre>{JSON.stringify(error.details, null, 2)}</pre>
              </details>
            )}
          </div>
          <Button
            variant="ghost"
            size="icon"
            aria-label="Dismiss error"
            onClick={() => setError(null)}
          >
            <X />
          </Button>
        </div>
      )}
      {!backendOnline && (
        <div className="backend-banner">
          Local backend is not responding. Run <code>make dev</code> in the project directory.
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              void refreshStatus()
              if (!dataset)
                void api
                  .current()
                  .then(setDataset)
                  .catch(() => {})
            }}
          >
            Retry connection
          </Button>
        </div>
      )}
      {booting ? (
        <main className="upload-view">
          <div className="skeleton boot-skeleton" />
          <p className="muted">Connecting to your local workspace…</p>
        </main>
      ) : busy ? (
        <main className="profiling-view" role="status">
          <LoaderCircle size={26} className="spin" />
          <h2>Profiling {uploadName}</h2>
          <p>{phase}</p>
          <div className="profiling-skeletons">
            <div className="skeleton" />
            <div className="skeleton" />
            <div className="skeleton" />
          </div>
          <span className="muted">Building a profile. The source file stays unchanged.</span>
        </main>
      ) : !dataset ? (
        <main className="upload-view">
          <div className="upload-intro">
            <h1>A closer look at your data.</h1>
            <p>
              Understand its structure. Find suspicious patterns.
              <br />
              Investigate the evidence, entirely on your machine.
            </p>
          </div>
          <div
            className={`dropzone ${dragging ? 'dragging' : ''}`}
            role="button"
            tabIndex={0}
            aria-label="Drop a dataset or browse files"
            onClick={() => fileInput.current?.click()}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                fileInput.current?.click()
              }
            }}
            onDragOver={(e) => {
              e.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault()
              setDragging(false)
              if (e.dataTransfer.files.length > 1)
                setError(new ApiError('ONE_FILE', 'Choose one dataset at a time.'))
              else if (e.dataTransfer.files[0]) void upload(e.dataTransfer.files[0])
            }}
          >
            <div className="upload-icon">
              <ArrowUpFromLine size={25} strokeWidth={1.5} />
            </div>
            <h2>{dragging ? 'Drop to start profiling' : 'Drop a dataset here'}</h2>
            <p>
              CSV or Parquet <span>·</span> Up to {limits.max_upload_mb} MB
            </p>
            <span className="browse-button">Browse files</span>
          </div>
          <button className="demo-row" onClick={() => void upload()}>
            <div className="demo-file">
              <FileSpreadsheet size={19} />
              <span>
                <strong>Take a look around</strong>
                <small>Try a synthetic customer dataset with a few things to investigate.</small>
              </span>
            </div>
            <span className="demo-action">
              Load example <ArrowRight size={15} />
            </span>
          </button>
          <div className="upload-principles">
            <span>
              <HardDrive size={15} />
              All data stays local
            </span>
            <span>
              <ShieldCheck size={15} />
              Original always preserved
            </span>
            <span>
              <Check size={15} />
              Profiling works without AI
            </span>
          </div>
        </main>
      ) : (
        <Tabs value={tab} onValueChange={setTab} className="dataset-workspace">
          <div className="dataset-heading">
            <div>
              <div className="dataset-file">
                <FileSpreadsheet size={21} strokeWidth={1.6} />
                <h1>{dataset.file_name}</h1>
              </div>
              <p>
                <span>{number(dataset.rows)} rows</span>
                <span>{dataset.columns} columns</span>
                <span className="snapshot-label">
                  <ShieldCheck size={12} />
                  Read-only snapshot
                </span>
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              disabled={!!active || starting}
              onClick={() => fileInput.current?.click()}
            >
              <Plus />
              Load dataset
            </Button>
          </div>
          <TabsList aria-label="Dataset views">
            {[
              ['overview', 'Overview'],
              ['findings', 'Findings'],
              ['columns', 'Columns'],
              ['investigator', 'Investigator'],
            ].map(([value, label]) => (
              <TabsTrigger value={value} key={value}>
                {label}
                {value === 'findings' && <span className="tab-count">{findings.length}</span>}
                {value === 'investigator' && active && <span className="status-dot connected" />}
              </TabsTrigger>
            ))}
            <span className="tabs-trailing">
              <HardDrive size={13} />
              Local workspace
            </span>
          </TabsList>
          <div className="view-content" key={dataset.dataset_id}>
            <TabsPrimitive.Content value="overview">
              <Overview
                profile={dataset.profile}
                {...common}
                dark={dark}
                viewFindings={() => setTab('findings')}
              />
            </TabsPrimitive.Content>
            <TabsPrimitive.Content value="findings">
              <FindingsView {...common} />
            </TabsPrimitive.Content>
            <TabsPrimitive.Content value="columns">
              <Columns profile={dataset.profile} {...common} dark={dark} />
            </TabsPrimitive.Content>
            <TabsPrimitive.Content value="investigator">
              <Investigator
                findings={findings}
                status={status}
                investigations={dataset.investigations}
                active={active}
                start={start}
                dark={dark}
                maxSteps={limits.agent_max_steps}
              />
            </TabsPrimitive.Content>
          </div>
        </Tabs>
      )}
      <footer className="app-footer">
        <span>
          <ShieldCheck size={13} />
          Your data stays on this machine.
        </span>
        <span>
          <CircleHelp size={13} />
          Findings are signals, not a verdict.
        </span>
      </footer>
      <FindingDetails
        finding={finding}
        close={() => setFinding(null)}
        onInvestigate={investigateFinding}
        canInvestigate={canInvestigate}
        investigations={dataset?.investigations || []}
        dark={dark}
      />
    </div>
  )
}
