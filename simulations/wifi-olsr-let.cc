
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/mobility-module.h"
#include "ns3/wifi-module.h"
#include "ns3/internet-module.h"
#include "ns3/olsr-helper.h"
#include "ns3/applications-module.h"

#include <iostream>
#include <cmath>
#include <limits>

using namespace ns3;

// ============================================
// 1. LET 계산 함수
// ============================================

double CalculateLET(Ptr<Node> node1,
                    Ptr<Node> node2,
                    double range)
{
    Ptr<MobilityModel> m1 =
        node1->GetObject<MobilityModel>();

    Ptr<MobilityModel> m2 =
        node2->GetObject<MobilityModel>();

    // 두 노드의 현재 위치
    Vector p1 = m1->GetPosition();
    Vector p2 = m2->GetPosition();

    // 두 노드의 현재 속도
    Vector v1 = m1->GetVelocity();
    Vector v2 = m2->GetVelocity();

    // 상대 위치
    double dx = p1.x - p2.x;
    double dy = p1.y - p2.y;
    double dz = p1.z - p2.z;

    // 상대 속도
    double vx = v1.x - v2.x;
    double vy = v1.y - v2.y;
    double vz = v1.z - v2.z;

    // 거리 방정식 계수
    double a = vx*vx + vy*vy + vz*vz;

    double b = 2.0 * (
        dx*vx + dy*vy + dz*vz
    );

    double c = dx*dx + dy*dy + dz*dz
               - range*range;

    // 이미 통신 범위 밖인 경우
    if (c > 0)
    {
        return 0.0;
    }

    // 상대 속도가 0인 경우
    if (a < 1e-12)
    {
        return std::numeric_limits<double>::infinity();
    }

    // 판별식
    double discriminant = b*b - 4*a*c;

    if (discriminant < 0)
    {
        return std::numeric_limits<double>::infinity();
    }

    // 통신 범위를 벗어나는 시점
    double tExit =
        (-b + std::sqrt(discriminant)) / (2*a);

    return tExit > 0 ? tExit : 0.0;
}

// ============================================
// 2. LET 출력 함수
// ============================================

void PrintLET(NodeContainer nodes, double range)
{
    double time = Simulator::Now().GetSeconds();

    double letAB = CalculateLET(
        nodes.Get(0), nodes.Get(1), range);

    double letBC = CalculateLET(
        nodes.Get(1), nodes.Get(2), range);

    std::cout << "\n========== LET ==========\n";

    std::cout << "Time: " << time << "s\n";

    std::cout << "A-B LET: "
              << letAB << "s\n";

    std::cout << "B-C LET: "
              << letBC << "s\n";

    std::cout << "=========================\n";
}

// ============================================
// 3. 메인 함수
// ============================================

int main(int argc, char* argv[])
{
    // ----------------------------------------
    // 1. 노드 4개 생성
    // ----------------------------------------

    NodeContainer nodes;
    nodes.Create(4);

    // Node 0 = A
    // Node 1 = B
    // Node 2 = C
    // Node 3 = D

    // ----------------------------------------
    // 2. 노드 위치 및 이동 모델 설정
    // ----------------------------------------

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

    // 모든 노드 초기 속도 0
    for (uint32_t i = 0; i < nodes.GetN(); i++)
    {
        Ptr<ConstantVelocityMobilityModel> model =
            nodes.Get(i)->GetObject<
                ConstantVelocityMobilityModel>();

        model->SetVelocity(Vector(0, 0, 0));
    }

    // ----------------------------------------
    // 3. B 노드 이동 설정
    // ----------------------------------------

    Ptr<ConstantVelocityMobilityModel> nodeB =
        nodes.Get(1)->GetObject<
            ConstantVelocityMobilityModel>();

    // 20초에 B가 Y축 방향으로 20m/s 이동
    Simulator::Schedule(
        Seconds(20.0),
        &ConstantVelocityMobilityModel::SetVelocity,
        nodeB,
        Vector(0, 20, 0));

    // ----------------------------------------
    // 4. Wi-Fi Ad Hoc 설정
    // ----------------------------------------

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

    // ----------------------------------------
    // 5. OLSR 라우팅 설정
    // ----------------------------------------

    OlsrHelper olsr;

    Ipv4ListRoutingHelper routing;
    routing.Add(olsr, 10);

    InternetStackHelper internet;
    internet.SetRoutingHelper(routing);
    internet.Install(nodes);

    // ----------------------------------------
    // 6. IP 주소 할당
    // ----------------------------------------

    Ipv4AddressHelper address;

    address.SetBase(
        "10.1.1.0",
        "255.255.255.0");

    Ipv4InterfaceContainer interfaces =
        address.Assign(devices);

    // ----------------------------------------
    // 7. UDP Echo 서버 (C 노드)
    // ----------------------------------------

    UdpEchoServerHelper server(9);

    ApplicationContainer serverApp =
        server.Install(nodes.Get(2));

    serverApp.Start(Seconds(1.0));
    serverApp.Stop(Seconds(45.0));

    // ----------------------------------------
    // 8. UDP Echo 클라이언트 (A 노드)
    // ----------------------------------------

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

    // ----------------------------------------
    // 9. UDP 로그 출력
    // ----------------------------------------

    LogComponentEnable(
        "UdpEchoClientApplication",
        LOG_LEVEL_INFO);

    LogComponentEnable(
        "UdpEchoServerApplication",
        LOG_LEVEL_INFO);

    // ----------------------------------------
    // 10. OLSR 라우팅 테이블 출력
    // ----------------------------------------

    Ptr<OutputStreamWrapper> routingStream =
        Create<OutputStreamWrapper>(&std::cout);

    // 이동 전 라우팅 테이블
    olsr.PrintRoutingTableAllAt(
        Seconds(14.0), routingStream);

    // 이동 중 및 이동 후
    for (int t = 20; t <= 40; t++)
    {
        olsr.PrintRoutingTableAllAt(
            Seconds(t), routingStream);
    }

    // ----------------------------------------
    // 11. LET 계산
    // ----------------------------------------

    // 20초부터 25초까지 매초 LET 계산
    for (int t = 20; t <= 25; t++)
    {
        Simulator::Schedule(
            Seconds(t),
            &PrintLET,
            nodes,
            85.0);
    }

    // ----------------------------------------
    // 12. 시뮬레이션 실행
    // ----------------------------------------

    Simulator::Stop(Seconds(45.0));

    Simulator::Run();
    Simulator::Destroy();

    return 0;
}
