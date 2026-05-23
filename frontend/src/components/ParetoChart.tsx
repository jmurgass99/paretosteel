'use client'

import React from 'react'
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import type { OptimizerCandidate } from '@/lib/api'

export function ParetoChart({ pareto }: { pareto: OptimizerCandidate[] }) {
  const feasible = pareto.filter((p) => p.feasible)
  const infeasible = pareto.filter((p) => !p.feasible)
  return (
    <div className="w-full h-80 bg-slate-900/50 rounded-lg p-3">
      <ResponsiveContainer>
        <ScatterChart>
          <CartesianGrid stroke="#334155" />
          <XAxis
            dataKey="weight_kg"
            name="Peso"
            unit=" kg"
            stroke="#94a3b8"
            label={{ value: 'Peso (kg)', position: 'insideBottom', dy: 10, fill: '#94a3b8' }}
          />
          <YAxis
            dataKey="cost_usd"
            name="Costo"
            unit=" USD"
            stroke="#94a3b8"
            label={{ value: 'Costo (USD)', angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155' }}
            formatter={(v: number) => v.toFixed(2)}
          />
          <Legend wrapperStyle={{ color: '#cbd5e1' }} />
          <Scatter name="Factible" data={feasible} fill="#10b981" />
          <Scatter name="No factible" data={infeasible} fill="#ef4444" />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}
