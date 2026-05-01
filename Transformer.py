
import numpy as np
import pandas as pd


# Big number used to represent an open circuit in the zero-sequence network.
# Using float('inf') breaks linear algebra; 1e6 pu admittance = 1e-6 pu impedance,
# i.e. effectively isolated from the rest of the network.
_OPEN_CIRCUIT_Z = 1e6 + 0j

_VALID_CONNECTIONS = ("Y", "Y_grounded", "Y_ungrounded", "Delta")


class Transformer:
    """Two-winding transformer with positive-, negative-, and zero-sequence networks."""

    def __init__(self,
                 name: str,
                 bus1_name: str,
                 bus2_name: str,
                 r: float,
                 x: float,
                 # Winding configurations for each side. Default Y-Y grounded
                 # so behavior matches a generic two-winding transformer.
                 connection_1: str = "Y_grounded",
                 connection_2: str = "Y_grounded",
                 # Optional neutral grounding impedance on each side (per unit).
                 zn1: complex = 0.0 + 0.0j,
                 zn2: complex = 0.0 + 0.0j):
        self.name: str = name
        self.bus1_name: str = bus1_name
        self.bus2_name: str = bus2_name

        # Per-unit leakage parameters (entered directly).
        self.r: float = r
        self.x: float = x

        # Validate winding connections
        for conn in (connection_1, connection_2):
            if conn not in _VALID_CONNECTIONS:
                raise ValueError(
                    f"connection '{conn}' invalid. Must be one of {_VALID_CONNECTIONS}"
                )
        self.connection_1: str = connection_1
        self.connection_2: str = connection_2
        self.zn1: complex = complex(zn1)
        self.zn2: complex = complex(zn2)

        # ------------------------------------------------------------------
        # Original Milestone 3 admittance — positive-sequence series only.
        # ------------------------------------------------------------------
        self.Yseries: complex = 1.0 / complex(r, x)

        # ------------------------------------------------------------------
        # Sequence impedances. For a transformer the leakage impedance is
        # the same in all three sequences (transformer is a static device,
        # so positive- and negative-sequence networks are identical, and
        # the zero-sequence leakage is the same magnitude — what changes
        # is whether the path is closed by the winding configuration).
        # ------------------------------------------------------------------
        self.z1: complex = complex(r, x)
        self.z2: complex = complex(r, x)
        self.z0_leakage: complex = complex(r, x)

    # ----------------------------------------------------------------------
    # Milestone 3 — positive-sequence primitive admittance matrix
    # ----------------------------------------------------------------------
    def calc_yprim(self) -> pd.DataFrame:
        """Return the 2x2 primitive admittance matrix labeled with bus names."""
        y = self.Yseries
        Y = np.array([[ y, -y],
                      [-y,  y]], dtype=complex)
        return pd.DataFrame(Y,
                            index=[self.bus1_name, self.bus2_name],
                            columns=[self.bus1_name, self.bus2_name])

    # ----------------------------------------------------------------------
    # Sequence-network primitive admittance matrices (extension)
    # ----------------------------------------------------------------------
    def calc_yprim_sequence(self, sequence: str = "positive") -> pd.DataFrame:
        """
        Yprim for the requested sequence network.
        Positive and negative are identical and look like the standard 2x2
        series-admittance stamp. Zero-sequence depends on winding config.
        """
        if sequence in ("positive", "negative"):
            y = 1.0 / (self.z1 if sequence == "positive" else self.z2)
            Y = np.array([[ y, -y],
                          [-y,  y]], dtype=complex)

        elif sequence == "zero":
            Y = self._zero_sequence_yprim()

        else:
            raise ValueError("sequence must be 'positive', 'negative', or 'zero'")

        return pd.DataFrame(Y,
                            index=[self.bus1_name, self.bus2_name],
                            columns=[self.bus1_name, self.bus2_name])

    def _zero_sequence_yprim(self) -> np.ndarray:
        """
        Build the 2x2 zero-sequence primitive admittance matrix according to
        winding configuration. The reasoning for each case is documented inline.

        We treat each side independently as 'closed' (zero-sequence current
        can flow into/out of the bus) or 'open' (no zero-sequence current).
        A delta side is special: it acts as a closed-but-grounded port,
        because zero-sequence current circulates inside the delta and is
        not seen at the bus terminal.
        """
        side1_closed = self.connection_1 in ("Y_grounded",)
        side2_closed = self.connection_2 in ("Y_grounded",)
        side1_delta  = self.connection_1 == "Delta"
        side2_delta  = self.connection_2 == "Delta"

        # Effective per-side leakage including 3*Zn for grounded-Y windings.
        z_leak = self.z0_leakage
        z1_branch = z_leak + 3.0 * self.zn1 if side1_closed else _OPEN_CIRCUIT_Z
        z2_branch = z_leak + 3.0 * self.zn2 if side2_closed else _OPEN_CIRCUIT_Z

        # Five canonical situations. We implement them by stamping a small
        # equivalent network of admittances:
        #   - 'series-through' admittance y_series between bus1 and bus2
        #   - 'shunt' admittance from each bus to ground (for delta legs)
        if side1_closed and side2_closed:
            # Y_grounded - Y_grounded: zero-sequence flows straight through.
            y = 1.0 / (z1_branch + z2_branch)
            return np.array([[ y, -y],
                             [-y,  y]], dtype=complex)

        elif side1_closed and side2_delta:
            # Y_grounded - Delta: zero-sequence on side 1 finds a path to
            # ground through the delta (current circulates internally on
            # side 2). Bus2 sees an open circuit in the zero-sequence
            # network (no zero-sequence at the bus terminal).
            y_shunt = 1.0 / z1_branch
            return np.array([[ y_shunt, 0.0 + 0.0j],
                             [0.0 + 0.0j, 0.0 + 0.0j]], dtype=complex)

        elif side1_delta and side2_closed:
            # Symmetric of the above.
            y_shunt = 1.0 / z2_branch
            return np.array([[0.0 + 0.0j, 0.0 + 0.0j],
                             [0.0 + 0.0j, y_shunt]], dtype=complex)

        elif side1_delta and side2_delta:
            # Delta-Delta: zero-sequence current cannot leave the windings
            # at either bus; from the network's perspective both buses are
            # open in the zero-sequence network.
            return np.array([[0.0 + 0.0j, 0.0 + 0.0j],
                             [0.0 + 0.0j, 0.0 + 0.0j]], dtype=complex)

        else:
            # Any other Y-Y combination where at least one side is
            # ungrounded — zero-sequence is open through the transformer.
            return np.array([[0.0 + 0.0j, 0.0 + 0.0j],
                             [0.0 + 0.0j, 0.0 + 0.0j]], dtype=complex)

    def __repr__(self):
        return (f"Transformer(name='{self.name}', "
                f"{self.bus1_name}({self.connection_1})"
                f"-{self.bus2_name}({self.connection_2}), "
                f"Z={self.z1})")
