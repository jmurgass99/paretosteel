'use client'

import React, { useState } from 'react'
import { runOptimizer, type OptimizerRequest, type OptimizerResponse } from '@/lib/api'
import { ParetoChart } from '@/components/ParetoChart'

const NORMS = ['AISC 360', 'EC3', 'NSR-10']
const CATALOGS = ['W (AISC)', 'IPE (EC3)', 'HEA (EC3)', 'HSS']

export default function OptimizerPage() {
  const [form, setForm] = useState<OptimizerRequest>({
    catalog: 'W (AISC)',
    norms: ['AISC 360'],
    objective: 'weight',
    constraints: { L_m: 6.0, Mu_kNm: 250, Pu_kN: 150, deflection_limit: 1 / 360 },
    ga: { population: 60, generations: 80 },
  })
  const [result, setResult] = useState<OptimizerResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function toggleNorm(n: string) {
    setForm((f) => ({
      ...f,
      norms: f.norms.includes(n) ? f.norms.filter((x) => x !== n) : [...f.norms, n],
    }))
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await runOptimizer(form)
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen p-8 bg-slate-950 text-slate-100">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-2">Optimizador GA — secciones acero</h1>
        <p className="text-slate-400 mb-6">
          POST <code>/api/optimizer/run</code> — multi-objetivo peso vs costo.
        </p>

        <form onSubmit={onSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-900/50 rounded-lg p-6 mb-6">
          <div>
            <label className="block text-sm mb-1">Catálogo</label>
            <select
              value={form.catalog}
              onChange={(e) => setForm({ ...form, catalog: e.target.value })}
              className="w-full px-3 py-2 rounded bg-slate-800 border border-slate-700 text-sm"
            >
              {CATALOGS.map((c) => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm mb-1">Objetivo</label>
            <select
              value={form.objective}
              onChange={(e) => setForm({ ...form, objective: e.target.value as 'weight' | 'cost' })}
              className="w-full px-3 py-2 rounded bg-slate-800 border border-slate-700 text-sm"
            >
              <option value="weight">Peso</option>
              <option value="cost">Costo</option>
            </select>
          </div>
          <div className="md:col-span-2">
            <label className="block text-sm mb-1">Normas</label>
            <div className="flex flex-wrap gap-2">
              {NORMS.map((n) => (
                <label key={n} className="inline-flex items-center gap-1 px-3 py-1 rounded bg-slate-800 border border-slate-700 text-xs">
                  <input
                    type="checkbox"
                    checked={form.norms.includes(n)}
                    onChange={() => toggleNorm(n)}
                  />
                  {n}
                </label>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-sm mb-1">L (m)</label>
            <input type="number" step="0.1" value={form.constraints.L_m}
              onChange={(e) => setForm({ ...form, constraints: { ...form.constraints, L_m: Number(e.target.value) } })}
              className="w-full px-3 py-2 rounded bg-slate-800 border border-slate-700 text-sm" />
          </div>
          <div>
            <label className="block text-sm mb-1">Mu (kN·m)</label>
            <input type="number" value={form.constraints.Mu_kNm}
              onChange={(e) => setForm({ ...form, constraints: { ...form.constraints, Mu_kNm: Number(e.target.value) } })}
              className="w-full px-3 py-2 rounded bg-slate-800 border border-slate-700 text-sm" />
          </div>
          <div>
            <label className="block text-sm mb-1">Pu (kN)</label>
            <input type="number" value={form.constraints.Pu_kN}
              onChange={(e) => setForm({ ...form, constraints: { ...form.constraints, Pu_kN: Number(e.target.value) } })}
              className="w-full px-3 py-2 rounded bg-slate-800 border border-slate-700 text-sm" />
          </div>
          <div>
            <label className="block text-sm mb-1">Población GA</label>
            <input type="number" value={form.ga.population}
              onChange={(e) => setForm({ ...form, ga: { ...form.ga, population: Number(e.target.value) } })}
              className="w-full px-3 py-2 rounded bg-slate-800 border border-slate-700 text-sm" />
          </div>
          <div className="md:col-span-2">
            <button type="submit" disabled={loading}
              className="px-4 py-2 rounded bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-sm">
              {loading ? 'Ejecutando GA…' : 'Optimizar'}
            </button>
          </div>
        </form>

        {error && (
          <div className="bg-red-900/40 border border-red-700 rounded p-3 mb-4 text-sm">{error}</div>
        )}

        {result && (
          <div className="space-y-6">
            <div className="bg-emerald-900/30 border border-emerald-700 rounded p-4 text-sm">
              <b>Mejor candidato:</b> {result.best.section} — {result.best.weight_kg.toFixed(1)} kg,
              {' '}${result.best.cost_usd.toFixed(2)} USD, utilización {(result.best.utilization * 100).toFixed(1)}%.
            </div>
            <div>
              <h2 className="text-xl font-semibold mb-2">Frente de Pareto</h2>
              <ParetoChart pareto={result.pareto} />
            </div>
            <div>
              <h2 className="text-xl font-semibold mb-2">Candidatos</h2>
              <div className="bg-slate-900/50 rounded p-3 overflow-auto">
                <table className="w-full text-sm">
                  <thead className="text-slate-400 text-left">
                    <tr>
                      <th>Sección</th><th>Peso (kg)</th><th>Costo (USD)</th><th>Util.</th><th>Factible</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.pareto.map((p, i) => (
                      <tr key={i} className="border-t border-slate-800">
                        <td>{p.section}</td>
                        <td>{p.weight_kg.toFixed(1)}</td>
                        <td>{p.cost_usd.toFixed(2)}</td>
                        <td>{(p.utilization * 100).toFixed(1)}%</td>
                        <td className={p.feasible ? 'text-emerald-400' : 'text-red-400'}>
                          {p.feasible ? '✓' : '✗'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  )
}
