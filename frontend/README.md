# SteelOptimizerJm — frontend Next.js

Frontend Next.js 14 (App Router) + TypeScript + Tailwind para el optimizador GA
de secciones de acero.

## Páginas

| Ruta         | Issue       | Descripción                                            |
| ------------ | ----------- | ------------------------------------------------------ |
| `/`          | —           | Landing simple                                         |
| `/optimizer` | IDEAS_20 #18 | Form (catálogo, normas, peso/costo, restricciones GA) + tabla de candidatos + Pareto chart (recharts). POST a `/api/optimizer/run`. |

## Quickstart

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

Variables:

- `NEXT_PUBLIC_API_URL` — base URL del backend FastAPI (`steeloptimizerjm.api.app`).
  Por defecto `http://localhost:8000`. El `next.config.mjs` ya reescribe
  `/api/*` hacia esa base.

## Dependencias notables

- `next@14.2.5`, `react@18`, `tailwindcss@3`
- `axios` para HTTP
- `recharts` para el gráfico Pareto (scatter peso vs costo)

## Estado

Verificación visual **pendiente** — los archivos se escribieron sin levantar
`npm run dev` en este lote (limitación de entorno). Tras `npm install` el
usuario debe validar el flow end-to-end con el backend corriendo.
