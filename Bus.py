

class Bus:
    """A node where equipment (lines, transformers, generators, loads) connects."""

    # Class-level counter used to assign each new Bus a unique integer index.
    # Indices start at 0 so they can be used directly as numpy/pandas row/col
    # indices when building Ybus, the Jacobian, and the mismatch vector.
    _bus_counter: int = 0

    # Bus type values permitted by the power-flow formulation.
    _ALLOWED_BUS_TYPES = ("Slack", "PQ", "PV")

    def __init__(self,
                 name: str,
                 nominal_kv: float,
                 bus_type: str = "PQ",
                 vpu: float = 1.0,
                 delta: float = 0.0):
        # Validate bus_type so an invalid value cannot silently corrupt the
        # power-flow formulation downstream.
        if bus_type not in Bus._ALLOWED_BUS_TYPES:
            raise ValueError(
                f"Invalid bus_type '{bus_type}'. "
                f"Must be one of {Bus._ALLOWED_BUS_TYPES}."
            )

        self.name: str = name
        self.nominal_kv: float = nominal_kv
        self.bus_type: str = bus_type

        # Voltage state variables. The defaults represent a "flat start"
        # which is the standard initial guess for Newton–Raphson.
        self.vpu: float = vpu        # per-unit voltage magnitude
        self.delta: float = delta    # phase angle in degrees

        # Assign a unique class-level index, then increment the counter.
        self.bus_index: int = Bus._bus_counter
        Bus._bus_counter += 1

    @classmethod
    def reset_counter(cls):
        """Reset the class-level counter — useful between independent test cases."""
        cls._bus_counter = 0

    def __repr__(self):
        return (f"Bus(name='{self.name}', idx={self.bus_index}, "
                f"kV={self.nominal_kv}, type={self.bus_type}, "
                f"V={self.vpu:.4f}∠{self.delta:.4f}°)")
