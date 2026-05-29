import { useAnimatedScore } from '../hooks/useAnimatedScore'

export default function ScoreBar({ label, score, duration = 800 }) {
  const animatedScore = useAnimatedScore(score || 0, duration)

  const getColor = (value) => {
    if (value >= 80) return 'bg-green-500'
    if (value >= 60) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  const getTextColor = (value) => {
    if (value >= 80) return 'text-green-600'
    if (value >= 60) return 'text-yellow-600'
    return 'text-red-600'
  }

  return (
    <div className="w-full">
      <div className="flex justify-between items-center mb-3">
        {label && <p className="text-xs font-bold text-gray-500 uppercase">{label}</p>}
        <span className={`text-lg font-bold ${getTextColor(animatedScore)}`}>
          {animatedScore}%
        </span>
      </div>
      
      <div className="w-full bg-gray-300 rounded-full h-6 overflow-hidden shadow-sm">
        <div
          className={`h-full rounded-full transition-all ease-out ${getColor(animatedScore)}`}
          style={{ 
            width: `${animatedScore}%`,
            transitionDuration: '50ms'
          }}
        />
      </div>
    </div>
  )
}