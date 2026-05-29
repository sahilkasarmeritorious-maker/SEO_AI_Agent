import { useState, useEffect } from 'react'

export function useAnimatedScore(targetScore, duration = 800) {
  const [animatedScore, setAnimatedScore] = useState(0)

  useEffect(() => {
    if (targetScore === 0) {
      setAnimatedScore(0)
      return
    }

    let startTime = null
    let animationFrameId = null

    const animate = (currentTime) => {
      if (startTime === null) {
        startTime = currentTime
      }

      const elapsed = currentTime - startTime
      const progress = Math.min(elapsed / duration, 1)
      const currentScore = Math.round(progress * targetScore)

      setAnimatedScore(currentScore)

      if (progress < 1) {
        animationFrameId = requestAnimationFrame(animate)
      }
    }

    setAnimatedScore(0)
    animationFrameId = requestAnimationFrame(animate)

    return () => {
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId)
      }
    }
  }, [targetScore, duration])

  return animatedScore
}