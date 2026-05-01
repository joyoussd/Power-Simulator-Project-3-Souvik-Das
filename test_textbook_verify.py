
import sys
sys.path.insert(0, '/home/claude/power_system_extension/src')

import numpy as np
from Bus import Bus
from Circuit import Circuit
from UnsymmetricalFault import UnsymmetricalFault


def build_single_bus_system():
    """A single generator + bus, used for hand-verification of fault math."""
    Bus.reset_counter()
    c = Circuit("single_bus_test")
    c.add_bus("Bus 1", 13.8, bus_type="Slack", vpu=1.0)
    c.add_generator("G1", "Bus 1",
                    voltage_setpoint=1.0,
                    mw_setpoint=0.0,
                    x1=0.20, x2=0.20, x0=0.05,
                    grounding="solid")
    return c


print("="*72)
print("Textbook verification — single-machine test system")
print("X1=X2=0.20, X0=0.05, solidly grounded, Vf=1.0 pu, Zf=0")
print("="*72)

c = build_single_bus_system()
c.calc_sequence_ybus()

# Print sequence Z at the faulted bus
Z1, Z2, Z0 = c.calc_sequence_zbus()
print(f"\nThevenin impedances at Bus 1:")
print(f"  Z1 = {Z1.iloc[0,0]:.6f}")
print(f"  Z2 = {Z2.iloc[0,0]:.6f}")
print(f"  Z0 = {Z0.iloc[0,0]:.6f}")

uf = UnsymmetricalFault(c)

print("\n--- SLG fault ---")
res = uf.run("SLG", "Bus 1")
print(f"  Computed Ia = {res['Iabc'][0]:.4f}")
print(f"  Expected Ia = 0 - 6.6667j  (magnitude 6.6667)")
print(f"  Match? mag = {abs(res['Iabc'][0]):.4f}, expected 6.6667")
expected_slg = 6.0 + 2.0/3.0  # 6.6667
assert abs(abs(res['Iabc'][0]) - expected_slg) < 1e-3, "SLG check FAILED"
print("  ✓ PASSED")

print("\n--- LL fault ---")
res = uf.run("LL", "Bus 1")
print(f"  Computed Ib = {res['Iabc'][1]:.4f} (mag {abs(res['Iabc'][1]):.4f})")
print(f"  Computed Ic = {res['Iabc'][2]:.4f} (mag {abs(res['Iabc'][2]):.4f})")
print(f"  Expected |Ib| = |Ic| = sqrt(3) * 2.5 = {np.sqrt(3)*2.5:.4f}")
expected_ll = np.sqrt(3) * 2.5
assert abs(abs(res['Iabc'][1]) - expected_ll) < 1e-3, "LL check FAILED"
print("  ✓ PASSED")

print("\n--- DLG fault ---")
res = uf.run("DLG", "Bus 1")
print(f"  Computed I0 = {res['I012'][0]:.4f}  (expected 0+3.333j)")
print(f"  Computed I1 = {res['I012'][1]:.4f}  (expected 0-4.167j)")
print(f"  Computed I2 = {res['I012'][2]:.4f}  (expected 0+0.833j)")
print(f"  Computed Ia = {res['Iabc'][0]:.4f}  (expected 0)")
assert abs(res['Iabc'][0]) < 1e-3, "DLG: Ia should be 0!"
assert abs(abs(res['I012'][1]) - 25.0/6.0) < 1e-3, "DLG I1 check FAILED"  # 4.1667
print("  ✓ PASSED")

print("\n" + "="*72)
print("ALL TEXTBOOK VERIFICATION CHECKS PASSED!")
print("="*72)
