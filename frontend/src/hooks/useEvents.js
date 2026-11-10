import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchEvents } from '../api/events.js'

const initialState = { status: 'loading', events: [], total: 0, error: null, loadingMore: false, loadMoreError: null }

export default function useEvents() {
  const [state, setState] = useState(initialState)
  const [request, setRequest] = useState(0)
  const moreController = useRef(null)

  useEffect(() => {
    const controller = new AbortController()
    fetchEvents({ signal: controller.signal }).then(
      ({ events, total }) => {
        if (!controller.signal.aborted) setState({ ...initialState, status: 'success', events, total })
      },
      (error) => {
        if (!controller.signal.aborted) setState({ ...initialState, status: 'error', error: error.message })
      },
    )
    return () => {
      controller.abort()
      moreController.current?.abort()
    }
  }, [request])

  const { status, events, total, loadingMore } = state
  const hasMore = status === 'success' && events.length < total

  const loadMore = useCallback(() => {
    if (!hasMore || loadingMore) return
    const controller = new AbortController()
    moreController.current = controller
    setState((current) => ({ ...current, loadingMore: true, loadMoreError: null }))
    fetchEvents({ offset: events.length, signal: controller.signal }).then(
      (page) => {
        if (controller.signal.aborted) return
        setState((current) => {
          const known = new Set(current.events.map((event) => event.key))
          const added = page.events.filter((event) => !known.has(event.key))
          // An empty page means the list shrank on the server; stop offering more.
          const nextTotal = page.events.length === 0 ? current.events.length : page.total
          return { ...current, events: [...current.events, ...added], total: nextTotal, loadingMore: false }
        })
      },
      (error) => {
        if (!controller.signal.aborted) setState((current) => ({ ...current, loadingMore: false, loadMoreError: error.message }))
      },
    )
  }, [hasMore, loadingMore, events.length])

  function reload() {
    moreController.current?.abort()
    setState(initialState)
    setRequest((value) => value + 1)
  }

  return { ...state, hasMore, loadMore, reload }
}
