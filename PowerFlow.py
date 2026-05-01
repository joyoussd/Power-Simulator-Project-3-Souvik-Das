

import numpy as np


class PowerFlow:
    """Newton–Raphson solver for the power-flow problem."""

    def __init__(self, circuit):
        self.circuit = circuit

        # Cached arrays populated by solve().
        self.bus_names: list[str] = list(circuit.buses.keys())
        self.N: int = len(self.bus_names)
        self.bus_idx: dict[str, int] = {n: i for i, n in enumerate(self.bus_names)}

        # Lists of bus indices grouped by type — built once at the start of solve().
        self.slack_idx: list[int] = []
        self.pv_idx: list[int] = []
        self.pq_idx: list[int] = []

        # Final iteration results — populated after a successful solve.
        self.iterations: int = 0
        self.converged: bool = False
        self.final_mismatch: float = float('inf')

    # ------------------------------------------------------------------
    # Bus type bookkeeping
    # ------------------------------------------------------------------
    def _classify_buses(self):
        self.slack_idx = []
        self.pv_idx = []
        self.pq_idx = []
        for name, bus in self.circuit.buses.items():
            i = self.bus_idx[name]
            if bus.bus_type == "Slack":
                self.slack_idx.append(i)
            elif bus.bus_type == "PV":
                self.pv_idx.append(i)
            else:
                self.pq_idx.append(i)

    # ------------------------------------------------------------------
    # Specified (scheduled) power injections
    # ------------------------------------------------------------------
    def _scheduled_powers(self, sbase: float = 100.0):
        """Return arrays of scheduled P and Q at every bus (per-unit).
        P_spec = generation - load; Q_spec = -load (no reactive scheduling for
        PV buses since they regulate voltage)."""
        P_spec = np.zeros(self.N)
        Q_spec = np.zeros(self.N)

        for g in self.circuit.generators.values():
            i = self.bus_idx[g.bus1_name]
            P_spec[i] += g.mw_setpoint / sbase

        for ld in self.circuit.loads.values():
            i = self.bus_idx[ld.bus1_name]
            P_spec[i] -= ld.mw / sbase
            Q_spec[i] -= ld.mvar / sbase

        return P_spec, Q_spec

    # ------------------------------------------------------------------
    # Milestone 6: power injection from V, δ, Ybus
    # ------------------------------------------------------------------
    @staticmethod
    def compute_power_injection(V: np.ndarray, delta: np.ndarray,
                                Ybus: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Compute P and Q injections at every bus given voltage magnitudes
        V, angles δ (radians), and the system Ybus."""
        N = len(V)
        G = Ybus.real
        B = Ybus.imag
        P = np.zeros(N)
        Q = np.zeros(N)
        for i in range(N):
            for j in range(N):
                dij = delta[i] - delta[j]
                P[i] += V[i] * V[j] * (G[i, j] * np.cos(dij) + B[i, j] * np.sin(dij))
                Q[i] += V[i] * V[j] * (G[i, j] * np.sin(dij) - B[i, j] * np.cos(dij))
        return P, Q

    # ------------------------------------------------------------------
    # Milestone 6: mismatch vector f = [ΔP_nonslack ; ΔQ_PQ]
    # ------------------------------------------------------------------
    def compute_mismatch(self, V: np.ndarray, delta: np.ndarray,
                         Ybus: np.ndarray, P_spec: np.ndarray,
                         Q_spec: np.ndarray) -> np.ndarray:
        P_calc, Q_calc = self.compute_power_injection(V, delta, Ybus)
        dP = P_spec - P_calc
        dQ = Q_spec - Q_calc

        # ΔP at every non-slack bus
        non_slack = [i for i in range(self.N) if i not in self.slack_idx]
        f_p = dP[non_slack]
        # ΔQ only at PQ buses
        f_q = dQ[self.pq_idx]
        return np.concatenate([f_p, f_q])

    # ------------------------------------------------------------------
    # Milestone 7: Jacobian
    # ------------------------------------------------------------------
    def compute_jacobian(self, V: np.ndarray, delta: np.ndarray,
                         Ybus: np.ndarray) -> np.ndarray:
        """
        Construct the Jacobian J = [[J1 J2],[J3 J4]] with rows/columns for
        the slack bus removed and rows/columns for |V| at PV buses removed.

        J1 = ∂P/∂δ , J2 = ∂P/∂|V| , J3 = ∂Q/∂δ , J4 = ∂Q/∂|V|

        We follow the standard formulas from Glover/Sarma chapter 6.
        """
        N = self.N
        G = Ybus.real
        B = Ybus.imag

        # Pre-compute the full N×N submatrices.
        J1 = np.zeros((N, N))   # dP/dδ
        J2 = np.zeros((N, N))   # dP/d|V|
        J3 = np.zeros((N, N))   # dQ/dδ
        J4 = np.zeros((N, N))   # dQ/d|V|

        # First compute calculated P, Q for use in the diagonal terms.
        P_calc, Q_calc = self.compute_power_injection(V, delta, Ybus)

        for i in range(N):
            for k in range(N):
                if i == k:
                    # Diagonals
                    J1[i, k] = -Q_calc[i] - B[i, i] * V[i]**2
                    J2[i, k] =  P_calc[i] / V[i] + G[i, i] * V[i]
                    J3[i, k] =  P_calc[i] - G[i, i] * V[i]**2
                    J4[i, k] =  Q_calc[i] / V[i] - B[i, i] * V[i]
                else:
                    dik = delta[i] - delta[k]
                    sin_d = np.sin(dik)
                    cos_d = np.cos(dik)
                    J1[i, k] =  V[i] * V[k] * (G[i, k] * sin_d - B[i, k] * cos_d)
                    J2[i, k] =  V[i]        * (G[i, k] * cos_d + B[i, k] * sin_d)
                    J3[i, k] = -V[i] * V[k] * (G[i, k] * cos_d + B[i, k] * sin_d)
                    J4[i, k] =  V[i]        * (G[i, k] * sin_d - B[i, k] * cos_d)

        # Now slice out the rows/columns we don't need.
        non_slack = [i for i in range(N) if i not in self.slack_idx]
        # Rows: ΔP at non-slack ; ΔQ at PQ only
        # Cols: δ at non-slack  ; |V| at PQ only
        J1_red = J1[np.ix_(non_slack, non_slack)]
        J2_red = J2[np.ix_(non_slack, self.pq_idx)]
        J3_red = J3[np.ix_(self.pq_idx, non_slack)]
        J4_red = J4[np.ix_(self.pq_idx, self.pq_idx)]

        # Assemble the full Jacobian
        top = np.hstack([J1_red, J2_red])
        bot = np.hstack([J3_red, J4_red])
        return np.vstack([top, bot])

    # ------------------------------------------------------------------
    # Milestone 8: Newton–Raphson iteration loop
    # ------------------------------------------------------------------
    def solve(self, tol: float = 1e-3, max_iter: int = 50,
              sbase: float = 100.0, verbose: bool = False):
        """Run Newton–Raphson until convergence or max_iter reached.
        Updates the Bus objects' vpu/delta attributes in place."""
        self._classify_buses()

        if self.circuit.ybus is None:
            self.circuit.calc_ybus()
        Ybus = self.circuit.ybus.values

        # Flat start for any value the user has not overridden — this matches
        # the Milestone 8 specification.
        V = np.ones(self.N)
        delta = np.zeros(self.N)
        for name, bus in self.circuit.buses.items():
            i = self.bus_idx[name]
            if bus.bus_type in ("Slack", "PV"):
                V[i] = bus.vpu
            delta[i] = np.deg2rad(bus.delta)

        # Override PV-bus voltage magnitudes with the generator setpoint.
        for g in self.circuit.generators.values():
            i = self.bus_idx[g.bus1_name]
            if self.circuit.buses[g.bus1_name].bus_type in ("Slack", "PV"):
                V[i] = g.voltage_setpoint

        P_spec, Q_spec = self._scheduled_powers(sbase)

        non_slack = [i for i in range(self.N) if i not in self.slack_idx]

        self.converged = False
        for it in range(max_iter):
            f = self.compute_mismatch(V, delta, Ybus, P_spec, Q_spec)
            mismatch_norm = np.max(np.abs(f))
            if verbose:
                print(f"Iter {it}: max|f| = {mismatch_norm:.6e}")
            if mismatch_norm < tol:
                self.converged = True
                self.iterations = it
                self.final_mismatch = mismatch_norm
                break

            J = self.compute_jacobian(V, delta, Ybus)
            try:
                dx = np.linalg.solve(J, f)
            except np.linalg.LinAlgError as err:
                raise RuntimeError(f"Jacobian singular at iter {it}: {err}")

            # Apply the corrections.
            n_p = len(non_slack)
            d_delta = dx[:n_p]
            d_V     = dx[n_p:]

            for k, i in enumerate(non_slack):
                delta[i] += d_delta[k]
            for k, i in enumerate(self.pq_idx):
                V[i] += d_V[k]
        else:
            self.iterations = max_iter
            self.final_mismatch = mismatch_norm

        # Write results back to Bus objects.
        for name, bus in self.circuit.buses.items():
            i = self.bus_idx[name]
            bus.vpu = V[i]
            bus.delta = np.rad2deg(delta[i])

        return self.converged, self.iterations, V, delta
