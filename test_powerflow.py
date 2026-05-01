
import sys
sys.path.insert(0, '/home/claude/power_system_extension/src')

from five_bus_system import build_five_bus_system
from PowerFlow import PowerFlow

c = build_five_bus_system()
c.calc_ybus()
print("Ybus:")
print(c.ybus.round(3))
print()

pf = PowerFlow(c)
converged, n_iter, V, delta = pf.solve(tol=1e-4, max_iter=50, verbose=True)
print()
print(f"Converged: {converged} in {n_iter} iterations")
print()
print("Final bus voltages:")
for name, bus in c.buses.items():
    print(f"  {name}: |V| = {bus.vpu:.4f} pu, δ = {bus.delta:.4f}°")
