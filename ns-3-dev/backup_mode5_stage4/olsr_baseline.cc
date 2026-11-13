#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/wifi-module.h"
#include "ns3/olsr-helper.h"
#include "ns3/olsr-routing-protocol.h"
#include "ns3/applications-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/energy-module.h"
#include <fstream>
#include <iostream>
#include <iomanip>
#include <string>
#include <algorithm>
#include <cstdint>

using namespace ns3;

// Periodically publish measured energy to the Mode-5 HELLO attribute.
// No dependency from the reusable OLSR module to the ns-3 energy module.
static void UpdateMode5Energy(std::vector<Ptr<olsr::RoutingProtocol>> protocols,
                              ns3::energy::EnergySourceContainer sources, double interval, double endTime)
{
    for (uint32_t i = 0; i < sources.GetN() && i < protocols.size(); ++i)
    {
        if (protocols[i])
        {
            protocols[i]->SetAttribute("Mode5EnergyJoules",
                                       DoubleValue(std::max(0.0, sources.Get(i)->GetRemainingEnergy())));
        }
    }
    if (Simulator::Now().GetSeconds() + interval < endTime)
    {
        Simulator::Schedule(Seconds(interval), &UpdateMode5Energy,
                            protocols, sources, interval, endTime);
    }
}

static void LogPositions(NodeContainer nodes, Ptr<OutputStreamWrapper> stream,
                         double interval, double endTime)
{
    auto& os = *stream->GetStream();
    for (uint32_t i = 0; i < nodes.GetN(); ++i)
    {
        Vector p = nodes.Get(i)->GetObject<MobilityModel>()->GetPosition();
        os << Simulator::Now().GetSeconds() << ',' << i << ','
           << p.x << ',' << p.y << ',' << p.z << '\n';
    }
    if (Simulator::Now().GetSeconds() + interval < endTime)
    {
        Simulator::Schedule(Seconds(interval), &LogPositions,
                            nodes, stream, interval, endTime);
    }
}

// Protocol-level OLSR Tx/Rx trace. Each row describes one OLSR packet event.
// TC/HELLO counts are the numbers of messages inside that packet.
static void
RecordOlsrControl(uint32_t nodeId, std::ofstream* csv, const char* event,
                  const olsr::PacketHeader& header,
                  const olsr::MessageList& messages)
{
    uint32_t hello = 0, tc = 0, mid = 0, hna = 0;
    for (const auto& msg : messages)
    {
        switch (msg.GetMessageType())
        {
        case olsr::MessageHeader::HELLO_MESSAGE: ++hello; break;
        case olsr::MessageHeader::TC_MESSAGE: ++tc; break;
        case olsr::MessageHeader::MID_MESSAGE: ++mid; break;
        case olsr::MessageHeader::HNA_MESSAGE: ++hna; break;
        default: break;
        }
    }
    *csv << std::fixed << std::setprecision(6)
         << Simulator::Now().GetSeconds() << ',' << nodeId << ',' << event << ','
         << header.GetPacketLength() << ',' << hello << ',' << tc << ','
         << mid << ',' << hna << '\n';
}

static void
RecordOlsrTx(uint32_t nodeId, std::ofstream* csv,
             const olsr::PacketHeader& header, const olsr::MessageList& messages)
{
    RecordOlsrControl(nodeId, csv, "TX", header, messages);
}

static void
RecordOlsrRx(uint32_t nodeId, std::ofstream* csv,
             const olsr::PacketHeader& header, const olsr::MessageList& messages)
{
    RecordOlsrControl(nodeId, csv, "RX", header, messages);
}

int main(int argc, char* argv[])
{
    uint32_t seed = 1, nodes = 5, mprMode = 0;
    double speed = 12.0, simTime = 120.0, range = 150.0;
    double spacing = 100.0, area = 350.0;
    double riskThreshold = 1.0, riskHorizon = 5.0, riskSigma = 2.0, riskAlpha = 0.9;
    double riskAddThreshold = 1.5, riskRemoveThreshold = 0.5;
    uint32_t riskScenarios = 100;
    std::string mobility = "static", out = "baseline.csv";

    CommandLine cmd(__FILE__);
    cmd.AddValue("seed", "Random run index", seed);
    cmd.AddValue("nodes", "Node count (>=2)", nodes);
    cmd.AddValue("speed", "Random mobility speed in m/s", speed);
    cmd.AddValue("simTime", "Simulation seconds (>30)", simTime);
    cmd.AddValue("range", "Idealized radio range in meters", range);
    cmd.AddValue("spacing", "Static chain spacing in meters", spacing);
    cmd.AddValue("area", "Random waypoint square side length in meters", area);
    cmd.AddValue("mobility", "static or random", mobility);
    cmd.AddValue("mprMode", "MPR mode: 0=standard, 1=fixed, 2=CVaR, 3=LET, 4=Hysteresis-CVaR, 5=paper reproduction (in progress)", mprMode);
    cmd.AddValue("riskThreshold", "Adaptive risk threshold in seconds", riskThreshold);
    cmd.AddValue("riskAddThreshold", "Hysteresis backup add threshold (seconds)", riskAddThreshold);
    cmd.AddValue("riskRemoveThreshold", "Hysteresis backup removal threshold (seconds)", riskRemoveThreshold);
    cmd.AddValue("riskHorizon", "Prediction horizon in seconds", riskHorizon);
    cmd.AddValue("riskSigma", "Velocity noise standard deviation", riskSigma);
    cmd.AddValue("riskAlpha", "CVaR confidence level", riskAlpha);
    cmd.AddValue("riskScenarios", "CVaR Monte Carlo scenarios", riskScenarios);
    cmd.AddValue("out", "Output flow CSV filename", out);
    cmd.Parse(argc, argv);

    if (nodes < 2 || speed < 0 || simTime <= 30 || range <= 0 ||
        spacing <= 0 || area <= 0 || mprMode > 5 || riskRemoveThreshold > riskAddThreshold ||
        riskRemoveThreshold < 0 || riskHorizon <= 0 || riskThreshold < 0 ||
        riskSigma < 0 || riskAlpha <= 0 || riskAlpha >= 1 || riskScenarios < 10 ||
        (mobility != "static" && mobility != "random"))
    {
        std::cerr << "Invalid parameters\n";
        return 1;
    }
    RngSeedManager::SetSeed(12345);
    RngSeedManager::SetRun(seed);
    NodeContainer n;
    n.Create(nodes);

    WifiHelper wifi;
    wifi.SetStandard(WIFI_STANDARD_80211g);
    wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager",
                                 "DataMode", StringValue("ErpOfdmRate6Mbps"),
                                 "ControlMode", StringValue("ErpOfdmRate6Mbps"));
    YansWifiChannelHelper channel;
    channel.SetPropagationDelay("ns3::ConstantSpeedPropagationDelayModel");
    // Ideal range model for diagnosis, not a realistic radio propagation model.
    channel.AddPropagationLoss("ns3::RangePropagationLossModel",
                               "MaxRange", DoubleValue(range));
    YansWifiPhyHelper phy;
    phy.SetChannel(channel.Create());
    WifiMacHelper mac;
    mac.SetType("ns3::AdhocWifiMac");
    NetDeviceContainer dev = wifi.Install(phy, mac, n);

    // Mode 5: a real ns-3 battery source and Wi-Fi radio consumption model.
    ns3::energy::EnergySourceContainer mode5Sources;
    if (mprMode == 5)
    {
        BasicEnergySourceHelper battery;
        battery.Set("BasicEnergySourceInitialEnergyJ", DoubleValue(100.0));
        mode5Sources = battery.Install(n);
        WifiRadioEnergyModelHelper radioEnergy;
        radioEnergy.Install(dev, mode5Sources);
    }

    MobilityHelper mob;
    if (mobility == "static")
    {
        Ptr<ListPositionAllocator> positions = CreateObject<ListPositionAllocator>();
        for (uint32_t i = 0; i < nodes; ++i)
            positions->Add(Vector(i * spacing, 0, 0));
        mob.SetPositionAllocator(positions);
        mob.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    }
    else
    {
        Ptr<RandomRectanglePositionAllocator> positions =
            CreateObject<RandomRectanglePositionAllocator>();
        positions->SetAttribute("X", StringValue(
            "ns3::UniformRandomVariable[Min=0|Max=" + std::to_string(area) + "]"));
        positions->SetAttribute("Y", StringValue(
            "ns3::UniformRandomVariable[Min=0|Max=" + std::to_string(area) + "]"));
        mob.SetPositionAllocator(positions);
        mob.SetMobilityModel("ns3::RandomWaypointMobilityModel",
                             "Speed", StringValue("ns3::ConstantRandomVariable[Constant=" +
                                                  std::to_string(speed) + "]"),
                             "Pause", StringValue("ns3::ConstantRandomVariable[Constant=0]"),
                             "PositionAllocator", PointerValue(positions));
    }
    mob.Install(n);

    OlsrHelper olsr;
    olsr.Set("MprMode", UintegerValue(mprMode));
    olsr.Set("MprLogFile", StringValue(out + ".mpr.csv"));
    olsr.Set("LetLogFile", StringValue(out + ".let.csv"));
    olsr.Set("LetRange", DoubleValue(range));
    olsr.Set("RiskThreshold", DoubleValue(riskThreshold));
    olsr.Set("RiskAddThreshold", DoubleValue(riskAddThreshold));
    olsr.Set("RiskRemoveThreshold", DoubleValue(riskRemoveThreshold));
    olsr.Set("RiskHorizon", DoubleValue(riskHorizon));
    olsr.Set("RiskSigma", DoubleValue(riskSigma));
    olsr.Set("RiskAlpha", DoubleValue(riskAlpha));
    olsr.Set("RiskScenarios", UintegerValue(riskScenarios));
    Ipv4StaticRoutingHelper staticRouting;
    Ipv4ListRoutingHelper routing;
    routing.Add(olsr, 10);
    routing.Add(staticRouting, 0);
    InternetStackHelper stack;
    stack.SetRoutingHelper(routing);
    stack.Install(n);
    Ipv4AddressHelper address;
    address.SetBase("10.1.1.0", "255.255.255.0");
    Ipv4InterfaceContainer interfaces = address.Assign(dev);

    std::vector<Ptr<olsr::RoutingProtocol>> mode5Protocols(n.GetN());
    // Connect directly to OLSR inside Ipv4ListRouting (not the outer list).
    std::ofstream controlCsv(out + ".control.csv");
    if (!controlCsv)
    {
        std::cerr << "Cannot open control CSV: " << out << ".control.csv\n";
        Simulator::Destroy();
        return 1;
    }
    controlCsv << "time,node,event,packet_bytes,hello_count,tc_count,mid_count,hna_count\n";
    for (uint32_t i = 0; i < n.GetN(); ++i)
    {
        Ptr<Ipv4> ipv4 = n.Get(i)->GetObject<Ipv4>();
        Ptr<Ipv4ListRouting> list = DynamicCast<Ipv4ListRouting>(ipv4->GetRoutingProtocol());
        if (!list)
        {
            std::cerr << "Node " << i << ": expected Ipv4ListRouting\n";
            Simulator::Destroy();
            return 1;
        }
        bool found = false;
        for (uint32_t j = 0; j < list->GetNRoutingProtocols(); ++j)
        {
            int16_t priority = 0;
            Ptr<olsr::RoutingProtocol> protocol =
                DynamicCast<olsr::RoutingProtocol>(list->GetRoutingProtocol(j, priority));
            if (!protocol)
                continue;
            found = true;
            if (mprMode == 5)
            {
                mode5Protocols[i] = protocol;
            }
            protocol->TraceConnectWithoutContext(
                "Tx", MakeBoundCallback(&RecordOlsrTx, i, &controlCsv));
            protocol->TraceConnectWithoutContext(
                "Rx", MakeBoundCallback(&RecordOlsrRx, i, &controlCsv));
        }
        if (!found)
        {
            std::cerr << "Node " << i << ": OLSR routing protocol not found\n";
            Simulator::Destroy();
            return 1;
        }
    }

    if (mprMode == 5)
    {
        UpdateMode5Energy(mode5Protocols, mode5Sources, 0.5, simTime);
    }

    const uint16_t port = 9000;
    UdpServerHelper server(port);
    ApplicationContainer serverApps = server.Install(n.Get(nodes - 1));
    serverApps.Start(Seconds(1));
    serverApps.Stop(Seconds(simTime));
    UdpClientHelper client(interfaces.GetAddress(nodes - 1), port);
    client.SetAttribute("MaxPackets", UintegerValue(1000000));
    client.SetAttribute("Interval", TimeValue(MilliSeconds(100)));
    client.SetAttribute("PacketSize", UintegerValue(512));
    ApplicationContainer clientApps = client.Install(n.Get(0));
    clientApps.Start(Seconds(20));
    clientApps.Stop(Seconds(simTime - 1));

    AsciiTraceHelper ascii;
    Ptr<OutputStreamWrapper> routeStream = ascii.CreateFileStream(out + ".routes.txt");
    olsr.PrintRoutingTableAllAt(Seconds(15), routeStream);
    olsr.PrintRoutingTableAllAt(Seconds(simTime / 2), routeStream);
    Ptr<OutputStreamWrapper> posStream = ascii.CreateFileStream(out + ".positions.csv");
    *posStream->GetStream() << "time,node,x,y,z\n";
    Simulator::Schedule(Seconds(0), &LogPositions, n, posStream, 0.5, simTime);

    FlowMonitorHelper flowHelper;
    Ptr<FlowMonitor> monitor = flowHelper.InstallAll();
    Simulator::Stop(Seconds(simTime));
    Simulator::Run();
    monitor->CheckForLostPackets();

    Ptr<Ipv4FlowClassifier> classifier =
        DynamicCast<Ipv4FlowClassifier>(flowHelper.GetClassifier());
    std::ofstream csv(out);
    if (!csv)
    {
        std::cerr << "Cannot open output file " << out << '\n';
        Simulator::Destroy();
        return 1;
    }
    csv << "seed,mpr_mode,mobility,nodes,speed,range,spacing,area,flow,src,dst,tx,rx,lost,pdr,delay_ms\n";
    uint64_t totalTx = 0, totalRx = 0;
    double totalDelay = 0;
    for (const auto& item : monitor->GetFlowStats())
    {
        auto tuple = classifier->FindFlow(item.first);
        if (tuple.protocol != 17 || tuple.destinationPort != port ||
            tuple.sourceAddress != interfaces.GetAddress(0) ||
            tuple.destinationAddress != interfaces.GetAddress(nodes - 1))
            continue;
        const auto& f = item.second;
        double pdr = f.txPackets ? double(f.rxPackets) / f.txPackets : 0;
        double delayMs = f.rxPackets ? 1000.0 * f.delaySum.GetSeconds() / f.rxPackets : 0;
        csv << seed << ',' << mprMode << ',' << mobility << ',' << nodes << ',' << speed << ','
            << range << ',' << spacing << ',' << area << ',' << item.first << ','
            << tuple.sourceAddress << ',' << tuple.destinationAddress << ','
            << f.txPackets << ',' << f.rxPackets << ',' << f.lostPackets << ','
            << pdr << ',' << delayMs << '\n';
        totalTx += f.txPackets;
        totalRx += f.rxPackets;
        totalDelay += f.delaySum.GetSeconds();
    }
    std::cout << "Mode=" << mobility << " MprMode=" << mprMode
              << " nodes=" << nodes << " speed=" << speed << " range=" << range << "\n"
              << "TX=" << totalTx << " RX=" << totalRx
              << " PDR=" << (totalTx ? 100.0 * totalRx / totalTx : 0) << "%"
              << " delay_ms=" << (totalRx ? 1000.0 * totalDelay / totalRx : 0)
              << " (undefined if RX=0)\n"
              << "Files: " << out << ", " << out << ".routes.txt, "
              << out << ".positions.csv, " << out << ".mpr.csv, "
              << out << ".control.csv\n";
    controlCsv.close();
    Simulator::Destroy();
    return 0;
}
