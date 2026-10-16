
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/mobility-module.h"
#include "ns3/wifi-module.h"
#include "ns3/internet-module.h"
#include "ns3/olsr-helper.h"
#include "ns3/applications-module.h"
#include "ns3/ipv4-static-routing-helper.h"
#include "ns3/ipv4-list-routing.h"

#include <iostream>
#include <cmath>
#include <limits>
#include <algorithm>
#include <iomanip>

using namespace ns3;

// ============================================
// 실험 설정
// ============================================

const double COMM_RANGE = 85.0;
const double LET_THRESHOLD = 1.5;

// 사전 전환 여부
bool switched = false;

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

    Vector p1 = m1->GetPosition();
    Vector p2 = m2->GetPosition();

    Vector v1 = m1->GetVelocity();
    Vector v2 = m2->GetVelocity();

    double dx = p1.x - p2.x;
    double dy = p1.y - p2.y;
    double dz = p1.z - p2.z;

    double vx = v1.x - v2.x;
    double vy = v1.y - v2.y;
    double vz = v1.z - v2.z;

    double a = vx*vx + vy*vy + vz*vz;

    double b = 2.0 * (
        dx*vx + dy*vy + dz*vz
    );

    double c = dx*dx + dy*dy + dz*dz
               - range*range;

    // 이미 통신 범위를 벗어난 경우
    if (c > 0)
    {
        return 0.0;
    }

    // 상대 이동이 없는 경우
    if (a < 1e-12)
    {
        return std::numeric_limits<double>::infinity();
    }

    double discriminant = b*b - 4*a*c;

    if (discriminant < 0)
    {
        return std::numeric_limits<double>::infinity();
    }

    double tExit =
        (-b + std::sqrt(discriminant)) / (2*a);

    return std::max(0.0, tExit);
}

// ============================================
// 2. LET 기반 경로 전환
// ============================================

void CheckLETAndSwitch(
    NodeContainer nodes,
    Ipv4Address destination,
    Ipv4Address alternativeNextHop)
{
    double now = Simulator::Now().GetSeconds();

    double letAB = CalculateLET(
        nodes.Get(0), nodes.Get(1), COMM_RANGE);

    double letBC = CalculateLET(
        nodes.Get(1), nodes.Get(2), COMM_RANGE);

    // 경로 LET = 구성 링크 LET 중 최솟값
    double pathLET = std::min(letAB, letBC);

    std::cout << std::fixed
              << std::setprecision(4);

    std::cout << "[LET] Time: " << now
              << "s, A-B: " << letAB
              << "s, B-C: " << letBC
              << "s, Path LET: " << pathLET
              << "s\n";

    // 이미 전환했다면 추가 작업 없음
    if (switched)
    {
        return;
    }

    // LET이 임계값보다 크면 기존 경로 유지
    if (pathLET > LET_THRESHOLD)
    {
        return;
    }

    // 대체 경로 A-D-C의 연결 여부 확인
    double letAD = CalculateLET(
        nodes.Get(0), nodes.Get(3), COMM_RANGE);

    double letDC = CalculateLET(
        nodes.Get(3), nodes.Get(2), COMM_RANGE);

    // 0이면 현재 링크가 끊어진 것으로 처리
    if (letAD <= 0.0 || letDC <= 0.0)
    {
        std::cout
            << "[LET] Alternative path unavailable\n";

        return;
    }

    // A 노드의 IPv4 라우팅 정보
    Ptr<Ipv4> ipv4 =
        nodes.Get(0)->GetObject<Ipv4>();

    Ipv4StaticRoutingHelper staticHelper;

    Ptr<Ipv4StaticRouting> staticRouting =
        staticHelper.GetStaticRouting(ipv4);

    // 목적지 C에 대한 정적 호스트 경로 추가
    // 인터페이스 1 = Wi-Fi
    staticRouting->AddHostRouteTo(
        destination,
        alternativeNextHop,
        1);

    switched = true;

    std::cout
        << "\n====================================\n"
        << "[LET SWITCH] Time: " << now << "s\n"
        << "Path LET: " << pathLET << "s\n"
        << "Old route: A -> B -> C\n"
        << "New route: A -> D -> C\n"
        << "Static host route installed\n"
        << "====================================\n\n";
}

// ============================================
// 3. 메인 함수
// ============================================

int main(int argc, char* argv[])
{
    // ----------------------------------------
    // 노드 4개 생성
    // ----------------------------------------

    NodeContainer nodes;
    nodes.Create(4);

    // A = Node 0
    // B = Node 1
    // C = Node 2
    // D = Node 3

    // ----------------------------------------
    // 위치 및 이동 설정
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

    for (uint32_t i = 0; i < nodes.GetN(); i++)
    {
        Ptr<ConstantVelocityMobilityModel> model =
            nodes.Get(i)->GetObject<
                ConstantVelocityMobilityModel>();

        model->SetVelocity(Vector(0, 0, 0));
    }

    Ptr<ConstantVelocityMobilityModel> nodeB =
        nodes.Get(1)->GetObject<
            ConstantVelocityMobilityModel>();

    // B는 20초부터 위쪽으로 이동
    Simulator::Schedule(
        Seconds(20.0),
        &ConstantVelocityMobilityModel::SetVelocity,
        nodeB,
        Vector(0, 20, 0));

    // ----------------------------------------
    // Wi-Fi Ad Hoc
    // ----------------------------------------

    YansWifiChannelHelper channel;

    channel.SetPropagationDelay(
        "ns3::ConstantSpeedPropagationDelayModel");

    channel.AddPropagationLoss(
        "ns3::RangePropagationLossModel",
        "MaxRange", DoubleValue(COMM_RANGE));

    YansWifiPhyHelper phy;
    phy.SetChannel(channel.Create());

    WifiHelper wifi;
    wifi.SetStandard(WIFI_STANDARD_80211b);

    WifiMacHelper mac;
    mac.SetType("ns3::AdhocWifiMac");

    NetDeviceContainer devices =
        wifi.Install(phy, mac, nodes);

    // ----------------------------------------
    // 라우팅 설정
    // ----------------------------------------

    OlsrHelper olsr;
    Ipv4StaticRoutingHelper staticHelper;

    Ipv4ListRoutingHelper routing;

    // 정적 경로 우선순위 20
    routing.Add(staticHelper, 20);

    // OLSR 우선순위 10
    routing.Add(olsr, 10);

    InternetStackHelper internet;
    internet.SetRoutingHelper(routing);
    internet.Install(nodes);

    // ----------------------------------------
    // IP 주소
    // ----------------------------------------

    Ipv4AddressHelper address;

    address.SetBase(
        "10.1.1.0",
        "255.255.255.0");

    Ipv4InterfaceContainer interfaces =
        address.Assign(devices);

    // ----------------------------------------
    // UDP Echo 서버 C
    // ----------------------------------------

    UdpEchoServerHelper server(9);

    ApplicationContainer serverApp =
        server.Install(nodes.Get(2));

    serverApp.Start(Seconds(1.0));
    serverApp.Stop(Seconds(45.0));

    // ----------------------------------------
    // UDP Echo 클라이언트 A
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
    // 로그 활성화
    // ----------------------------------------

    LogComponentEnable(
        "UdpEchoClientApplication",
        LOG_LEVEL_INFO);

    LogComponentEnable(
        "UdpEchoServerApplication",
        LOG_LEVEL_INFO);

    // ----------------------------------------
    // OLSR 라우팅 테이블 출력
    // ----------------------------------------

    Ptr<OutputStreamWrapper> routingStream =
        Create<OutputStreamWrapper>(&std::cout);

    olsr.PrintRoutingTableAllAt(
        Seconds(14.0), routingStream);

    for (int t = 20; t <= 40; t++)
    {
        olsr.PrintRoutingTableAllAt(
            Seconds(t), routingStream);
    }

    // ----------------------------------------
    // LET 기반 경로 전환 검사
    // ----------------------------------------

    for (int t = 20; t <= 25; t++)
    {
        Simulator::Schedule(
            Seconds(t),
            &CheckLETAndSwitch,
            nodes,
            interfaces.GetAddress(2),
            interfaces.GetAddress(3));
    }

    // ----------------------------------------
    // 시뮬레이션 실행
    // ----------------------------------------

    Simulator::Stop(Seconds(45.0));

    Simulator::Run();
    Simulator::Destroy();

    return 0;
}
