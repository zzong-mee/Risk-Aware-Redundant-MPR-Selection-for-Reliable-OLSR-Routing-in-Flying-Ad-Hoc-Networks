#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/mobility-module.h"
#include "ns3/wifi-module.h"
#include "ns3/internet-module.h"
#include "ns3/olsr-helper.h"
#include "ns3/olsr-routing-protocol.h"
#include "ns3/socket.h"
#include "ns3/udp-socket-factory.h"
#include <map>
#include <fstream>
#include <set>
#include <vector>
#include <cmath>
#include <algorithm>
using namespace ns3;
static std::ofstream out;
static NodeContainer nodes;
static std::vector<Ptr<olsr::RoutingProtocol>> protocols;
static std::map<Ipv4Address, uint32_t> addrToId;
static std::vector<std::set<uint32_t>> oldNeighbors;
static std::vector<double> illustrativeHello;
static std::vector<Ipv4Address> addresses;
static double radius=180.0, duration=60.0, interval=0.5;
static std::map<std::pair<uint32_t,uint32_t>, uint32_t> sequences;
static std::vector<Ptr<Socket>> receiverSockets;
static std::vector<Ptr<Socket>> senderSockets;

static void Receive(Ptr<Socket> socket)
{
  Address from;
  while (Ptr<Packet> packet = socket->RecvFrom(from))
  {
    if (packet->GetSize() < 12) continue;
    uint8_t bytes[12];
    packet->CopyData(bytes, 12);
    auto read32 = [&](int offset) -> uint32_t {
      return (uint32_t(bytes[offset]) << 24) |
             (uint32_t(bytes[offset+1]) << 16) |
             (uint32_t(bytes[offset+2]) << 8) |
             uint32_t(bytes[offset+3]);
    };
    uint32_t src = read32(0);
    uint32_t dst = read32(4);
    uint32_t seq = read32(8);
    uint32_t receiver = socket->GetNode()->GetId();
    if (receiver == dst)
      out << Simulator::Now().GetSeconds() << ",RX," << receiver
          << "," << src << "," << seq << ",0\n";
  }
}
static void SendProbe(uint32_t src, uint32_t dst)
{
  uint32_t seq = sequences[{src,dst}]++;
  uint32_t fields[3] = {src,dst,seq};
  uint8_t bytes[12];
  for (int k=0;k<3;++k)
    for (int b=0;b<4;++b)
      bytes[k*4+b] = uint8_t(fields[k] >> (24-8*b));
  Ptr<Packet> packet = Create<Packet>(bytes,12);
  int sent = senderSockets[src]->SendTo(
      packet,0,InetSocketAddress(addresses[dst],9000));
  out << Simulator::Now().GetSeconds() << ",TX," << src
      << "," << dst << "," << seq << "," << (sent>=0?1:0) << "\n";
  if (Simulator::Now().GetSeconds()+1.0 <= duration+1e-9)
    Simulator::Schedule(Seconds(1.0), &SendProbe, src, dst);
}
static void Sample()
{
  double now=Simulator::Now().GetSeconds();
  uint32_t n=nodes.GetN();
  std::vector<Vector> positions(n);
  std::vector<std::set<uint32_t>> neighbors(n);
  for(uint32_t i=0;i<n;++i) positions[i]=nodes.Get(i)->GetObject<MobilityModel>()->GetPosition();
  for(uint32_t i=0;i<n;++i) for(uint32_t j=i+1;j<n;++j)
    if(std::hypot(positions[i].x-positions[j].x,positions[i].y-positions[j].y)<=radius)
    {neighbors[i].insert(j);neighbors[j].insert(i);}
  for(uint32_t i=0;i<n;++i)
  {
    uint32_t changes=0;
    for(auto j:neighbors[i]) if(!oldNeighbors[i].count(j)) ++changes;
    for(auto j:oldNeighbors[i]) if(!neighbors[i].count(j)) ++changes;
    double lcr=changes/interval;
    illustrativeHello[i]=std::clamp(2.0/(1.0+0.4*lcr),0.5,2.0);
    out << now << ",NODE," << i << "," << positions[i].x << "," << positions[i].y << "," << illustrativeHello[i] << "\n";
  }
  for(uint32_t i=0;i<n;++i) for(auto j:neighbors[i])
    out << now << ",EDGE," << i << "," << j << "," << 3.0*illustrativeHello[i] << ",0\n";
  for(uint32_t i=0;i<n;++i)
  {
    for(const auto& address:protocols[i]->GetMprSet())
    {
      auto it=addrToId.find(address);
      if(it!=addrToId.end()) out << now << ",MPR," << i << "," << it->second << ",0,0\n";
    }
    // ROUTE: id=source node, x_or_to=destination node,
    // y_or_weight=next-hop node, hello_or_unused=hop count.
    for(const auto& entry:protocols[i]->GetRoutingTableEntries())
    {
      auto d=addrToId.find(entry.destAddr);
      auto h=addrToId.find(entry.nextAddr);
      if(d!=addrToId.end() && h!=addrToId.end() && d->second!=i)
        out << now << ",ROUTE," << i << "," << d->second << "," << h->second << "," << entry.distance << "\n";
    }
  }
  oldNeighbors=std::move(neighbors);
  if(now+interval<=duration+1e-9) Simulator::Schedule(Seconds(interval),&Sample);
}
int main(int argc,char** argv)
{
  uint32_t count=12,seed=3;
  std::string output="olsr-route-trace.csv";
  CommandLine cmd(__FILE__);
  cmd.AddValue("nodes","Number of nodes",count);
  cmd.AddValue("duration","Simulation duration (seconds)",duration);
  cmd.AddValue("range","Visualization distance threshold (m)",radius);
  cmd.AddValue("seed","RNG run",seed);
  // All ordered source/destination pairs are probed.
  cmd.AddValue("output","Output CSV",output);
  cmd.Parse(argc,argv);
  if(count<2 || duration<=0) return 1;
  RngSeedManager::SetSeed(1);RngSeedManager::SetRun(seed);
  nodes.Create(count);
  MobilityHelper mobility;
  mobility.SetPositionAllocator("ns3::RandomRectanglePositionAllocator",
    "X",StringValue("ns3::UniformRandomVariable[Min=20|Max=580]"),
    "Y",StringValue("ns3::UniformRandomVariable[Min=20|Max=380]"));
  mobility.SetMobilityModel("ns3::RandomWaypointMobilityModel",
    "Speed",StringValue("ns3::UniformRandomVariable[Min=3|Max=12]"),
    "Pause",StringValue("ns3::ConstantRandomVariable[Constant=0.5]"),
    "PositionAllocator",PointerValue(CreateObjectWithAttributes<RandomRectanglePositionAllocator>(
      "X",StringValue("ns3::UniformRandomVariable[Min=20|Max=580]"),
      "Y",StringValue("ns3::UniformRandomVariable[Min=20|Max=380]"))));
  mobility.Install(nodes);
  WifiHelper wifi;wifi.SetStandard(WIFI_STANDARD_80211g);
  WifiMacHelper mac;mac.SetType("ns3::AdhocWifiMac");
  // Use the same maximum range for the Wi-Fi propagation model and CSV visualization.
  // Within this range, packet reception still depends on PHY/MAC conditions.
  YansWifiChannelHelper channel;
  channel.SetPropagationDelay("ns3::ConstantSpeedPropagationDelayModel");
  channel.AddPropagationLoss("ns3::RangePropagationLossModel",
                             "MaxRange", DoubleValue(radius));
  YansWifiPhyHelper phy;
  phy.SetChannel(channel.Create());
  NetDeviceContainer devices=wifi.Install(phy,mac,nodes);
  OlsrHelper olsr;InternetStackHelper internet;internet.SetRoutingHelper(olsr);internet.Install(nodes);
  Ipv4AddressHelper ipv4;ipv4.SetBase("10.1.1.0","255.255.255.0");
  Ipv4InterfaceContainer interfaces=ipv4.Assign(devices);
  protocols.resize(count);addresses.resize(count);
  for(uint32_t i=0;i<count;++i)
  {
    addresses[i]=interfaces.GetAddress(i);addrToId[addresses[i]]=i;
    protocols[i]=DynamicCast<olsr::RoutingProtocol>(nodes.Get(i)->GetObject<Ipv4>()->GetRoutingProtocol());
    if(!protocols[i]) {NS_LOG_UNCOND("Missing OLSR on node "<<i);return 1;}
  }
  out.open(output);
  if(!out) {NS_LOG_UNCOND("Could not open "<<output);return 1;}
  out << "time,type,id,x_or_to,y_or_weight,hello_or_unused\n";
  oldNeighbors.resize(count);illustrativeHello.assign(count,2.0);
  for(uint32_t i=0;i<count;++i)
  {
    Ptr<Socket> sock=Socket::CreateSocket(nodes.Get(i),UdpSocketFactory::GetTypeId());
    if(sock->Bind(InetSocketAddress(Ipv4Address::GetAny(),9000))!=0) return 1;
    sock->SetRecvCallback(MakeCallback(&Receive));receiverSockets.push_back(sock);
  }
  for(uint32_t i=0;i<count;++i)
  {
    Ptr<Socket> sock=Socket::CreateSocket(nodes.Get(i),UdpSocketFactory::GetTypeId());
    if(sock->Bind()!=0) return 1;
    senderSockets.push_back(sock);
  }
  Simulator::ScheduleNow(&Sample);
  // One UDP probe per ordered pair per second, with starts spread over
  // each second to reduce artificial synchronized contention.
  uint32_t pairIndex=0;
  uint32_t pairCount=count*(count-1);
  if(duration>=5.0)
    for(uint32_t src=0;src<count;++src)
      for(uint32_t dst=0;dst<count;++dst)
      {
        if(src==dst) continue;
        double start=5.0+double(pairIndex++)/double(pairCount);
        if(start<=duration)
          Simulator::Schedule(Seconds(start),&SendProbe,src,dst);
      }
  Simulator::Stop(Seconds(duration+0.01));Simulator::Run();Simulator::Destroy();out.close();
  return 0;
}
