import React, { useState, useEffect } from 'react';
import './ComparisonChart.css';

/**
 * ComparisonChart — Animated grouped bar chart comparing
 * blind mode vs reflection mode metrics.
 */
export default function ComparisonChart({ comparison }) {
  const [animated, setAnimated] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setAnimated(true), 300);
    return () => clearTimeout(timer);
  }, [comparison]);

  if (!comparison) return null;

  const metrics = [
    {
      label: 'Success Rate',
      blind: comparison.success_rate?.blind || 0,
      reflection: comparison.success_rate?.reflection || 0,
      format: (v) => `${(v * 100).toFixed(0)}%`,
      max: 1,
    },
    {
      label: 'Fix Quality (Avg Code Correctness)',
      blind: comparison.avg_fix_quality?.blind || 0,
      reflection: comparison.avg_fix_quality?.reflection || 0,
      format: (v) => `${(v * 100).toFixed(0)}%`,
      max: 1,
    },
    {
      label: 'Reflection Quality',
      blind: comparison.avg_reflection_quality?.blind || 0,
      reflection: comparison.avg_reflection_quality?.reflection || 0,
      format: (v) => `${(v * 100).toFixed(0)}%`,
      max: 1,
    },
    {
      label: 'Steps Taken (fewer = better)',
      blind: comparison.steps_taken?.blind || 0,
      reflection: comparison.steps_taken?.reflection || 0,
      format: (v) => `${v}`,
      max: 8,
      invertedBetter: true, // fewer is better
    },
  ];

  // Compute improvement stats
  const successImprovement =
    ((comparison.success_rate?.reflection || 0) - (comparison.success_rate?.blind || 0)) * 100;
  const qualityImprovement =
    ((comparison.avg_fix_quality?.reflection || 0) - (comparison.avg_fix_quality?.blind || 0)) * 100;
  const stepsReduction =
    (comparison.steps_taken?.blind || 0) - (comparison.steps_taken?.reflection || 0);

  return (
    <div className="glass-panel comparison-chart" id="comparison-chart">
      <div className="comparison-chart-title">
        <span>📊</span> A/B Experiment Results
      </div>

      <div className="comparison-bars">
        {metrics.map((m, idx) => {
          const blindPct = m.max > 0 ? (m.blind / m.max) * 100 : 0;
          const refPct = m.max > 0 ? (m.reflection / m.max) * 100 : 0;
          const reflectionWins = m.invertedBetter
            ? m.reflection < m.blind
            : m.reflection > m.blind;

          return (
            <div key={idx} className="comparison-metric">
              <div className="comparison-metric-label">
                {m.label}
                {reflectionWins && <span className="comparison-winner">✨ Reflection Wins</span>}
              </div>
              <div className="comparison-bar-group">
                <div className="comparison-bar-row">
                  <span className="comparison-bar-label blind">Blind</span>
                  <div className="comparison-bar-track">
                    <div
                      className="comparison-bar-fill blind"
                      style={{ width: animated ? `${Math.max(blindPct, 5)}%` : '0%' }}
                    >
                      {m.format(m.blind)}
                    </div>
                  </div>
                </div>
                <div className="comparison-bar-row">
                  <span className="comparison-bar-label reflection">Reflect</span>
                  <div className="comparison-bar-track">
                    <div
                      className={`comparison-bar-fill reflection ${reflectionWins ? 'winner' : ''}`}
                      style={{ width: animated ? `${Math.max(refPct, 5)}%` : '0%' }}
                    >
                      {m.format(m.reflection)}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="comparison-summary">
        <div className="comparison-stat">
          <div className={`comparison-stat-value ${successImprovement >= 0 ? 'positive' : 'negative'}`}>
            {successImprovement >= 0 ? '+' : ''}{successImprovement.toFixed(0)}%
          </div>
          <div className="comparison-stat-label">Success Rate Δ</div>
        </div>
        <div className="comparison-stat">
          <div className={`comparison-stat-value ${qualityImprovement >= 0 ? 'positive' : 'negative'}`}>
            {qualityImprovement >= 0 ? '+' : ''}{qualityImprovement.toFixed(0)}%
          </div>
          <div className="comparison-stat-label">Fix Quality Δ</div>
        </div>
        <div className="comparison-stat">
          <div className={`comparison-stat-value ${stepsReduction >= 0 ? 'positive' : 'negative'}`}>
            {stepsReduction >= 0 ? '-' : '+'}{Math.abs(stepsReduction)}
          </div>
          <div className="comparison-stat-label">Steps Saved</div>
        </div>
      </div>
    </div>
  );
}
