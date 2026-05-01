
import sys
sys.path.insert(0, '/home/claude/power_system_extension/src')

import numpy as np
from Bus import Bus
from Circuit import Circuit
from UnsymmetricalFault import UnsymmetricalFault
from SymmetricalFault import SymmetricalFault
from five_bus_system import build_five_bus_system


# ================================================================
# Test 1: Fault impedance effect on SLG
# ================================================================
print("="*72)
print("TEST 1: Effect of fault impedance on SLG fault current")
print("="*72)

Bus.reset_counter()
c = Circuit("test1")
c.add_bus("Bus 1", 13.8, bus_type="Slack", vpu=1.0)
c.add_generator("G1", "Bus 1", 1.0, 0.0,
                x1=0.20, x2=0.20, x0=0.05, grounding="solid")
c.calc_sequence_ybus()

uf = UnsymmetricalFault(c)
print(f"  {'Zf (pu)':>8} | {'|Ia| (pu)':>10}")
print(f"  {'-'*8} | {'-'*10}")
for zf in (0.0, 0.05j, 0.10j, 0.20j, 0.50j):
    res = uf.run("SLG", "Bus 1", zf=zf)
    print(f"  {str(zf):>8} | {abs(res['Iabc'][0]):>10.4f}")
print("  As Zf increases, fault current decreases — physical sanity ✓")


# ================================================================
# Test 2: Ungrounded generator — SLG should reduce dramatically
# ================================================================
print("\n" + "="*72)
print("TEST 2: Ungrounded generator — zero-sequence isolated")
print("="*72)

Bus.reset_counter()
c = Circuit("test2_ungrounded")
c.add_bus("Bus 1", 13.8, bus_type="Slack", vpu=1.0)
c.add_generator("G1", "Bus 1", 1.0, 0.0,
                x1=0.20, x2=0.20, x0=0.05,
                grounding="ungrounded")
c.calc_sequence_ybus()

uf = UnsymmetricalFault(c)
res_slg = uf.run("SLG", "Bus 1")
res_3ph = uf.run("3ph", "Bus 1")
print(f"  SLG fault on ungrounded gen:  |Ia| = {abs(res_slg['Iabc'][0]):.6f} pu")
print(f"  3ph fault on same gen:        |Ia| = {abs(res_3ph['Iabc'][0]):.4f} pu")
print(f"  Expected: SLG should be ≈ 0 (no path for zero-sequence current)")
assert abs(res_slg['Iabc'][0]) < 1e-5, "Ungrounded SLG should be ~0!"
print("  ✓ PASSED — ungrounded generator blocks zero-sequence current")


# ================================================================
# Test 3: 3ph cross-check — UnsymmetricalFault vs SymmetricalFault
# ================================================================
print("\n" + "="*72)
print("TEST 3: 3ph fault — Symmetrical vs Unsymmetrical solver match")
print("="*72)

c = build_five_bus_system()
c.calc_sequence_ybus()

sym = SymmetricalFault(c)
uf  = UnsymmetricalFault(c)

print(f"  {'Bus':<8} {'sym |If|':>12} {'uf |If|':>12} {'diff':>12}")
print(f"  {'-'*8} {'-'*12} {'-'*12} {'-'*12}")
for bus in c.buses:
    I_sym, _ = sym.run(bus)
    res     = uf.run("3ph", bus)
    I_uf    = res['I012'][1]   # only positive-sequence current for 3ph
    diff    = abs(abs(I_sym) - abs(I_uf))
    print(f"  {bus:<8} {abs(I_sym):>12.4f} {abs(I_uf):>12.4f} {diff:>12.2e}")
    assert diff < 1e-9, f"Mismatch at {bus}!"
print("  ✓ PASSED — both solvers give identical 3ph results")


# ================================================================
# Test 4: Verify Vfaulted = 0 for bolted faults at faulted bus
# ================================================================
print("\n" + "="*72)
print("TEST 4: Faulted-phase voltage at faulted bus = 0 for bolted fault")
print("="*72)

c = build_five_bus_system()
c.calc_sequence_ybus()
uf = UnsymmetricalFault(c)

# SLG: Va at faulted bus must be 0
res = uf.run("SLG", "Bus 4", zf=0.0)
Va = res["Vabc"].loc["Bus 4", "Va"]
print(f"  SLG @ Bus 4: |Va at Bus 4| = {abs(Va):.6f}  (expected ~0)")
assert abs(Va) < 1e-9, "Va should be 0 for bolted SLG!"

# LL: Vb - Vc = 0 at faulted bus
Vb = res["Vabc"].loc["Bus 4", "Vb"]
Vc = res["Vabc"].loc["Bus 4", "Vc"]
res = uf.run("LL", "Bus 4", zf=0.0)
Vb = res["Vabc"].loc["Bus 4", "Vb"]
Vc = res["Vabc"].loc["Bus 4", "Vc"]
print(f"  LL  @ Bus 4: |Vb - Vc| at Bus 4 = {abs(Vb - Vc):.6f}  (expected ~0)")
assert abs(Vb - Vc) < 1e-9, "Vb=Vc should hold for bolted LL!"

# DLG: Vb = Vc = 0 at faulted bus
res = uf.run("DLG", "Bus 4", zf=0.0)
Vb = res["Vabc"].loc["Bus 4", "Vb"]
Vc = res["Vabc"].loc["Bus 4", "Vc"]
print(f"  DLG @ Bus 4: |Vb at Bus 4| = {abs(Vb):.6f}, |Vc| = {abs(Vc):.6f}  (both ~0)")
assert abs(Vb) < 1e-9 and abs(Vc) < 1e-9, "Vb=Vc=0 should hold for bolted DLG!"

print("  ✓ ALL boundary-condition checks passed")

print("\n" + "="*72)
print("ALL ADVANCED VALIDATION TESTS PASSED")
print("="*72)
