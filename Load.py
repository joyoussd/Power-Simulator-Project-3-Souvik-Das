

class Load:
    """Constant real and reactive power load connected to a single bus."""

    def __init__(self,
                 name: str,
                 bus1_name: str,
                 mw: float,
                 mvar: float):
        self.name: str = name
        self.bus1_name: str = bus1_name
        self.mw: float = mw
        self.mvar: float = mvar

        # Per-unit values populated by calc_p()/calc_q().
        self.p: float = 0.0
        self.q: float = 0.0

    def calc_p(self, sbase: float = 100.0) -> float:
        """Real power consumption in per-unit on the system base."""
        self.p = self.mw / sbase
        return self.p

    def calc_q(self, sbase: float = 100.0) -> float:
        """Reactive power consumption in per-unit on the system base."""
        self.q = self.mvar / sbase
        return self.q

    def __repr__(self):
        return (f"Load(name='{self.name}', bus='{self.bus1_name}', "
                f"MW={self.mw}, MVAR={self.mvar})")
