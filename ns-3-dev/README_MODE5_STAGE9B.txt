Stage 9B: optional IEEE 802.11b PHY, configurable CBR, 3D connectivity analysis

Prerequisite: Stage 9A successfully applied to scratch/olsr_baseline.cc.
Apply from ~/jm/ns-3-dev after extracting ZIP:
  cp scratch/olsr_baseline.cc scratch/olsr_baseline.cc.stage9a.bak
  python3 apply_mode5_stage9b.py scratch/olsr_baseline.cc
  ./ns3 build
  ./test.py -s routing-olsr-header
  ./test.py -s routing-olsr

New options:
  --wifiStandard=80211b|80211g (default 80211g)
  --packetSize=512 (default)
  --packetInterval=0.1 (seconds; default)

Smoke test (500m radio, 3000m cube, 60 seconds):
  ./ns3 run "olsr_baseline --mprMode=0 --mobility=gaussmarkov3d --nodes=10 --speed=10 --range=500 --area=3000 --altitude=3000 --gmAlpha=0.85 --gmStep=1 --wifiStandard=80211b --packetSize=512 --packetInterval=0.1 --simTime=60 --seed=1 --out=mode0_stage9b.csv"
  python3 analyze_mode5_stage9b_connectivity.py mode0_stage9b.csv.positions.csv --range 500 --src 0 --dst 9 --output mode0_stage9b.connectivity.csv

Compare with previously generated 500m and 1500m trajectories:
  python3 analyze_mode5_stage9b_connectivity.py gm3d_smoke.csv.positions.csv --range 500 --src 0 --dst 9
  python3 analyze_mode5_stage9b_connectivity.py gm3d_range1500.csv.positions.csv --range 1500 --src 0 --dst 9

Caveats:
- Uses existing ideal RangePropagationLossModel, not a realistic 802.11b propagation model.
- Connectivity script computes an undirected geometric graph from positions, not actual reception, OLSR routes or PDR.
- Packet size 512B and interval 100ms were already present before this patch.
- Current Mode 5 starts at 100J and can deplete before 500 seconds; check before long runs.
- 802.11b DSSS 11Mbps is a chosen test rate, not verified as the paper's precise PHY data rate.
- 3D initial positions are uniform in the cube, which may not match the paper's initialization.
- Default 60s runs are smoke tests, not paper reproduction.
