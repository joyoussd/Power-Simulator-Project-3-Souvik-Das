
import numpy as np
import pandas as pd

from Bus import Bus
from Transformer import Transformer
from TransmissionLine import TransmissionLine
from Generator import Generator
from Load import Load


class Circuit:
    """A complete power system network."""

    def __init__(self, name: str):
        self.name: str = name

        # Equipment dictionaries — keys are component names.
        self.buses: dict[str, Bus] = {}
        self.transformers: dict[str, Transformer] = {}
        self.transmission_lines: dict[str, TransmissionLine] = {}
        self.generators: dict[str, Generator] = {}
        self.loads: dict[str, Load] = {}

        # Network matrices populated by calc_ybus / calc_sequence_ybus.
        self.ybus: pd.DataFrame | None = None
        self.y1bus: pd.DataFrame | None = None
        self.y2bus: pd.DataFrame | None = None
        self.y0bus: pd.DataFrame | None = None

    # ------------------------------------------------------------------
    # Add-equipment helper methods (Milestone 2)
    # ------------------------------------------------------------------
    def add_bus(self, name: str, nominal_kv: float, bus_type: str = "PQ",
                vpu: float = 1.0, delta: float = 0.0) -> Bus:
        if name in self.buses:
            raise ValueError(f"Bus '{name}' already exists.")
        bus = Bus(name, nominal_kv, bus_type, vpu, delta)
        self.buses[name] = bus
        return bus

    def add_transformer(self, name: str, bus1: str, bus2: str,
                        r: float, x: float,
                        connection_1: str = "Y_grounded",
                        connection_2: str = "Y_grounded",
                        zn1: complex = 0.0,
                        zn2: complex = 0.0) -> Transformer:
        t = Transformer(name, bus1, bus2, r, x,
                        connection_1, connection_2, zn1, zn2)
        self.transformers[name] = t
        return t

    def add_transmission_line(self, name: str, bus1: str, bus2: str,
                              r: float, x: float, g: float, b: float,
                              z0_multiplier: float = 3.0,
                              b0_multiplier: float = 0.5) -> TransmissionLine:
        line = TransmissionLine(name, bus1, bus2, r, x, g, b,
                                z0_multiplier, b0_multiplier)
        self.transmission_lines[name] = line
        return line

    def add_generator(self, name: str, bus1: str,
                      voltage_setpoint: float, mw_setpoint: float,
                      x1: float = 0.12, x2: float = 0.14, x0: float = 0.05,
                      grounding: str = "solid",
                      zn: complex = 0.0) -> Generator:
        g = Generator(name, bus1, voltage_setpoint, mw_setpoint,
                      x1, x2, x0, grounding, zn)
        self.generators[name] = g
        return g

    def add_load(self, name: str, bus1: str, mw: float, mvar: float) -> Load:
        ld = Load(name, bus1, mw, mvar)
        self.loads[name] = ld
        return ld

    # ------------------------------------------------------------------
    # Bus index utilities
    # ------------------------------------------------------------------
    def _bus_index_map(self) -> dict[str, int]:
        """Map bus name -> integer matrix index (0-based) following the order
        in which buses were added. We re-number locally so bus indexes are
        contiguous within this circuit even if other circuits exist."""
        return {name: i for i, name in enumerate(self.buses.keys())}

    def _bus_names(self) -> list[str]:
        return list(self.buses.keys())

    # ------------------------------------------------------------------
    # Milestone 4: Positive-sequence Ybus from transformers + lines
    # ------------------------------------------------------------------
    def calc_ybus(self) -> None:
        """Stamp every transformer and transmission line's primitive
        admittance matrix into the system Ybus. Updates self.ybus in place."""
        N = len(self.buses)
        bus_idx = self._bus_index_map()
        names = self._bus_names()

        Y = np.zeros((N, N), dtype=complex)

        # Transformers
        for t in self.transformers.values():
            yp = t.calc_yprim().values
            i = bus_idx[t.bus1_name]
            j = bus_idx[t.bus2_name]
            Y[i, i] += yp[0, 0]
            Y[i, j] += yp[0, 1]
            Y[j, i] += yp[1, 0]
            Y[j, j] += yp[1, 1]

        # Transmission lines
        for line in self.transmission_lines.values():
            yp = line.calc_yprim().values
            i = bus_idx[line.bus1_name]
            j = bus_idx[line.bus2_name]
            Y[i, i] += yp[0, 0]
            Y[i, j] += yp[0, 1]
            Y[j, i] += yp[1, 0]
            Y[j, j] += yp[1, 1]

        self.ybus = pd.DataFrame(Y, index=names, columns=names)

    # ------------------------------------------------------------------
    # EXTENSION: Sequence Ybus assembly
    # ------------------------------------------------------------------
    def calc_sequence_ybus(self,
                           include_generators: bool = True,
                           include_loads: bool = False) -> None:
        """
        Build the three sequence admittance matrices (Y1, Y2, Y0) used by
        unsymmetrical fault analysis, and store them on self.

        For fault studies, generators are represented by a shunt admittance
        at their terminal bus (1/jX" for positive sequence, 1/jX2 for
        negative, 1/(jX0+3Zn) for zero — handled inside Generator).
        Loads are usually neglected (their impedance is large compared to
        the source impedance) — set include_loads=True to include them
        as constant-impedance shunts derived from their nominal P+jQ.
        """
        N = len(self.buses)
        bus_idx = self._bus_index_map()
        names = self._bus_names()

        Y1 = np.zeros((N, N), dtype=complex)
        Y2 = np.zeros((N, N), dtype=complex)
        Y0 = np.zeros((N, N), dtype=complex)

        # ------ Transformers ------
        for t in self.transformers.values():
            i = bus_idx[t.bus1_name]
            j = bus_idx[t.bus2_name]
            for Y, seq in ((Y1, "positive"), (Y2, "negative"), (Y0, "zero")):
                yp = t.calc_yprim_sequence(seq).values
                Y[i, i] += yp[0, 0]
                Y[i, j] += yp[0, 1]
                Y[j, i] += yp[1, 0]
                Y[j, j] += yp[1, 1]

        # ------ Transmission lines ------
        for line in self.transmission_lines.values():
            i = bus_idx[line.bus1_name]
            j = bus_idx[line.bus2_name]
            for Y, seq in ((Y1, "positive"), (Y2, "negative"), (Y0, "zero")):
                yp = line.calc_yprim_sequence(seq).values
                Y[i, i] += yp[0, 0]
                Y[i, j] += yp[0, 1]
                Y[j, i] += yp[1, 0]
                Y[j, j] += yp[1, 1]

        # ------ Generators (positive/negative/zero shunt to ground) ------
        if include_generators:
            for g in self.generators.values():
                k = bus_idx[g.bus1_name]
                Y1[k, k] += g.y1
                Y2[k, k] += g.y2
                Y0[k, k] += g.y0  # already includes 3*Zn / open-circuit

        # ------ Loads (optional, constant impedance) ------
        if include_loads:
            for ld in self.loads.values():
                # Convert P+jQ at V=1.0 pu into an equivalent shunt admittance:
                # S = V * I*  =>  Y_load = (P - jQ) / |V|^2 ; assume |V|=1 pu
                k = bus_idx[ld.bus1_name]
                p_pu = ld.mw / 100.0
                q_pu = ld.mvar / 100.0
                y_load = complex(p_pu, -q_pu)
                Y1[k, k] += y_load
                Y2[k, k] += y_load
                # Loads typically don't contribute to zero-sequence (delta-connected).

        self.y1bus = pd.DataFrame(Y1, index=names, columns=names)
        self.y2bus = pd.DataFrame(Y2, index=names, columns=names)
        self.y0bus = pd.DataFrame(Y0, index=names, columns=names)

    # ------------------------------------------------------------------
    # Convenience: invert sequence Ybus to get sequence Zbus
    # ------------------------------------------------------------------
    def calc_sequence_zbus(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Return (Z1bus, Z2bus, Z0bus) by inverting the sequence Ybus
        matrices. The user must call calc_sequence_ybus() first."""
        if self.y1bus is None:
            raise RuntimeError("Call calc_sequence_ybus() before calc_sequence_zbus().")
        names = self._bus_names()
        Z1 = pd.DataFrame(np.linalg.inv(self.y1bus.values), index=names, columns=names)
        Z2 = pd.DataFrame(np.linalg.inv(self.y2bus.values), index=names, columns=names)
        Z0 = pd.DataFrame(np.linalg.inv(self.y0bus.values), index=names, columns=names)
        return Z1, Z2, Z0

    def __repr__(self):
        return (f"Circuit('{self.name}': {len(self.buses)} buses, "
                f"{len(self.transformers)} transformers, "
                f"{len(self.transmission_lines)} lines, "
                f"{len(self.generators)} generators, "
                f"{len(self.loads)} loads)")
