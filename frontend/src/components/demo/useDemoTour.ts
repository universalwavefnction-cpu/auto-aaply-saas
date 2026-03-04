import { useState, useCallback } from 'react'

export type DemoStep = 0 | 1 | 2 | 3 | 4

export function useDemoTour() {
  const [step, setStep] = useState<DemoStep>(0)
  const [direction, setDirection] = useState<'forward' | 'back'>('forward')

  const next = useCallback(() => {
    setDirection('forward')
    setStep((s) => Math.min(4, s + 1) as DemoStep)
  }, [])

  const back = useCallback(() => {
    setDirection('back')
    setStep((s) => Math.max(0, s - 1) as DemoStep)
  }, [])

  const goTo = useCallback((target: DemoStep) => {
    setStep((current) => {
      setDirection(target > current ? 'forward' : 'back')
      return target
    })
  }, [])

  return {
    step,
    direction,
    next,
    back,
    goTo,
    isFirst: step === 0,
    isLast: step === 4,
    total: 5,
  }
}
