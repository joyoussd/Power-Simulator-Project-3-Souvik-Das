

from Bus import Bus
from Circuit import Circuit


def build_five_bus_system() -> Circuit:
    """Return a fresh Circuit object for the 5-bus test system."""
    # Reset the class-level bus counter so indices start at 0.
    Bus.reset_counter()

    c = Circuit("Glover_5_Bus")

    # -------- Buses --------
    c.add_bus("Bus 1", 15.0,  bus_type="Slack", vpu=1.0)
    c.add_bus("Bus 2", 345.0, bus_type="PQ")
    c.add_bus("Bus 3", 15.0,  bus_type="PV",    vpu=1.05)
    c.add_bus("Bus 4", 345.0, bus_type="PQ")
    c.add_bus("Bus 5", 345.0, bus_type="PQ")

    # -------- Transformers --------
    # Y-grounded / Delta is a typical step-up transformer configuration.
    # Generator side (low-voltage) is delta; system side (HV) is grounded-Y.
    c.add_transformer("T1", "Bus 1", "Bus 5",
                      r=0.00150, x=0.02,
                      connection_1="Delta",     # generator side
                      connection_2="Y_grounded")
    c.add_transformer("T2", "Bus 3", "Bus 4",
                      r=0.00150, x=0.02,
                      connection_1="Delta",
                      connection_2="Y_grounded")

    # -------- Transmission lines (all 345 kV, fully transposed) --------
    c.add_transmission_line("L1", "Bus 2", "Bus 4",
                            r=0.0090, x=0.10, g=0.0, b=1.72,
                            z0_multiplier=2.5, b0_multiplier=0.6)
    c.add_transmission_line("L2", "Bus 2", "Bus 5",
                            r=0.0045, x=0.05, g=0.0, b=0.88,
                            z0_multiplier=2.5, b0_multiplier=0.6)
    c.add_transmission_line("L3", "Bus 4", "Bus 5",
                            r=0.00225, x=0.025, g=0.0, b=0.44,
                            z0_multiplier=2.5, b0_multiplier=0.6)

    # -------- Generators --------
    # Subtransient X" = 0.12 pu, X2 = 0.14 pu, X0 = 0.05 pu (textbook defaults).
    c.add_generator("G1", "Bus 1",
                    voltage_setpoint=1.0,
                    mw_setpoint=0.0,         # slack — value is decided by solver
                    x1=0.12, x2=0.14, x0=0.05,
                    grounding="solid")

    c.add_generator("G2", "Bus 3",
                    voltage_setpoint=1.05,
                    mw_setpoint=520.0,
                    x1=0.12, x2=0.14, x0=0.05,
                    grounding="solid")

    # -------- Loads --------
    c.add_load("L4", "Bus 4", mw=800.0, mvar=280.0)
    c.add_load("L5", "Bus 5", mw=80.0,  mvar=40.0)

    return c


if __name__ == "__main__":
    sys = build_five_bus_system()
    print(sys)
    for name, bus in sys.buses.items():
        print(" ", bus)
    print()
    print("Transformers:", list(sys.transformers))
    print("Lines       :", list(sys.transmission_lines))
    print("Generators  :", list(sys.generators))
    print("Loads       :", list(sys.loads))
