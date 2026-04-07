import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts';
import useEnvironmentStore from '../store/useEnvironmentStore';
import './RewardChart.css';

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload || !payload.length) return null;
  return (
    <div
      style={{
        background: 'rgba(15, 15, 40, 0.95)',
        border: '1px solid rgba(99, 102, 241, 0.3)',
        borderRadius: '8px',
        padding: '8px 12px',
        fontSize: '0.8rem',
      }}
    >
      <p style={{ color: '#f1f5f9', fontWeight: 600, marginBottom: 4 }}>
        Step {label}
      </p>
      {payload.map((entry, i) => (
        <p key={i} style={{ color: entry.color, margin: 0 }}>
          {entry.name}: {entry.value.toFixed(3)}
        </p>
      ))}
    </div>
  );
};

export default function RewardChart() {
  const history = useEnvironmentStore((s) => s.history);

  const chartData = history.map((h, i) => ({
    step: i + 1,
    combined: h.combined_reward || h.reward || 0,
    code: h.code_correctness || 0,
    reflection: h.reflection_quality || 0,
  }));

  // calculate correlation between code_correctness and reflection_quality
  let correlationStr = "N/A";
  if (chartData.length > 2) {
    const n = chartData.length;
    const sumX = chartData.reduce((acc, d) => acc + d.reflection, 0);
    const sumY = chartData.reduce((acc, d) => acc + d.code, 0);
    const sumXY = chartData.reduce((acc, d) => acc + (d.reflection * d.code), 0);
    const sumX2 = chartData.reduce((acc, d) => acc + (d.reflection * d.reflection), 0);
    const sumY2 = chartData.reduce((acc, d) => acc + (d.code * d.code), 0);
    
    // Pearson correlation
    const num = (n * sumXY) - (sumX * sumY);
    const den = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));
    if (den !== 0) {
       correlationStr = (num / den).toFixed(2);
    }
  }

  return (
    <div className="glass-panel reward-chart" id="reward-chart">
      <div className="reward-chart-title" style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
        <span><span>📈</span> Reward Evaluation Metrics</span>
        <span style={{ fontSize: '0.75rem', fontWeight: 'normal', color: '#94a3b8' }}>
          Reflection-to-Success Correlation: <strong style={{ color: '#fff' }}>{correlationStr}</strong>
        </span>
      </div>

      {chartData.length > 0 ? (
        <div className="reward-chart-container">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
              <defs>
                <linearGradient id="colorCombined" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#5046e5" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#5046e5" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorCode" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#22d3ee" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="step" tick={{ fontSize: 12 }} />
              <YAxis domain={[0, 1]} tick={{ fontSize: 12 }} />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="combined"
                name="Combined Score"
                stroke="#5046e5"
                fill="url(#colorCombined)"
                strokeWidth={2}
                dot={{ r: 4, fill: '#5046e5' }}
              />
              <Area
                type="monotone"
                dataKey="code"
                name="Code Correctness"
                stroke="#22d3ee"
                fill="url(#colorCode)"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                dot={{ r: 3, fill: '#22d3ee' }}
              />
              <Line
                type="monotone"
                dataKey="reflection"
                name="Reflection Quality"
                stroke="#a78bfa"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                dot={{ r: 3, fill: '#a78bfa' }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="reward-chart-empty">
          Take steps to see reward progression and correlation metrics.
        </div>
      )}
    </div>
  );
}
