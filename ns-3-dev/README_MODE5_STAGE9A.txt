Stage 9A: add 3D Gauss-Markov mobility without overwriting Stage 8 source.

1. Extract ZIP in ~/jm/ns-3-dev, preserving current source.
2. Back up: cp scratch/olsr_baseline.cc scratch/olsr_baseline.cc.stage8.bak
3. Patch: python3 apply_mode5_stage9a.py scratch/olsr_baseline.cc
4. Build: ./ns3 build
5. Smoke test (Mode 0, avoids energy depletion during initial check):
   ./ns3 run "olsr_baseline --mprMode=0 --mobility=gaussmarkov3d --nodes=10 --speed=10 --range=500 --area=3000 --altitude=3000 --gmAlpha=0.85 --gmStep=1 --simTime=60 --seed=1 --out=gm3d_smoke.csv"
6. Check: python3 verify_mode5_stage9a.py gm3d_smoke.csv.positions.csv 3000 3000
7. Check existing mobility still works:
   ./ns3 run "olsr_baseline --mprMode=0 --mobility=random --nodes=5 --speed=10 --simTime=60 --out=random_regression.csv"

Notes:
- Gauss-Markov parameters are explicit experimental assumptions, not verified as exact paper settings.
- This step does not change Wi-Fi standard, propagation, traffic or energy model.
- With 10 nodes randomly distributed in 3000^3 m and 500 m range, the graph may be disconnected and PDR low; this does not indicate a mobility implementation bug.
- Gauss-Markov speed is a mean with stochastic perturbations; instantaneous speeds may differ.
- The Stage 8 source code is retained: only scratch/olsr_baseline.cc is patched.
