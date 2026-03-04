import { useState, useCallback } from 'react'

export type OnboardingStep = 0 | 1 | 2 | 3 | 4

export function useOnboardingTour() {
  const [step, setStep] = useState<OnboardingStep>(0)
  const [direction, setDirection] = useState<'forward' | 'back'>('forward')
  const [completed, setCompleted] = useState<Set<OnboardingStep>>(new Set())

  const next = useCallback(() => {
    setDirection('forward')
    setStep((s) => Math.min(4, s + 1) as OnboardingStep)
  }, [])

  const back = useCallback(() => {
    setDirection('back')
    setStep((s) => Math.max(0, s - 1) as OnboardingStep)
  }, [])

  const goTo = useCallback((target: OnboardingStep) => {
    setStep((current) => {
      setDirection(target > current ? 'forward' : 'back')
      return target
    })
  }, [])

  const markCompleted = useCallback((s: OnboardingStep) => {
    setCompleted((prev) => new Set(prev).add(s))
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
    completed,
    markCompleted,
  }
}
