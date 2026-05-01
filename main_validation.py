
import sys
sys.path.insert(0, '/home/claude/power_system_extension/src')

import numpy as np
import pandas as pd
from five_bus_system import build_five_bus_system
from Solver import Solver

# Pretty printing
pd.set_option("display.float_format", lambda x: f"{x:.4f}")
pd.set_option("display.width", 140)


def fmt_complex(z, decimals=4):
    """Return |z| ∠ angle° as a string."""
    return f"{abs(z):.{decimals}f} ∠ {np.rad2deg(np.angle(z)):>7.2f}°"


def print_section(title):
    print("\n" + "="*78)
    print(f"  {title}")
    print("="*78)


# ====================================================================
# STEP 1: Build the system
# ====================================================================
print_section("STEP 1 — Build the 5-bus Glover/Sarma test system")
circuit = build_five_bus_system()
print(circuit)
print()
for name, bus in circuit.buses.items():
    print(f"  {bus}")


# ====================================================================
# STEP 2: Run power flow
# ====================================================================
print_section("STEP 2 — Newton–Raphson power flow")
solver = Solver(circuit)
converged, n_iter, V, delta = solver.run_powerflow(tol=1e-4, verbose=True)
print(f"\nConverged in {n_iter} iterations.")
print("\nPrefault bus voltages:")
print(f"  {'Bus':<8} {'|V| (pu)':>10} {'angle (°)':>12} {'type':>8}")
for name, bus in circuit.buses.items():
    print(f"  {name:<8} {bus.vpu:>10.4f} {bus.delta:>12.4f} {bus.bus_type:>8}")


# ====================================================================
# STEP 3: Sequence Ybus / Zbus
# ====================================================================
print_section("STEP 3 — Sequence admittance and impedance matrices")
circuit.calc_sequence_ybus()
Z1, Z2, Z0 = circuit.calc_sequence_zbus()

print("\nY1bus (positive sequence) — diagonals:")
for b in circuit.buses:
    print(f"  Y1[{b}, {b}] = {circuit.y1bus.loc[b, b]:.4f}")

print("\nThevenin sequence impedances (diagonals of Zbus):")
print(f"  {'Bus':<8} {'Z1':>20} {'Z2':>20} {'Z0':>20}")
for b in circuit.buses:
    z1 = Z1.loc[b, b]; z2 = Z2.loc[b, b]; z0 = Z0.loc[b, b]
    print(f"  {b:<8} "
          f"{f'{z1.real:+.4f}{z1.imag:+.4f}j':>20} "
          f"{f'{z2.real:+.4f}{z2.imag:+.4f}j':>20} "
          f"{f'{z0.real:+.4f}{z0.imag:+.4f}j':>20}")


# ====================================================================
# STEP 4: Fault studies — every type, every bus
# ====================================================================
print_section("STEP 4 — Fault analysis at every bus")

fault_types = ("3ph", "SLG", "LL", "DLG")
results_table = []

for ftype in fault_types:
    for bus in circuit.buses:
        res = solver.run_fault(ftype, bus, zf=0.0)
        Iabc = res["Iabc"]
        results_table.append({
            "Fault Type":  ftype,
            "Faulted Bus": bus,
            "|Ia| (pu)":   abs(Iabc[0]),
            "|Ib| (pu)":   abs(Iabc[1]),
            "|Ic| (pu)":   abs(Iabc[2]),
            "Max |I| (pu)": float(np.max(np.abs(Iabc))),
        })

results_df = pd.DataFrame(results_table)
print(results_df.to_string(index=False))


# ====================================================================
# STEP 5: Detailed report for SLG fault at Bus 4 (typical study bus)
# ====================================================================
print_section("STEP 5 — Detailed example: SLG fault at Bus 4")
res = solver.run_fault("SLG", "Bus 4", zf=0.0)

print("\nSequence currents at faulted bus (per unit):")
for label, val in zip(("I0", "I1", "I2"), res["I012"]):
    print(f"  {label}: {fmt_complex(val)}")

print("\nPhase currents at faulted bus (per unit):")
for label, val in zip(("Ia", "Ib", "Ic"), res["Iabc"]):
    print(f"  {label}: {fmt_complex(val)}")

print("\nPost-fault sequence voltages (per unit):")
print(res["V012"].apply(lambda col: col.apply(lambda z: fmt_complex(z))).to_string())

print("\nPost-fault phase voltages (per unit):")
print(res["Vabc"].apply(lambda col: col.apply(lambda z: fmt_complex(z))).to_string())


# ====================================================================
# STEP 6: Comparison summary — fault current magnitudes
# ====================================================================
print_section("STEP 6 — Comparison: fault current magnitudes by type")

# Build a clean comparison table
summary = pd.DataFrame(index=list(circuit.buses.keys()),
                       columns=fault_types, dtype=float)
for ftype in fault_types:
    for bus in circuit.buses:
        res = solver.run_fault(ftype, bus, zf=0.0)
        summary.loc[bus, ftype] = float(np.max(np.abs(res["Iabc"])))

print("\nMaximum phase fault current magnitude (pu) by fault type and bus:")
print(summary.to_string())

print("\nObservations:")
print("  • SLG faults often produce the LARGEST current at low-impedance,")
print("    well-grounded buses near a generator — this drives breaker sizing.")
print("  • 3ph faults are the most symmetric and only exercise positive seq.")
print("  • LL faults have the smallest fault current of the three unbalanced")
print("    types because no zero-sequence path is involved.")
print("  • DLG fault currents are sensitive to grounding and zero-sequence Z.")

print("\n" + "="*78)
print("  END OF VALIDATION RUN")
print("="*78)


# ====================================================================
# Save key artifacts to disk for the report
# ====================================================================
import os
out_dir = "/home/claude/power_system_extension/validation"
os.makedirs(out_dir, exist_ok=True)

summary.to_csv(f"{out_dir}/fault_current_summary.csv")
results_df.to_csv(f"{out_dir}/fault_full_results.csv", index=False)
circuit.y1bus.to_csv(f"{out_dir}/y1bus.csv")
circuit.y2bus.to_csv(f"{out_dir}/y2bus.csv")
circuit.y0bus.to_csv(f"{out_dir}/y0bus.csv")
print(f"\nResults written to {out_dir}/")
