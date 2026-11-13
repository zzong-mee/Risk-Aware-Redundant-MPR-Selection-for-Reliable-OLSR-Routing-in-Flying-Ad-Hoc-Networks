#!/usr/bin/env python3
"""Idempotent Stage 9B patch for Stage 9A scratch/olsr_baseline.cc."""
from pathlib import Path
import sys
p=Path(sys.argv[1] if len(sys.argv)>1 else 'scratch/olsr_baseline.cc')
s=p.read_text()
if 'Stage9B configurable PHY and traffic' in s:
    print('Stage 9B already applied; no changes'); sys.exit(0)
if 'gaussmarkov3d' not in s:
    sys.exit('ERROR: Stage 9A must be applied first')
def replace(old,new):
    global s
    if s.count(old)!=1:
        sys.exit(f'ERROR: expected one occurrence, found {s.count(old)}: {old[:95]!r}. No file modified.')
    s=s.replace(old,new,1)
replace('    std::string mobility = "static", out = "baseline.csv";', '''    std::string mobility = "static", out = "baseline.csv";
    // Stage9B configurable PHY and traffic; defaults preserve earlier experiments.
    std::string wifiStandard = "80211g";
    uint32_t packetSize = 512;
    double packetInterval = 0.1;''')
replace('    cmd.AddValue("out", "Output flow CSV filename", out);', '''    cmd.AddValue("wifiStandard", "80211g (default) or 80211b", wifiStandard);
    cmd.AddValue("packetSize", "UDP CBR payload size in bytes", packetSize);
    cmd.AddValue("packetInterval", "UDP CBR interval in seconds", packetInterval);
    cmd.AddValue("out", "Output flow CSV filename", out);''')
replace('    if (nodes < 2 || speed < 0 || simTime <= 30 || range <= 0 ||', '''    if ((wifiStandard != "80211g" && wifiStandard != "80211b") ||
        packetSize == 0 || packetInterval <= 0 ||
        nodes < 2 || speed < 0 || simTime <= 30 || range <= 0 ||''')
replace('''    wifi.SetStandard(WIFI_STANDARD_80211g);
    wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager",
                                 "DataMode", StringValue("ErpOfdmRate6Mbps"),
                                 "ControlMode", StringValue("ErpOfdmRate6Mbps"));''','''    if (wifiStandard == "80211b")
    {
        wifi.SetStandard(WIFI_STANDARD_80211b);
        wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager",
                                     "DataMode", StringValue("DsssRate11Mbps"),
                                     "ControlMode", StringValue("DsssRate11Mbps"));
    }
    else
    {
        wifi.SetStandard(WIFI_STANDARD_80211g);
        wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager",
                                     "DataMode", StringValue("ErpOfdmRate6Mbps"),
                                     "ControlMode", StringValue("ErpOfdmRate6Mbps"));
    }''')
replace('    client.SetAttribute("Interval", TimeValue(MilliSeconds(100)));', '    client.SetAttribute("Interval", TimeValue(Seconds(packetInterval)));')
replace('    client.SetAttribute("PacketSize", UintegerValue(512));', '    client.SetAttribute("PacketSize", UintegerValue(packetSize));')
replace('    std::cout << "Mode=" << mobility << " MprMode=" << mprMode', '''    std::cout << "Stage9B PHY=" << wifiStandard << " packetSize=" << packetSize
              << " packetInterval=" << packetInterval << "s\\n";
    std::cout << "Mode=" << mobility << " MprMode=" << mprMode''')
p.write_text(s)
print('Patched Stage 9B:',p)
