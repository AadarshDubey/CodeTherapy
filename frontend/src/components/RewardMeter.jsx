import React from 'react';
import useEnvironmentStore from '../store/useEnvironmentStore';
import './RewardMeter.css';

export default function RewardMeter() {
  const observation = useEnvironmentStore((s) => s.observation);
  const breakdown = observation?.reward_breakdown;
  const reward = observation?.reward || 0;

  const codeScore = breakdown?.code_correctness || 0;
  const reflectionScore = breakdown?.reflection_quality || 0;
  const combined = breakdown?.combined_reward || reward;

  // SVG circular gauge
  const radius = 64;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - combined * circumference;

  // Color based on score
  const getColor = (score) => {
    if (score >= 0.8) return '#22c55e';
    if (score >= 0.5) return '#f59e0b';
    if (score >= 0.2) return '#f97316';
    return '#f43f5e';
  };

  return (
    <div className="glass-panel reward-meter" id="reward-meter">
      <div className="reward-meter-title">
        <span>🏆</span> Reward
      </div>

      <div className="reward-meter-gauge">
        <svg
          className="reward-meter-circle"
          width="160"
          height="160"
          viewBox="0 0 160 160"
        >
          <circle
            className="reward-meter-bg"
            cx="80"
            cy="80"
            r={radius}
          />
          <circle
            className="reward-meter-fill"
            cx="80"
            cy="80"
            r={radius}
            stroke={getColor(combined)}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
          />
        </svg>
        <div className="reward-meter-value">
          <div
            className="reward-meter-number"
            style={{ color: getColor(combined) }}
          >
            {combined.toFixed(2)}
          </div>
          <div className="reward-meter-label">Combined</div>
        </div>
      </div>

      <div className="reward-meter-breakdown">
        <div className="reward-meter-item">
          <div className="reward-meter-item-value reward-color-code">
            {codeScore.toFixed(2)}
          </div>
          <div className="reward-meter-item-label">Code (×0.6)</div>
        </div>
        <div className="reward-meter-item">
          <div className="reward-meter-item-value reward-color-reflection">
            {reflectionScore.toFixed(2)}
          </div>
          <div className="reward-meter-item-label">Reflection (×0.4)</div>
        </div>
      </div>
    </div>
  );
}
