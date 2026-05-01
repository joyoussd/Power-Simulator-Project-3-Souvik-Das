# Power-Simulator-Project-3-Souvik-Das
The Repository containts all the relevant documents regarding Project 3 - Unsymmetrical Fault Analysis via Symmetrical Components 

1) Detailed PDF Documentation - Souvik Das Project 3 Documentation
2) Class files (Pycharm)
3) UML Diagram
4) PowerWorld file - p3souvik.pwb


Project Flow :
The project has two phases: build the classes, then run validation.
Phase 1 — Class development
#	File	Role
1)	src/Settings.py --- 	System constants (60 Hz, 100 MVA base)
2)	src/Bus.py	-- Bus class with class-level counter for bus indexing
3)	src/Generator.py  -- 	Generator with sequence reactances (x1, x2, x0) and grounding
4)	src/Transformer.py --- 	Transformer with calc_yprim_sequence() for winding configurations
5)	src/TransmissionLine.py --- 	Line with calc_yprim_sequence() and z0_multiplier
6)	src/Load.py ---	Constant-power load
7)	src/Circuit.py  -- 	Network container; builds y1bus, y2bus, y0bus, and Z-bus matrices
8)	src/PowerFlow.py -- Newton-Raphson power-flow solver
9)	src/SymmetricalFault.py	--- 3-phase fault solver (positive sequence only)
10)	src/UnsymmetricalFault.py  ---	NEW for Project 2 — SLG, LL, DLG via Fortescue transform
11)	src/Solver.py  ---	Unified facade: run_powerflow() and run_fault(fault_type, ...)
12)	src/five_bus_system.py	--- Builds the Glover/Sarma 5-bus test case
Phase 2 — Validation
#	Command	What it does
1)	python tests/test_powerflow.py  ---	Verify Newton-Raphson power flow converges
2)	python tests/test_textbook_verify.py ---	Match textbook hand-calculation to 4 decimals
3)	python tests/test_faults.py ---	Run all 4 fault types (3PH, SLG, LL, DLG) at one bus
4)	python tests/test_advanced_validation.py ---	Boundary conditions, Zf sweep, sanity checks
5)	python main_validation.py	Full validation; writes CSVs to validation/
6)	python make_plots.py  ---	Generate plots from the validation CSVs
Run validation steps 1–6 in order. Steps 1–4 are tests that must pass first. Step 6 must run after Step 5 because it reads the CSVs that Step 5 produces.








