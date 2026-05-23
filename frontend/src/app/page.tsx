import Link from 'next/link'

export default function HomePage() {
  return (
    <main className="min-h-screen p-8 bg-slate-950 text-slate-100">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-4xl font-bold mb-3">SteelOptimizerJm</h1>
        <p className="text-slate-400 mb-8">
          Optimizador GA multi-objetivo (peso / costo) para secciones de acero —
          AISC 360, EC3, NSR-10.
        </p>
        <Link
          href="/optimizer"
          className="inline-block px-5 py-3 rounded bg-blue-600 hover:bg-blue-700 text-white font-medium"
        >
          Abrir optimizador
        </Link>
      </div>
    </main>
  )
}
