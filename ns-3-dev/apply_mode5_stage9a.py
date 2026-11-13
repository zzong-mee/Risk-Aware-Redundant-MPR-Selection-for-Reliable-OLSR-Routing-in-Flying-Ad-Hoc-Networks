#!/usr/bin/env python3
"""Patch existing ns-3 scratch/olsr_baseline.cc in place, preserving Stage 8 changes."""
from pathlib import Path
import sys
p = Path(sys.argv[1] if len(sys.argv)>1 else 'scratch/olsr_baseline.cc')
s = p.read_text()
if 'gaussmarkov3d' in s:
    print('Already patched; no changes.'); sys.exit(0)
old='    double spacing = 100.0, area = 350.0;'
new='    double spacing = 100.0, area = 350.0;\n    double altitude = 3000.0, gmAlpha = 0.85, gmStep = 1.0;'
assert s.count(old)==1, 'Cannot locate area declaration'
s=s.replace(old,new)
old='    cmd.AddValue("mobility", "static or random", mobility);'
new='''    cmd.AddValue("mobility", "static, random, or gaussmarkov3d", mobility);
    cmd.AddValue("altitude", "Gauss-Markov 3D Z-axis upper bound in meters", altitude);
    cmd.AddValue("gmAlpha", "Gauss-Markov memory coefficient [0,1]", gmAlpha);
    cmd.AddValue("gmStep", "Gauss-Markov update interval in seconds (>0)", gmStep);'''
assert s.count(old)==1
s=s.replace(old,new)
old='        (mobility != "static" && mobility != "random"))'
new='''        altitude <= 0 || gmAlpha < 0 || gmAlpha > 1 || gmStep <= 0 ||
        (mobility != "static" && mobility != "random" && mobility != "gaussmarkov3d"))'''
assert s.count(old)==1
s=s.replace(old,new)
old='''    else
    {
        Ptr<RandomRectanglePositionAllocator> positions ='''
new='''    else if (mobility == "gaussmarkov3d")
    {
        // Gauss-Markov is 3D when MeanPitch/NormalPitch are configured.
        // Start positions are uniformly sampled inside the configured 3D box.
        mob.SetPositionAllocator("ns3::RandomBoxPositionAllocator",
                                 "X", StringValue("ns3::UniformRandomVariable[Min=0|Max=" +
                                                  std::to_string(area) + "]"),
                                 "Y", StringValue("ns3::UniformRandomVariable[Min=0|Max=" +
                                                  std::to_string(area) + "]"),
                                 "Z", StringValue("ns3::UniformRandomVariable[Min=0|Max=" +
                                                  std::to_string(altitude) + "]"));
        mob.SetMobilityModel("ns3::GaussMarkovMobilityModel",
                             "Bounds", BoxValue(Box(0.0, area, 0.0, area, 0.0, altitude)),
                             "TimeStep", TimeValue(Seconds(gmStep)),
                             "Alpha", DoubleValue(gmAlpha),
                             "MeanVelocity", StringValue(
                                 "ns3::ConstantRandomVariable[Constant=" +
                                 std::to_string(speed) + "]"),
                             "MeanDirection", StringValue(
                                 "ns3::UniformRandomVariable[Min=0|Max=6.283185307179586]"),
                             "MeanPitch", StringValue(
                                 "ns3::UniformRandomVariable[Min=-0.523598775598299|Max=0.523598775598299]"),
                             "NormalVelocity", StringValue(
                                 "ns3::NormalRandomVariable[Mean=0|Variance=1]"),
                             "NormalDirection", StringValue(
                                 "ns3::NormalRandomVariable[Mean=0|Variance=0.1]"),
                             "NormalPitch", StringValue(
                                 "ns3::NormalRandomVariable[Mean=0|Variance=0.05]"));
    }
    else
    {
        Ptr<RandomRectanglePositionAllocator> positions ='''
assert s.count(old)==1
s=s.replace(old,new)
p.write_text(s)
print('Patched:',p)
