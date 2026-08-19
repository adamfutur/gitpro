import { useCallback, useEffect, useRef, useState } from 'react'

export interface JobLike<TResult> {
  status: 'pending' | 'running' | 'completed' | 'failed'
  stage: string
  result?: TResult
  error?: string
}

export interface JobPollingState<TResult> {
  status: 'idle' | 'running' | 'completed' | 'failed'
  stage: string | null
  result: TResult | null
  error: string | null
}

const IDLE_STATE: JobPollingState<never> = { status: 'idle', stage: null, result: null, error: null }
const POLL_INTERVAL_MS = 2000

/**
 * Tracks one or more background jobs (each identified by an arbitrary string key) through
 * start -> poll -> terminal state, independent of which component is currently mounted.
 *
 * Call this once in a component that outlives the UI that displays job progress (e.g. a
 * layout route that stays mounted while its child tabs swap) and pass the returned handle
 * down, rather than calling it inside the tab itself — otherwise navigating away mid-job
 * unmounts the poller and the job's progress becomes invisible until it's restarted.
 */
export function useJobPolling<TResult>() {
  const [jobs, setJobs] = useState<Record<string, JobPollingState<TResult>>>({})
  const timeoutsRef = useRef<Record<string, number>>({})
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    const timeouts = timeoutsRef.current
    return () => {
      mountedRef.current = false
      Object.values(timeouts).forEach((id) => window.clearTimeout(id))
    }
  }, [])

  const setJobState = useCallback((key: string, state: JobPollingState<TResult>) => {
    setJobs((prev) => ({ ...prev, [key]: state }))
  }, [])

  const pollLoop = useCallback(
    (key: string, poll: (jobId: string) => Promise<JobLike<TResult>>, jobId: string) => {
      poll(jobId)
        .then((job) => {
          if (!mountedRef.current) return
          if (job.status === 'completed' && job.result !== undefined) {
            setJobState(key, { status: 'completed', stage: null, result: job.result, error: null })
          } else if (job.status === 'failed') {
            setJobState(key, { status: 'failed', stage: null, result: null, error: job.error ?? 'Job failed' })
          } else {
            setJobs((prev) => ({ ...prev, [key]: { ...prev[key], stage: job.stage } }))
            timeoutsRef.current[key] = window.setTimeout(() => pollLoop(key, poll, jobId), POLL_INTERVAL_MS)
          }
        })
        .catch((err) => {
          if (!mountedRef.current) return
          setJobState(key, {
            status: 'failed',
            stage: null,
            result: null,
            error: err instanceof Error ? err.message : 'Job failed',
          })
        })
    },
    [setJobState]
  )

  /** Kicks off a new job under `key`, replacing any previous state for that key. */
  const run = useCallback(
    async (
      key: string,
      start: () => Promise<{ job_id: string }>,
      poll: (jobId: string) => Promise<JobLike<TResult>>
    ) => {
      setJobState(key, { status: 'running', stage: 'Starting...', result: null, error: null })
      try {
        const { job_id } = await start()
        pollLoop(key, poll, job_id)
      } catch (err) {
        if (!mountedRef.current) return
        setJobState(key, {
          status: 'failed',
          stage: null,
          result: null,
          error: err instanceof Error ? err.message : 'Failed to start',
        })
      }
    },
    [pollLoop, setJobState]
  )

  /** Seeds `key` with an already-known result (e.g. a previously-persisted analysis), without running a job. */
  const hydrate = useCallback(
    (key: string, result: TResult) => {
      setJobState(key, { status: 'completed', stage: null, result, error: null })
    },
    [setJobState]
  )

  const getState = useCallback((key: string): JobPollingState<TResult> => jobs[key] ?? IDLE_STATE, [jobs])

  return { getState, run, hydrate }
}
