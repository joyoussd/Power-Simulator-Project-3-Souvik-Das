"""make_plots.py — generate result figures for the technical report."""
import sys
sys.path.insert(0, '/home/claude/power_system_extension/src')

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from five_bus_system import build_five_bus_system
from Solver import Solver

# Build the system and run faults
circuit = build_five_bus_system()
solver = Solver(circuit)
circuit.calc_sequence_ybus()

fault_types = ("3ph", "SLG", "LL", "DLG")
buses = list(circuit.buses.keys())

# Build comparison matrix
data = pd.DataFrame(index=buses, columns=fault_types, dtype=float)
for ftype in fault_types:
    for b in buses:
        res = solver.run_fault(ftype, b, zf=0.0)
        data.loc[b, ftype] = float(np.max(np.abs(res["Iabc"])))

# Plot 1: Bar chart of fault currents
fig, ax = plt.subplots(figsize=(10, 6))
data.plot(kind="bar", ax=ax, width=0.8,
          color=["#1f77b4", "#d62728", "#2ca02c", "#ff7f0e"])
ax.set_ylabel("Maximum Phase Fault Current (pu)", fontsize=11)
ax.set_xlabel("Faulted Bus", fontsize=11)
ax.set_title("Fault Current Magnitude by Fault Type and Bus\n"
             "(5-bus Glover/Sarma system, bolted faults, $V_f$ = 1.0 pu)",
             fontsize=12)
ax.legend(title="Fault Type", loc="upper right", framealpha=0.9)
ax.grid(axis="y", linestyle="--", alpha=0.5)
ax.set_xticklabels(buses, rotation=0)
plt.tight_layout()
plt.savefig("/home/claude/power_system_extension/validation/fault_comparison_bar.png",
            dpi=150)
plt.close()

# Plot 2: Effect of Zf on SLG fault at Bus 4
zf_values = np.linspace(0, 0.5, 21)
ia_mags = []
for zf in zf_values:
    res = solver.run_fault("SLG", "Bus 4", zf=1j*zf)
    ia_mags.append(abs(res["Iabc"][0]))

fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(zf_values, ia_mags, "o-", color="#d62728", linewidth=2, markersize=6)
ax.set_xlabel(r"Fault impedance $|Z_f|$ (pu, purely reactive)", fontsize=11)
ax.set_ylabel(r"$|I_a|$ at faulted bus (pu)", fontsize=11)
ax.set_title("SLG Fault Current vs Fault Impedance (Bus 4)", fontsize=12)
ax.grid(linestyle="--", alpha=0.5)
plt.tight_layout()
plt.savefig("/home/claude/power_system_extension/validation/slg_zf_sweep.png", dpi=150)
plt.close()

# Plot 3: Phase voltage profile during SLG fault at Bus 4
res = solver.run_fault("SLG", "Bus 4", zf=0.0)
vabc = res["Vabc"]
mags = vabc.map(abs)

fig, ax = plt.subplots(figsize=(9, 5))
x = np.arange(len(buses))
w = 0.27
ax.bar(x - w, mags["Va"], w, label="|Va|", color="#d62728")
ax.bar(x,     mags["Vb"], w, label="|Vb|", color="#2ca02c")
ax.bar(x + w, mags["Vc"], w, label="|Vc|", color="#1f77b4")
ax.set_xticks(x)
ax.set_xticklabels(buses)
ax.set_ylabel("Voltage Magnitude (pu)", fontsize=11)
ax.set_xlabel("Bus", fontsize=11)
ax.set_title("Post-Fault Phase Voltages — SLG Fault at Bus 4 (bolted)",
             fontsize=12)
ax.axhline(1.0, color="gray", linestyle=":", linewidth=1, alpha=0.5)
ax.legend()
ax.grid(axis="y", linestyle="--", alpha=0.5)
plt.tight_layout()
plt.savefig("/home/claude/power_system_extension/validation/slg_voltage_profile.png",
            dpi=150)
plt.close()

print("Plots saved to /home/claude/power_system_extension/validation/")
print("  - fault_comparison_bar.png")
print("  - slg_zf_sweep.png")
print("  - slg_voltage_profile.png")
