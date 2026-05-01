"""
UnsymmetricalFault.py
=====================
Unsymmetrical (asymmetrical) fault analysis via symmetrical components.

Project 2 extension

This class implements the three classical unbalanced-fault types:
  - SLG  : Single Line-to-Ground fault          (phase a faulted)
  - LL   : Line-to-Line fault                   (phases b and c)
  - DLG  : Double Line-to-Ground fault          (phases b and c to ground)

THEORY (Glover, Sarma & Overbye, Chapter 9):
The Fortescue transformation decomposes an unbalanced 3-phase phasor
set [Va, Vb, Vc] into three balanced sequence sets:

    [V0]     1  [1  1  1 ] [Va]
    [V1] =  --- [1  a  a²] [Vb]
    [V2]     3  [1  a² a ] [Vc]                      a = exp(j*2π/3)

For a fault at bus k, the Thevenin sequence impedances seen from bus k
are the diagonal elements of the sequence bus-impedance matrices:
    Z1_kk = Z1bus[k,k] ,  Z2_kk = Z2bus[k,k] ,  Z0_kk = Z0bus[k,k]

The three fault types differ only in their boundary conditions, which
yield the following sequence-current expressions (Vf is the prefault
voltage at bus k, Zf is the fault impedance):

  SLG (phase a to ground via Zf):
      I0 = I1 = I2 = Vf / (Z1_kk + Z2_kk + Z0_kk + 3*Zf)

  LL (phase b to phase c through Zf):
      I0 = 0
      I1 = -I2 = Vf / (Z1_kk + Z2_kk + Zf)

  DLG (phases b and c to ground through Zf each):
      I1 = Vf / [ Z1_kk + Z2_kk*(Z0_kk+3Zf) / (Z2_kk + Z0_kk + 3Zf) ]
      I2 = -I1 * (Z0_kk + 3Zf) / (Z2_kk + Z0_kk + 3Zf)
      I0 = -I1 *  Z2_kk        / (Z2_kk + Z0_kk + 3Zf)

After computing the sequence currents at the faulted bus, sequence
voltages at every bus k are recovered via superposition:
    V0_k = 0            - Z0bus[k, n] * I0_n
    V1_k = Vf_k         - Z1bus[k, n] * I1_n
    V2_k = 0            - Z2bus[k, n] * I2_n

Finally the inverse Fortescue transformation gives the abc voltages and
currents.

NOTE on prefault voltage assumption:
For consistency with the standard textbook approach we use the prefault
voltage Vf = 1.0∠0° pu at every bus (a flat profile). For higher-fidelity
results, the user can supply the converged power-flow voltages.
"""

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------
# The Fortescue transformation matrices
# --------------------------------------------------------------------------
# `a` is the 120° rotation operator, central to symmetrical components.
A_ROT = np.exp(1j * 2.0 * np.pi / 3.0)

# A : abc <- 012  (sequence-to-phase)
A_FORTESCUE = np.array([
    [1.0,        1.0,         1.0      ],
    [1.0,        A_ROT**2,    A_ROT    ],
    [1.0,        A_ROT,       A_ROT**2 ]
], dtype=complex)

# A^-1 : 012 <- abc  (phase-to-sequence)
A_INV = (1.0 / 3.0) * np.array([
    [1.0,     1.0,         1.0     ],
    [1.0,     A_ROT,       A_ROT**2],
    [1.0,     A_ROT**2,    A_ROT   ]
], dtype=complex)


def seq_to_phase(seq_vec: np.ndarray) -> np.ndarray:
    """Convert a length-3 sequence vector [V0, V1, V2] to phase [Va, Vb, Vc]."""
    return A_FORTESCUE @ seq_vec


def phase_to_seq(phase_vec: np.ndarray) -> np.ndarray:
    """Convert a length-3 phase vector [Va, Vb, Vc] to sequence [V0, V1, V2]."""
    return A_INV @ phase_vec


# --------------------------------------------------------------------------
# Main fault solver class
# --------------------------------------------------------------------------
class UnsymmetricalFault:
    """Solve SLG, LL, and DLG faults using symmetrical components."""

    VALID_TYPES = ("SLG", "LL", "DLG", "3ph")

    def __init__(self, circuit):
        self.circuit = circuit
        self.bus_names: list[str] = list(circuit.buses.keys())
        self.bus_idx: dict[str, int] = {n: i for i, n in enumerate(self.bus_names)}

        # Filled in after run().
        self.fault_type: str | None = None
        self.faulted_bus: str | None = None
        self.zf: complex = 0.0 + 0.0j
        self.v_prefault: complex = 1.0 + 0.0j

        # Sequence currents at the faulted bus.
        self.I012: np.ndarray | None = None        # [I0, I1, I2]
        # Phase currents at the faulted bus.
        self.Iabc: np.ndarray | None = None        # [Ia, Ib, Ic]
        # Per-bus sequence voltages: rows = bus, cols = [V0, V1, V2]
        self.V012: pd.DataFrame | None = None
        # Per-bus phase voltages:    rows = bus, cols = [Va, Vb, Vc]
        self.Vabc: pd.DataFrame | None = None

    # ----------------------------------------------------------------------
    # Public entry point
    # ----------------------------------------------------------------------
    def run(self,
            fault_type: str,
            faulted_bus: str,
            zf: complex = 0.0 + 0.0j,
            v_prefault: complex = 1.0 + 0.0j) -> dict:
        """
        Solve an unsymmetrical fault and return a results dictionary.

        Parameters
        ----------
        fault_type : 'SLG' | 'LL' | 'DLG' | '3ph'
        faulted_bus: name of the bus where the fault occurs
        zf         : fault impedance (per-unit). 0 = bolted fault.
        v_prefault : prefault voltage at the faulted bus (default 1.0∠0°).

        Returns
        -------
        dict with keys:
            'I012'           : sequence currents at faulted bus
            'Iabc'           : phase currents at faulted bus
            'V012'           : DataFrame of sequence voltages
            'Vabc'           : DataFrame of phase voltages
            'I_fault_mag'    : magnitude of the largest phase fault current
            'fault_type', 'faulted_bus', 'zf', 'v_prefault'
        """
        if fault_type not in self.VALID_TYPES:
            raise ValueError(
                f"fault_type must be one of {self.VALID_TYPES}, got '{fault_type}'."
            )
        if faulted_bus not in self.bus_idx:
            raise KeyError(f"Bus '{faulted_bus}' not in circuit.")

        # Make sure sequence Ybus matrices exist.
        if self.circuit.y1bus is None:
            self.circuit.calc_sequence_ybus()

        Y1 = self.circuit.y1bus.values
        Y2 = self.circuit.y2bus.values
        Y0 = self.circuit.y0bus.values

        # Invert to obtain sequence Zbus matrices.
        Z1 = np.linalg.inv(Y1)
        Z2 = np.linalg.inv(Y2)
        Z0 = np.linalg.inv(Y0)

        n = self.bus_idx[faulted_bus]
        Vf = v_prefault

        # Thevenin sequence impedances at the faulted bus.
        Z1nn = Z1[n, n]
        Z2nn = Z2[n, n]
        Z0nn = Z0[n, n]

        # ------------------------------------------------------------------
        # Compute sequence currents based on fault type
        # ------------------------------------------------------------------
        if fault_type == "SLG":
            # Single line-to-ground fault on phase a.
            I_seq = Vf / (Z1nn + Z2nn + Z0nn + 3.0 * zf)
            I0 = I1 = I2 = I_seq

        elif fault_type == "LL":
            # Line-to-line fault between phases b and c.
            I1 = Vf / (Z1nn + Z2nn + zf)
            I2 = -I1
            I0 = 0.0 + 0.0j

        elif fault_type == "DLG":
            # Double line-to-ground: phases b and c to ground via Zf each.
            denom_par = Z2nn + Z0nn + 3.0 * zf
            # Equivalent impedance is Z1 + Z2 in parallel with (Z0 + 3Zf).
            Z_par = (Z2nn * (Z0nn + 3.0 * zf)) / denom_par
            I1 = Vf / (Z1nn + Z_par)
            I2 = -I1 * (Z0nn + 3.0 * zf) / denom_par
            I0 = -I1 *  Z2nn               / denom_par

        elif fault_type == "3ph":
            # Provided for completeness — only positive sequence is involved.
            I1 = Vf / (Z1nn + zf)
            I0 = 0.0 + 0.0j
            I2 = 0.0 + 0.0j

        I012 = np.array([I0, I1, I2], dtype=complex)
        Iabc = seq_to_phase(I012)

        # ------------------------------------------------------------------
        # Compute sequence voltages at every bus by superposition
        # ------------------------------------------------------------------
        N = len(self.bus_names)
        V0 = np.zeros(N, dtype=complex)
        V1 = np.zeros(N, dtype=complex)
        V2 = np.zeros(N, dtype=complex)

        # Prefault voltage profile: positive-sequence Vf everywhere; 0 for
        # negative and zero sequences.
        for k in range(N):
            V0[k] = 0.0           - Z0[k, n] * I0
            V1[k] = Vf            - Z1[k, n] * I1
            V2[k] = 0.0           - Z2[k, n] * I2

        V012 = pd.DataFrame(np.column_stack([V0, V1, V2]),
                            index=self.bus_names,
                            columns=["V0", "V1", "V2"])

        # Inverse Fortescue: convert each row to abc.
        Vabc_arr = np.zeros((N, 3), dtype=complex)
        for k in range(N):
            Vabc_arr[k] = seq_to_phase(np.array([V0[k], V1[k], V2[k]]))
        Vabc = pd.DataFrame(Vabc_arr,
                            index=self.bus_names,
                            columns=["Va", "Vb", "Vc"])

        # Cache outputs.
        self.fault_type = fault_type
        self.faulted_bus = faulted_bus
        self.zf = zf
        self.v_prefault = Vf
        self.I012 = I012
        self.Iabc = Iabc
        self.V012 = V012
        self.Vabc = Vabc

        return {
            "fault_type":   fault_type,
            "faulted_bus":  faulted_bus,
            "zf":           zf,
            "v_prefault":   Vf,
            "I012":         I012,
            "Iabc":         Iabc,
            "V012":         V012,
            "Vabc":         Vabc,
            "I_fault_mag":  float(np.max(np.abs(Iabc))),
        }

    # ----------------------------------------------------------------------
    # Pretty-printing helpers
    # ----------------------------------------------------------------------
    def report(self) -> str:
        """Return a human-readable summary of the most recent fault solution."""
        if self.I012 is None:
            return "No fault solved yet."

        lines = []
        lines.append("=" * 72)
        lines.append(f"Fault report: {self.fault_type} fault at bus '{self.faulted_bus}'")
        lines.append(f"  Zf         = {self.zf}")
        lines.append(f"  V_prefault = {abs(self.v_prefault):.4f} ∠ "
                     f"{np.rad2deg(np.angle(self.v_prefault)):.2f}° pu")
        lines.append("-" * 72)
        lines.append("Sequence currents at faulted bus (per unit):")
        for label, val in zip(("I0", "I1", "I2"), self.I012):
            lines.append(f"  {label} = {abs(val):8.4f} ∠ "
                         f"{np.rad2deg(np.angle(val)):8.3f}°")
        lines.append("Phase currents at faulted bus (per unit):")
        for label, val in zip(("Ia", "Ib", "Ic"), self.Iabc):
            lines.append(f"  {label} = {abs(val):8.4f} ∠ "
                         f"{np.rad2deg(np.angle(val)):8.3f}°")
        lines.append("-" * 72)
        lines.append("Post-fault phase voltages (pu):")
        lines.append(f"  {'Bus':<10} {'|Va|':>8} {'∠Va':>8} "
                     f"{'|Vb|':>8} {'∠Vb':>8} {'|Vc|':>8} {'∠Vc':>8}")
        for bus in self.bus_names:
            row = self.Vabc.loc[bus]
            lines.append(
                f"  {bus:<10} "
                f"{abs(row['Va']):>8.4f} {np.rad2deg(np.angle(row['Va'])):>8.2f} "
                f"{abs(row['Vb']):>8.4f} {np.rad2deg(np.angle(row['Vb'])):>8.2f} "
                f"{abs(row['Vc']):>8.4f} {np.rad2deg(np.angle(row['Vc'])):>8.2f}"
            )
        lines.append("=" * 72)
        return "\n".join(lines)
