

class Settings:
    """Global system-wide per-unit base values."""

    def __init__(self, freq: float = 60.0, sbase: float = 100.0):
        # System frequency in Hz (typical North American grid value)
        self.freq: float = freq
        # System base apparent power in MVA — every per-unit quantity in the
        # network is referenced to this base.
        self.sbase: float = sbase

    def __repr__(self):
        return f"Settings(freq={self.freq} Hz, sbase={self.sbase} MVA)"


# A single shared instance imported by other modules so per-unit conversions
# are consistent across the project.
settings = Settings()
