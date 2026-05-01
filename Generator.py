

class Generator:
    """Synchronous generator with full sequence-network representation."""

    _ALLOWED_GROUNDING = ("solid", "impedance", "ungrounded")

    def __init__(self,
                 name: str,
                 bus1_name: str,
                 voltage_setpoint: float,
                 mw_setpoint: float,
                 # Subtransient reactance from Milestone 9 — kept as an alias
                 # for the positive-sequence reactance for backward compatibility.
                 x1: float = 0.12,
                 # Negative- and zero-sequence reactances (per unit, system base).
                 x2: float = 0.14,
                 x0: float = 0.05,
                 # Grounding parameters used by the zero-sequence network.
                 grounding: str = "solid",
                 zn: complex = 0.0 + 0.0j):

        # ------------------------------------------------------------------
        # Original Milestone 1 / 5 attributes
        # ------------------------------------------------------------------
        self.name: str = name
        self.bus1_name: str = bus1_name
        self.voltage_setpoint: float = voltage_setpoint
        self.mw_setpoint: float = mw_setpoint

        # Real power injection in per-unit (computed in calc_p()).
        # Stored as an attribute so the power-flow solver can read it without
        # recomputing from MW each iteration.
        self.p: float = 0.0

        # ------------------------------------------------------------------
        # Sequence reactances (per unit, system base)
        # ------------------------------------------------------------------
        # x1 is the subtransient reactance X" used for both symmetrical and
        # unsymmetrical fault studies. Resistance is neglected in the
        # short-circuit model (industry standard for generator faults).
        self.x1: float = x1
        self.x2: float = x2
        self.x0: float = x0

        # Complex sequence impedances. Neglecting armature resistance is the
        # standard assumption for fault studies; if the user wants to include
        # it, they can set self.r1 etc. and modify these properties.
        self.z1: complex = 0.0 + 1j * x1
        self.z2: complex = 0.0 + 1j * x2
        self.z0: complex = 0.0 + 1j * x0

        # ------------------------------------------------------------------
        # Grounding model
        # ------------------------------------------------------------------
        if grounding not in Generator._ALLOWED_GROUNDING:
            raise ValueError(
                f"Invalid grounding '{grounding}'. "
                f"Must be one of {Generator._ALLOWED_GROUNDING}."
            )
        self.grounding: str = grounding
        self.zn: complex = complex(zn)

        # Effective zero-sequence impedance seen at the machine terminals.
        # Per the symmetrical-components transformation of a wye-connected
        # machine, the neutral impedance Zn appears as 3*Zn in series with
        # the per-phase zero-sequence impedance.
        if grounding == "ungrounded":
            # Use a very large number to represent an open zero-sequence
            # path. Using float('inf') would break linear algebra so we
            # use a numerically large impedance (1e6 pu) instead.
            self.z0_effective: complex = 1e6 + 0j
        else:
            self.z0_effective: complex = self.z0 + 3.0 * self.zn

    # ----------------------------------------------------------------------
    # Methods preserved from earlier milestones
    # ----------------------------------------------------------------------
    def calc_p(self, sbase: float = 100.0) -> float:
        """Return real power injection in per-unit on the system base."""
        self.p = self.mw_setpoint / sbase
        return self.p

    # ----------------------------------------------------------------------
    # Sequence admittances — used when stamping into Y1bus / Y2bus / Y0bus
    # ----------------------------------------------------------------------
    @property
    def y1(self) -> complex:
        """Positive-sequence admittance seen between the generator's internal
        EMF and its terminal bus. 1/Z1."""
        return 1.0 / self.z1

    @property
    def y2(self) -> complex:
        """Negative-sequence admittance: 1/Z2."""
        return 1.0 / self.z2

    @property
    def y0(self) -> complex:
        """Zero-sequence admittance, including the 3*Zn neutral term and
        accounting for an ungrounded machine."""
        return 1.0 / self.z0_effective

    def __repr__(self):
        return (f"Generator(name='{self.name}', bus='{self.bus1_name}', "
                f"X1={self.x1}, X2={self.x2}, X0={self.x0}, "
                f"grounding={self.grounding}, Zn={self.zn})")
