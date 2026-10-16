
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/mobility-module.h"
#include "ns3/wifi-module.h"
#include "ns3/internet-module.h"
#include "ns3/olsr-helper.h"
#include "ns3/applications-module.h"

#include <iostream>

using namespace ns3;

int main(int argc, char* argv[])
{
    // ====================================
    // 1. 노드 4개 생성
    // ====================================

    NodeContainer nodes;
    nodes.Create(4);

    // Node 0 = A
    // Node 1 = B
    // Node 2 = C
    // Node 3 = D

    // ====================================
    // 2. 노드 위치 설정
    // ====================================

    MobilityHelper mobility;

    Ptr<ListPositionAllocator> positions =
        CreateObject<ListPositionAllocator>();

    positions->Add(Vector(0, 0, 0));     // A
    positions->Add(Vector(60, 0, 0));    // B
    positions->Add(Vector(120, 0, 0));   // C
    positions->Add(Vector(60, -60, 0));  // D

    mobility.SetPositionAllocator(positions);

    mobility.SetMobilityModel(
        "ns3::ConstantVelocityMobilityModel");

    mobility.Install(nodes);

    // ====================================
    // 3. B 노드 이동 설정
    // ====================================

    Ptr<ConstantVelocityMobilityModel> nodeB =
        nodes.Get(1)->GetObject<
            ConstantVelocityMobilityModel>();

    nodeB->SetVelocity(Vector(0, 0, 0));

    // 20초부터 B가 위쪽으로 이동
    Simulator::Schedule(
        Seconds(20.0),
        &ConstantVelocityMobilityModel::SetVelocity,
        nodeB,
        Vector(0, 20, 0));

    // ====================================
    // 4. Wi-Fi Ad Hoc 설정
    // ====================================

    YansWifiChannelHelper channel;

    channel.SetPropagationDelay(
        "ns3::ConstantSpeedPropagationDelayModel");

    channel.AddPropagationLoss(
        "ns3::RangePropagationLossModel",
        "MaxRange", DoubleValue(85.0));

    YansWifiPhyHelper phy;
    phy.SetChannel(channel.Create());

    WifiHelper wifi;
    wifi.SetStandard(WIFI_STANDARD_80211b);

    WifiMacHelper mac;
    mac.SetType("ns3::AdhocWifiMac");

    NetDeviceContainer devices =
        wifi.Install(phy, mac, nodes);

    // ====================================
    // 5. OLSR 설정
    // ====================================

    OlsrHelper olsr;

    Ipv4ListRoutingHelper routing;
    routing.Add(olsr, 10);

    InternetStackHelper internet;
    internet.SetRoutingHelper(routing);
    internet.Install(nodes);

    // ====================================
    // 6. IP 주소 할당
    // ====================================

    Ipv4AddressHelper address;

    address.SetBase(
        "10.1.1.0",
        "255.255.255.0");

    Ipv4InterfaceContainer interfaces =
        address.Assign(devices);

    // ====================================
    // 7. UDP Echo 서버 (C)
    // ====================================

    UdpEchoServerHelper server(9);

    ApplicationContainer serverApp =
        server.Install(nodes.Get(2));

    serverApp.Start(Seconds(1.0));
    serverApp.Stop(Seconds(45.0));

    // ====================================
    // 8. UDP Echo 클라이언트 (A)
    // ====================================

    UdpEchoClientHelper client(
        interfaces.GetAddress(2), 9);

    client.SetAttribute(
        "MaxPackets", UintegerValue(25));

    client.SetAttribute(
        "Interval", TimeValue(Seconds(1.0)));

    client.SetAttribute(
        "PacketSize", UintegerValue(1024));

    ApplicationContainer clientApp =
        client.Install(nodes.Get(0));

    clientApp.Start(Seconds(15.0));
    clientApp.Stop(Seconds(42.0));

    // ====================================
    // 9. UDP 로그 활성화
    // ====================================

    LogComponentEnable(
        "UdpEchoClientApplication",
        LOG_LEVEL_INFO);

    LogComponentEnable(
        "UdpEchoServerApplication",
        LOG_LEVEL_INFO);

    // ====================================
    // 10. OLSR 라우팅 테이블 출력
    // ====================================

    Ptr<OutputStreamWrapper> routingStream =
        Create<OutputStreamWrapper>(&std::cout);

    // 이동 전
    olsr.PrintRoutingTableAllAt(
        Seconds(14.0), routingStream);

    // 이동 중 및 이동 후
    for (int t = 20; t <= 40; t++)
    {
        olsr.PrintRoutingTableAllAt(
            Seconds(t), routingStream);
    }

    // ====================================
    // 11. 실행
    // ====================================

    Simulator::Stop(Seconds(45.0));

    Simulator::Run();
    Simulator::Destroy();

    return 0;
}
