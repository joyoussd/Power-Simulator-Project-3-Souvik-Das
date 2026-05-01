
import sys
sys.path.insert(0, '/home/claude/power_system_extension/src')

import numpy as np
from five_bus_system import build_five_bus_system
from Solver import Solver

# Build system and run power flow first
c = build_five_bus_system()
c.calc_ybus()
c.calc_sequence_ybus()

solver = Solver(c)

print("="*72)
print("Sequence Ybus matrices:")
print()
print("Y1bus (positive-sequence):")
print(c.y1bus.round(3))
print()
print("Y2bus (negative-sequence):")
print(c.y2bus.round(3))
print()
print("Y0bus (zero-sequence):")
print(c.y0bus.round(3))

# Test all 4 fault types at Bus 4
print("\n" + "#"*72)
print("Fault analyses at Bus 4 (bolted)")
print("#"*72)

for ftype in ("3ph", "SLG", "LL", "DLG"):
    print(f"\n--- {ftype} fault ---")
    res = solver.run_fault(ftype, "Bus 4", zf=0.0)
    print(f"  Sequence currents I012 (pu):")
    for label, val in zip(("I0", "I1", "I2"), res["I012"]):
        print(f"    {label}: |{label}| = {abs(val):.4f}, ∠ = {np.rad2deg(np.angle(val)):.2f}°")
    print(f"  Phase currents Iabc (pu):")
    for label, val in zip(("Ia", "Ib", "Ic"), res["Iabc"]):
        print(f"    {label}: |{label}| = {abs(val):.4f}, ∠ = {np.rad2deg(np.angle(val)):.2f}°")
    print(f"  Largest phase current magnitude: {res['I_fault_mag']:.4f} pu")
