import { useEffect, useState } from 'react'
import { fetchEvents } from '../api/events.js'

const initialState = { status: 'loading', events: [], error: null }

export default function useEvents() {
  const [state, setState] = useState(initialState)
  const [request, setRequest] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    fetchEvents({ signal: controller.signal }).then(
      (events) => {
        if (!controller.signal.aborted) setState({ status: 'success', events, error: null })
      },
      (error) => {
        if (!controller.signal.aborted) setState({ status: 'error', events: [], error: error.message })
      },
    )
    return () => controller.abort()
  }, [request])

  function reload() {
    setState(initialState)
    setRequest((value) => value + 1)
  }

  return { ...state, reload }
}
