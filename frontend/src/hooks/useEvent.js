import { useEffect, useState } from 'react'
import { fetchEvent } from '../api/events.js'

const initialState = { status: 'loading', event: null, error: null }

// Loads one event. Mount it with `key={id}` so a different id starts from a fresh state.
export default function useEvent(id) {
  const [state, setState] = useState(initialState)
  const [request, setRequest] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    fetchEvent(id, { signal: controller.signal }).then(
      (event) => {
        if (!controller.signal.aborted) setState({ status: 'success', event, error: null })
      },
      (error) => {
        if (controller.signal.aborted) return
        setState({ status: error.code === 'not-found' ? 'not-found' : 'error', event: null, error: error.message })
      },
    )
    return () => controller.abort()
  }, [id, request])

  function reload() {
    setState(initialState)
    setRequest((value) => value + 1)
  }

  return { ...state, reload }
}
