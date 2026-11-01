"""Metamodelo de Kriging (`surrogate.KrigingSurrogate`) ajustado a la curva de pandeo AISC 360 §E3.

Se muestrea Fcr/Fy de `bracing.aisc_e3_critical_stress` (Fy = 345 MPa, E = 200 GPa) en 9 esbelteces
KL/r ∈ [20, 180], con la variable normalizada a [0, 1], y se compara la predicción con la función
exacta en 33 puntos intermedios. También se predice fuera del rango muestreado: el Kriging del paquete
es un proceso gaussiano de media cero con núcleo RBF de longitud fija (sin ajuste de hiperparámetros),
así que lejos de los datos la predicción vuelve a 0, no a la tendencia.

Ejecutar:  python examples/kriging_surrogate_fit_of_aisc_e3_column_curve_vs_exact_and_extrapolation_warning.py
"""
from paretosteel.bracing import aisc_e3_critical_stress
from paretosteel.surrogate import KrigingSurrogate

FY, E = 345.0, 200000.0
LO, HI = 20.0, 180.0


def exact(klr: float) -> float:
    return aisc_e3_critical_stress(klr, FY, E)[0] / FY


def norm(klr: float) -> float:
    return (klr - LO) / (HI - LO)


def main() -> None:
    train = [LO + i * (HI - LO) / 8 for i in range(9)]
    for length in (0.10, 0.25, 0.50):
        k = KrigingSurrogate(X=[[norm(x)] for x in train], y=[exact(x) for x in train], length=length).fit()
        test = [LO + (i + 0.5) * (HI - LO) / 33 for i in range(33)]
        errs = [abs(k.predict([norm(x)]) - exact(x)) for x in test]
        worst = max(zip(errs, test))
        print(f"longitud {length:.2f}: error máximo {worst[0]:.4f} (en KL/r = {worst[1]:.0f}), "
              f"medio {sum(errs) / len(errs):.4f} sobre Fcr/Fy")
    k = KrigingSurrogate(X=[[norm(x)] for x in train], y=[exact(x) for x in train], length=0.25).fit()
    print("\nLongitud 0,25 — predicción frente a la curva exacta:")
    print(f"  {'KL/r':>5} {'exacto':>7} {'Kriging':>8}")
    for x in (25, 60, 100, 113.4, 140, 175):
        print(f"  {x:5.1f} {exact(x):7.4f} {k.predict([norm(x)]):8.4f}")
    print("  Fuera del rango muestreado:")
    for x in (0.0, 200.0, 260.0):
        print(f"  {x:5.1f} {exact(x):7.4f} {k.predict([norm(x)]):8.4f}")
    far = k.predict([norm(400.0)])
    print(f"\nEn KL/r = 400 el Kriging predice {far:.4f} (exacto {exact(400.0):.4f}): con media nula la "
          "predicción decae hacia 0 al alejarse de los datos. Úsalo solo para interpolar dentro del muestreo.")


if __name__ == "__main__":
    main()
