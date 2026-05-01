
import numpy as np
import pandas as pd


class TransmissionLine:
    """Lumped-parameter pi-model transmission line."""

    def __init__(self,
                 name: str,
                 bus1_name: str,
                 bus2_name: str,
                 r: float,
                 x: float,
                 g: float,
                 b: float,
                 # Sequence impedance multipliers — for a transposed line
                 # Z1 = Z2 = (r + jx) and Z0 is typically 2-3.5x Z1.
                 z0_multiplier: float = 3.0,
                 b0_multiplier: float = 0.5):
        self.name: str = name
        self.bus1_name: str = bus1_name
        self.bus2_name: str = bus2_name

        # Positive-sequence parameters (entered directly in per unit).
        self.r: float = r
        self.x: float = x
        self.g: float = g
        self.b: float = b

        # ------------------------------------------------------------------
        # Original Milestone 3 admittances (positive-sequence)
        # ------------------------------------------------------------------
        # Series admittance: Yseries = 1 / (r + jx)
        self.Yseries: complex = 1.0 / complex(r, x)
        # Shunt admittance: Yshunt = g + jb (placed at each end of the pi-model)
        self.Yshunt: complex = complex(g, b)

        # ------------------------------------------------------------------
        # Sequence impedances for fault analysis
        # ------------------------------------------------------------------
        # Positive- and negative-sequence are identical for a transposed line.
        self.z1: complex = complex(r, x)
        self.z2: complex = complex(r, x)
        self.z0: complex = z0_multiplier * complex(r, x)

        # Sequence shunt admittances — kept for completeness; classical fault
        # studies neglect them because |Yshunt| << |Yseries|.
        self.b1: float = b
        self.b2: float = b
        self.b0: float = b0_multiplier * b

    # ----------------------------------------------------------------------
    # Milestone 3 method — positive-sequence primitive admittance matrix
    # ----------------------------------------------------------------------
    def calc_yprim(self) -> pd.DataFrame:
        """
        Return the 2x2 primitive admittance matrix for the pi-model in a
        labeled DataFrame. The off-diagonal entries are -Yseries; the
        diagonals add Yshunt/2 from each end of the pi-section.
        """
        y_series = self.Yseries
        y_shunt_half = self.Yshunt / 2.0
        Y = np.array([
            [y_series + y_shunt_half, -y_series],
            [-y_series,                y_series + y_shunt_half]
        ], dtype=complex)
        return pd.DataFrame(Y,
                            index=[self.bus1_name, self.bus2_name],
                            columns=[self.bus1_name, self.bus2_name])

    # ----------------------------------------------------------------------
    # Sequence-network primitive admittance matrices (extension)
    # ----------------------------------------------------------------------
    def calc_yprim_sequence(self, sequence: str = "positive") -> pd.DataFrame:
        """Yprim for the requested sequence network ('positive', 'negative',
        'zero'). Shunt is neglected here as is standard in fault studies."""
        if sequence == "positive":
            z = self.z1
        elif sequence == "negative":
            z = self.z2
        elif sequence == "zero":
            z = self.z0
        else:
            raise ValueError("sequence must be 'positive', 'negative', or 'zero'")

        y = 1.0 / z
        Y = np.array([[ y, -y],
                      [-y,  y]], dtype=complex)
        return pd.DataFrame(Y,
                            index=[self.bus1_name, self.bus2_name],
                            columns=[self.bus1_name, self.bus2_name])

    def __repr__(self):
        return (f"TransmissionLine(name='{self.name}', "
                f"{self.bus1_name}->{self.bus2_name}, "
                f"Z1={self.z1}, Z0={self.z0})")
