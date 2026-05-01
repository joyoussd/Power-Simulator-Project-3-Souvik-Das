

import numpy as np
import pandas as pd


class SymmetricalFault:
    """Three-phase bolted-fault solver."""

    def __init__(self, circuit):
        self.circuit = circuit
        self.bus_names: list[str] = list(circuit.buses.keys())
        self.bus_idx: dict[str, int] = {n: i for i, n in enumerate(self.bus_names)}

        # Outputs populated after run().
        self.fault_current: complex | None = None
        self.fault_voltages: pd.Series | None = None

    def run(self, faulted_bus: str,
            v_prefault: complex = 1.0 + 0.0j,
            zf: complex = 0.0 + 0.0j) -> tuple[complex, pd.Series]:
        """
        Solve a symmetrical fault at faulted_bus.

        Parameters
        ----------
        faulted_bus : name of the bus where the fault occurs
        v_prefault  : prefault Thevenin voltage at the faulted bus (per unit)
        zf          : fault impedance (0 for a bolted fault)

        Returns
        -------
        (I_fault, V_post)   complex fault current and a Series of post-fault
                            voltages indexed by bus name.
        """
        if faulted_bus not in self.bus_idx:
            raise KeyError(f"Bus '{faulted_bus}' not in circuit.")

        # Build / refresh the sequence Ybus matrices.
        if self.circuit.y1bus is None:
            self.circuit.calc_sequence_ybus()
        Y1 = self.circuit.y1bus.values
        Z1 = np.linalg.inv(Y1)

        n = self.bus_idx[faulted_bus]
        Z1nn = Z1[n, n]

        # Subtransient fault current.
        I_f = v_prefault / (Z1nn + zf)

        # Post-fault voltage at every bus (superposition).
        V_post = np.zeros(len(self.bus_names), dtype=complex)
        for k in range(len(self.bus_names)):
            V_post[k] = v_prefault - Z1[k, n] * I_f

        self.fault_current = I_f
        self.fault_voltages = pd.Series(V_post, index=self.bus_names,
                                        name=f"V_post (3ph fault @ {faulted_bus})")
        return I_f, self.fault_voltages
