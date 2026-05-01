

from PowerFlow import PowerFlow
from SymmetricalFault import SymmetricalFault
from UnsymmetricalFault import UnsymmetricalFault


class Solver:
    """Single interface to power flow and all fault types."""

    def __init__(self, circuit):
        self.circuit = circuit
        # Sub-solver instances are created on demand.
        self._pf: PowerFlow | None = None
        self._sym_fault: SymmetricalFault | None = None
        self._unsym_fault: UnsymmetricalFault | None = None

    # ------------------------------------------------------------------
    # Power flow
    # ------------------------------------------------------------------
    def run_powerflow(self, tol: float = 1e-3, max_iter: int = 50,
                      sbase: float = 100.0, verbose: bool = False):
        self._pf = PowerFlow(self.circuit)
        return self._pf.solve(tol=tol, max_iter=max_iter,
                              sbase=sbase, verbose=verbose)

    # ------------------------------------------------------------------
    # Fault study (one mode for both 3-phase and unbalanced faults)
    # ------------------------------------------------------------------
    def run_fault(self, fault_type: str, faulted_bus: str,
                  zf: complex = 0.0 + 0.0j,
                  v_prefault: complex = 1.0 + 0.0j) -> dict:
        """
        Run a fault study.

        fault_type :
            '3ph' - balanced three-phase fault (uses positive-sequence only,
                    same answer as the SymmetricalFault class).
            'SLG' - single line-to-ground.
            'LL'  - line-to-line.
            'DLG' - double line-to-ground.
        """
        self._unsym_fault = UnsymmetricalFault(self.circuit)
        return self._unsym_fault.run(fault_type=fault_type,
                                     faulted_bus=faulted_bus,
                                     zf=zf,
                                     v_prefault=v_prefault)

    # ------------------------------------------------------------------
    # Top-level mode dispatch
    # ------------------------------------------------------------------
    def solve(self, mode: str = "powerflow", **kwargs):
        if mode == "powerflow":
            return self.run_powerflow(**kwargs)
        elif mode == "fault":
            return self.run_fault(**kwargs)
        else:
            raise ValueError(f"Unknown mode '{mode}'. "
                             "Must be 'powerflow' or 'fault'.")
