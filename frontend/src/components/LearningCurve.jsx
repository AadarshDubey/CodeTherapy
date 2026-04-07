import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import useEnvironmentStore from '../store/useEnvironmentStore';
import './LearningCurve.css';

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
          {entry.name}: {(entry.value * 100).toFixed(1)}% Success
        </p>
      ))}
    </div>
  );
};

export default function LearningCurve() {
  const history = useEnvironmentStore((s) => s.history);

  const chartData = history.map((h, i) => {
    const successRate = h.tests_total > 0 ? h.tests_passed / h.tests_total : 0;
    const firstRate = history[0] ? (history[0].tests_total > 0 ? history[0].tests_passed / history[0].tests_total : 0) : 0;
    return {
      step: h.step || (i + 1),
      reflectionAgent: successRate,
      randomAgent: firstRate,
    };
  });

  return (
    <div className="glass-panel learning-curve-panel" id="learning-curve">
      <div className="learning-curve-title">
        <span>📈</span> Learning Curve (Success Rate)
      </div>
      
      {chartData.length > 0 ? (
        <div className="learning-curve-container">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis 
                dataKey="step" 
                tick={{ fontSize: 11, fill: '#94a3b8' }} 
                axisLine={false} 
                tickLine={false} 
              />
              <YAxis 
                domain={[0, 1]} 
                tick={{ fontSize: 11, fill: '#94a3b8' }} 
                axisLine={false} 
                tickLine={false} 
                tickFormatter={(val) => `${(val * 100).toFixed(0)}%`}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend 
                wrapperStyle={{ fontSize: '0.75rem', color: '#94a3b8', paddingTop: '10px' }} 
                iconType="circle" 
              />
              
              <Line 
                type="monotone" 
                dataKey="reflectionAgent" 
                name="Process-Supervised (Reflection Agent)" 
                stroke="#22d3ee" 
                strokeWidth={2.5}
                dot={{ r: 3, fill: '#22d3ee' }} 
                activeDot={{ r: 5 }} 
              />
              <Line 
                type="monotone" 
                dataKey="randomAgent" 
                name="Standard LLM (Zero-Shot Baseline)" 
                stroke="#f43f5e" 
                strokeWidth={2}
                strokeDasharray="4 4"
                dot={{ r: 2, fill: '#f43f5e' }} 
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', color: '#94a3b8', fontSize: '0.85rem' }}>
          Take steps to visualize agent success rate improvement.
        </div>
      )}
    </div>
  );
}
