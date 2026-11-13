/*
 * Copyright (c) 2007 INESC Porto
 *
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * Author: Gustavo J. A. M. Carneiro  <gjc@inescporto.pt>
 */

#include "olsr-header.h"

#include "ns3/assert.h"
#include "ns3/log.h"

#include <cmath>
#include <cstring>
#include <limits>

#define IPV4_ADDRESS_SIZE 4
#define OLSR_MSG_HEADER_SIZE 12
#define OLSR_PKT_HEADER_SIZE 4

namespace ns3
{

NS_LOG_COMPONENT_DEFINE("OlsrHeader");

namespace olsr
{

/// Scaling factor used in RFC 3626.
#define OLSR_C 0.0625

///
/// @brief Converts a decimal number of seconds to the mantissa/exponent format.
///
/// @param seconds decimal number of seconds we want to convert.
/// @return the number of seconds in mantissa/exponent format.
///
uint8_t
SecondsToEmf(double seconds)
{
    int a;
    int b = 0;

    NS_ASSERT_MSG(seconds >= OLSR_C, "SecondsToEmf - Can not convert a value less than OLSR_C");

    // find the largest integer 'b' such that: T/C >= 2^b
    for (b = 1; (seconds / OLSR_C) >= (1 << b); ++b)
    {
    }
    NS_ASSERT((seconds / OLSR_C) < (1 << b));
    b--;
    NS_ASSERT((seconds / OLSR_C) >= (1 << b));

    // compute the expression 16*(T/(C*(2^b))-1), which may not be a integer
    double tmp = 16 * (seconds / (OLSR_C * (1 << b)) - 1);

    // round it up.  This results in the value for 'a'
    a = (int)std::ceil(tmp - 0.5);

    // if 'a' is equal to 16: increment 'b' by one, and set 'a' to 0
    if (a == 16)
    {
        b += 1;
        a = 0;
    }

    // now, 'a' and 'b' should be integers between 0 and 15,
    NS_ASSERT(a >= 0 && a < 16);
    NS_ASSERT(b >= 0 && b < 16);

    // the field will be a byte holding the value a*16+b
    return (uint8_t)((a << 4) | b);
}

///
/// @brief Converts a number of seconds in the mantissa/exponent format to a decimal number.
///
/// @param olsrFormat number of seconds in mantissa/exponent format.
/// @return the decimal number of seconds.
///
double
EmfToSeconds(uint8_t olsrFormat)
{
    int a = (olsrFormat >> 4);
    int b = (olsrFormat & 0xf);
    // value = C*(1+a/16)*2^b [in seconds]
    return OLSR_C * (1 + a / 16.0) * (1 << b);
}

// ---------------- OLSR Packet -------------------------------

NS_OBJECT_ENSURE_REGISTERED(PacketHeader);

PacketHeader::PacketHeader()
{
}

PacketHeader::~PacketHeader()
{
}

TypeId
PacketHeader::GetTypeId()
{
    static TypeId tid = TypeId("ns3::olsr::PacketHeader")
                            .SetParent<Header>()
                            .SetGroupName("Olsr")
                            .AddConstructor<PacketHeader>();
    return tid;
}

TypeId
PacketHeader::GetInstanceTypeId() const
{
    return GetTypeId();
}

uint32_t
PacketHeader::GetSerializedSize() const
{
    return OLSR_PKT_HEADER_SIZE;
}

void
PacketHeader::Print(std::ostream& os) const
{
    os << "len: " << m_packetLength << " seqNo: " << m_packetSequenceNumber;
}

void
PacketHeader::Serialize(Buffer::Iterator start) const
{
    Buffer::Iterator i = start;
    i.WriteHtonU16(m_packetLength);
    i.WriteHtonU16(m_packetSequenceNumber);
}

uint32_t
PacketHeader::Deserialize(Buffer::Iterator start)
{
    Buffer::Iterator i = start;
    m_packetLength = i.ReadNtohU16();
    m_packetSequenceNumber = i.ReadNtohU16();
    return GetSerializedSize();
}

// ---------------- OLSR Message -------------------------------

NS_OBJECT_ENSURE_REGISTERED(MessageHeader);

MessageHeader::MessageHeader()
    : m_messageType(MessageHeader::MessageType(0))
{
}

MessageHeader::~MessageHeader()
{
}

TypeId
MessageHeader::GetTypeId()
{
    static TypeId tid = TypeId("ns3::olsr::MessageHeader")
                            .SetParent<Header>()
                            .SetGroupName("Olsr")
                            .AddConstructor<MessageHeader>();
    return tid;
}

TypeId
MessageHeader::GetInstanceTypeId() const
{
    return GetTypeId();
}

uint32_t
MessageHeader::GetSerializedSize() const
{
    uint32_t size = OLSR_MSG_HEADER_SIZE;
    switch (m_messageType)
    {
    case MID_MESSAGE:
        size += m_message.mid.GetSerializedSize();
        break;
    case HELLO_MESSAGE:
        NS_LOG_DEBUG("Hello Message Size: " << size << " + "
                                            << m_message.hello.GetSerializedSize());
        size += m_message.hello.GetSerializedSize();
        break;
    case TC_MESSAGE:
        size += m_message.tc.GetSerializedSize();
        break;
    case HNA_MESSAGE:
        size += m_message.hna.GetSerializedSize();
        break;
    default:
        NS_ASSERT(false);
    }
    return size;
}

void
MessageHeader::Print(std::ostream& os) const
{
    switch (m_messageType)
    {
    case HELLO_MESSAGE:
        os << "type: HELLO";
        break;
    case TC_MESSAGE:
        os << "type: TC";
        break;
    case MID_MESSAGE:
        os << "type: MID";
        break;
    case HNA_MESSAGE:
        os << "type: HNA";
        break;
    }

    os << " TTL: " << +m_timeToLive;
    os << " Orig: " << m_originatorAddress;
    os << " SeqNo: " << m_messageSequenceNumber;
    os << " Validity: " << +m_vTime;
    os << " Hop count: " << +m_hopCount;
    os << " Size: " << m_messageSize;

    switch (m_messageType)
    {
    case MID_MESSAGE:
        m_message.mid.Print(os);
        break;
    case HELLO_MESSAGE:
        m_message.hello.Print(os);
        break;
    case TC_MESSAGE:
        m_message.tc.Print(os);
        break;
    case HNA_MESSAGE:
        m_message.hna.Print(os);
        break;
    default:
        NS_ASSERT(false);
    }
}

void
MessageHeader::Serialize(Buffer::Iterator start) const
{
    Buffer::Iterator i = start;
    i.WriteU8(m_messageType);
    i.WriteU8(m_vTime);
    i.WriteHtonU16(GetSerializedSize());
    i.WriteHtonU32(m_originatorAddress.Get());
    i.WriteU8(m_timeToLive);
    i.WriteU8(m_hopCount);
    i.WriteHtonU16(m_messageSequenceNumber);

    switch (m_messageType)
    {
    case MID_MESSAGE:
        m_message.mid.Serialize(i);
        break;
    case HELLO_MESSAGE:
        m_message.hello.Serialize(i);
        break;
    case TC_MESSAGE:
        m_message.tc.Serialize(i);
        break;
    case HNA_MESSAGE:
        m_message.hna.Serialize(i);
        break;
    default:
        NS_ASSERT(false);
    }
}

uint32_t
MessageHeader::Deserialize(Buffer::Iterator start)
{
    uint32_t size;
    Buffer::Iterator i = start;
    m_messageType = (MessageType)i.ReadU8();
    NS_ASSERT(m_messageType >= HELLO_MESSAGE && m_messageType <= HNA_MESSAGE);
    m_vTime = i.ReadU8();
    m_messageSize = i.ReadNtohU16();
    m_originatorAddress = Ipv4Address(i.ReadNtohU32());
    m_timeToLive = i.ReadU8();
    m_hopCount = i.ReadU8();
    m_messageSequenceNumber = i.ReadNtohU16();
    size = OLSR_MSG_HEADER_SIZE;
    switch (m_messageType)
    {
    case MID_MESSAGE:
        size += m_message.mid.Deserialize(i, m_messageSize - OLSR_MSG_HEADER_SIZE);
        break;
    case HELLO_MESSAGE:
        size += m_message.hello.Deserialize(i, m_messageSize - OLSR_MSG_HEADER_SIZE);
        break;
    case TC_MESSAGE:
        size += m_message.tc.Deserialize(i, m_messageSize - OLSR_MSG_HEADER_SIZE);
        break;
    case HNA_MESSAGE:
        size += m_message.hna.Deserialize(i, m_messageSize - OLSR_MSG_HEADER_SIZE);
        break;
    default:
        NS_ASSERT(false);
    }
    return size;
}

// ---------------- OLSR MID Message -------------------------------

uint32_t
MessageHeader::Mid::GetSerializedSize() const
{
    return this->interfaceAddresses.size() * IPV4_ADDRESS_SIZE;
}

void
MessageHeader::Mid::Print(std::ostream& os) const
{
    bool first = true;
    os << " [";
    for (const auto& iAddr : interfaceAddresses)
    {
        if (first)
        {
            first = false;
        }
        else
        {
            os << ", ";
        }
        os << iAddr;
    }
    os << "]";
}

void
MessageHeader::Mid::Serialize(Buffer::Iterator start) const
{
    Buffer::Iterator i = start;

    for (auto iter = this->interfaceAddresses.begin(); iter != this->interfaceAddresses.end();
         iter++)
    {
        i.WriteHtonU32(iter->Get());
    }
}

uint32_t
MessageHeader::Mid::Deserialize(Buffer::Iterator start, uint32_t messageSize)
{
    Buffer::Iterator i = start;

    this->interfaceAddresses.clear();
    NS_ASSERT(messageSize % IPV4_ADDRESS_SIZE == 0);

    int numAddresses = messageSize / IPV4_ADDRESS_SIZE;
    this->interfaceAddresses.erase(this->interfaceAddresses.begin(),
                                   this->interfaceAddresses.end());
    for (int n = 0; n < numAddresses; ++n)
    {
        this->interfaceAddresses.emplace_back(i.ReadNtohU32());
    }
    return GetSerializedSize();
}

// Experimental HELLO extension: private format, NOT RFC 3626 interoperable.
namespace
{
constexpr uint16_t MODE5_HELLO_MAGIC = 0x4d35; // "M5"
constexpr uint16_t MODE5_EXT_MAGIC = 0x4558;   // "EX"
constexpr uint8_t MODE5_EXT_VERSION = 3;
constexpr uint16_t MODE5_EXT_BASE_LENGTH = 64; // V1/V2: 4-byte header + 7 doubles + uint32
constexpr uint8_t MODE5_V2_MAX_RATIOS = 15;
constexpr uint8_t MODE5_MAX_RATIOS = 29; // 30-node comparison experiment
uint16_t Mode5ExtensionLength(std::size_t n)
{
    // V3: 5-byte header (16-bit length) + 7 doubles + uint32 + 1-byte count.
    return static_cast<uint16_t>(MODE5_EXT_BASE_LENGTH + 2 +
                                 12 * std::min(n, static_cast<std::size_t>(MODE5_MAX_RATIOS)));
}

void WriteMode5Double(Buffer::Iterator& i, double value)
{
    static_assert(sizeof(double) == sizeof(uint64_t), "Requires IEEE-754 binary64");
    uint64_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    i.WriteHtonU32(static_cast<uint32_t>(bits >> 32));
    i.WriteHtonU32(static_cast<uint32_t>(bits));
}

double ReadMode5Double(Buffer::Iterator& i)
{
    uint64_t bits = (static_cast<uint64_t>(i.ReadNtohU32()) << 32);
    bits |= i.ReadNtohU32();
    double value;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}
} // namespace

// ---------------- OLSR HELLO Message -------------------------------

uint32_t
MessageHeader::Hello::GetSerializedSize() const
{
    uint32_t size = 4 + (hasMode5Extension ? Mode5ExtensionLength(mode5ReceptionRatios.size()) : 0);
    for (auto iter = this->linkMessages.begin(); iter != this->linkMessages.end(); iter++)
    {
        const LinkMessage& lm = *iter;
        size += 4;
        size += IPV4_ADDRESS_SIZE * lm.neighborInterfaceAddresses.size();
    }
    return size;
}

void
MessageHeader::Hello::Print(std::ostream& os) const
{
    os << " Interval: " << +hTime << " (" << EmfToSeconds(hTime) << "s)";
    os << " Willingness: " << willingness;

    for (const auto& ilinkMessage : linkMessages)
    {
        const LinkMessage& lm = ilinkMessage;
        os << " Link code: " << +(lm.linkCode);
        os << " [";
        bool first = true;
        for (const auto& neigh_iter : lm.neighborInterfaceAddresses)
        {
            if (first)
            {
                first = false;
            }
            else
            {
                os << ", ";
            }
            os << neigh_iter;
        }
        os << "]";
    }
}

void
MessageHeader::Hello::Serialize(Buffer::Iterator start) const
{
    Buffer::Iterator i = start;

    i.WriteHtonU16(hasMode5Extension ? MODE5_HELLO_MAGIC : 0);
    i.WriteU8(this->hTime);
    i.WriteU8(static_cast<uint8_t>(this->willingness));

    if (hasMode5Extension)
    {
        i.WriteHtonU16(MODE5_EXT_MAGIC);
        i.WriteU8(MODE5_EXT_VERSION);
        i.WriteHtonU16(Mode5ExtensionLength(mode5ReceptionRatios.size()));
        for (double x : mode5Position) { WriteMode5Double(i, x); }
        for (double x : mode5Velocity) { WriteMode5Double(i, x); }
        WriteMode5Double(i, mode5ResidualEnergy);
        i.WriteHtonU32(mode5Degree);
        const auto count = static_cast<uint8_t>(std::min(mode5ReceptionRatios.size(),
                                                        static_cast<std::size_t>(MODE5_MAX_RATIOS)));
        i.WriteU8(count);
        for (uint8_t n = 0; n < count; ++n)
        {
            i.WriteHtonU32(mode5ReceptionRatios[n].first.Get());
            WriteMode5Double(i, mode5ReceptionRatios[n].second);
        }
    }

    for (auto iter = this->linkMessages.begin(); iter != this->linkMessages.end(); iter++)
    {
        const LinkMessage& lm = *iter;

        i.WriteU8(lm.linkCode);
        i.WriteU8(0); // Reserved

        // The size of the link message, counted in bytes and measured
        // from the beginning of the "Link Code" field and until the
        // next "Link Code" field (or - if there are no more link types
        // - the end of the message).
        i.WriteHtonU16(4 + lm.neighborInterfaceAddresses.size() * IPV4_ADDRESS_SIZE);

        for (auto neigh_iter = lm.neighborInterfaceAddresses.begin();
             neigh_iter != lm.neighborInterfaceAddresses.end();
             neigh_iter++)
        {
            i.WriteHtonU32(neigh_iter->Get());
        }
    }
}

uint32_t
MessageHeader::Hello::Deserialize(Buffer::Iterator start, uint32_t messageSize)
{
    Buffer::Iterator i = start;

    NS_ASSERT(messageSize >= 4);

    this->linkMessages.clear();

    uint16_t helloSizeLeft = messageSize;

    const uint16_t reserved = i.ReadNtohU16();
    this->hTime = i.ReadU8();
    this->willingness = Willingness(i.ReadU8());
    this->hasMode5Extension = false;
    helloSizeLeft -= 4;

    NS_ASSERT_MSG(reserved == 0 || reserved == MODE5_HELLO_MAGIC,
                  "Unknown HELLO reserved/extension format");
    if (reserved == MODE5_HELLO_MAGIC)
    {
        NS_ASSERT_MSG(helloSizeLeft >= MODE5_EXT_BASE_LENGTH, "Truncated Mode5 HELLO extension");
        const uint16_t magic = i.ReadNtohU16();
        const uint8_t version = i.ReadU8();
        // V1/V2 use a one-byte length; V3 uses a two-byte network-order length.
        NS_ASSERT_MSG(version >= 1 && version <= MODE5_EXT_VERSION,
                      "Unsupported Mode5 HELLO extension version");
        NS_ASSERT_MSG(helloSizeLeft >= (version == 3 ? 5u : 4u),
                      "Truncated Mode5 HELLO extension header");
        const uint16_t length = version == 3 ? i.ReadNtohU16() : i.ReadU8();
        NS_ASSERT_MSG(magic == MODE5_EXT_MAGIC &&
                          length >= MODE5_EXT_BASE_LENGTH + (version == 3 ? 1u : 0u) &&
                          length <= helloSizeLeft,
                      "Unsupported Mode5 HELLO extension");
        if (version == 1)
        {
            NS_ASSERT_MSG(length == MODE5_EXT_BASE_LENGTH, "Invalid V1 Mode5 HELLO length");
        }
        for (double& x : mode5Position) { x = ReadMode5Double(i); }
        for (double& x : mode5Velocity) { x = ReadMode5Double(i); }
        mode5ResidualEnergy = ReadMode5Double(i);
        mode5Degree = i.ReadNtohU32();
        mode5ReceptionRatios.clear();
        if (version >= 2)
        {
            const uint16_t ratioBaseLength = MODE5_EXT_BASE_LENGTH + (version == 3 ? 2 : 1);
            NS_ASSERT_MSG(length >= ratioBaseLength, "Truncated Mode5 ratio count");
            const uint8_t count = i.ReadU8();
            const uint8_t maxRatios = version == 3 ? MODE5_MAX_RATIOS : MODE5_V2_MAX_RATIOS;
            NS_ASSERT_MSG(count <= maxRatios &&
                              length == ratioBaseLength + 12 * count,
                          "Invalid Mode5 ratio count/length");
            for (uint8_t n = 0; n < count; ++n)
            {
                const Ipv4Address addr(i.ReadNtohU32());
                const double ratio = ReadMode5Double(i);
                mode5ReceptionRatios.emplace_back(addr, ratio);
            }
        }
        hasMode5Extension = true;
        helloSizeLeft -= length;
    }

    while (helloSizeLeft)
    {
        LinkMessage lm;
        NS_ASSERT(helloSizeLeft >= 4);
        lm.linkCode = i.ReadU8();
        i.ReadU8(); // Reserved
        uint16_t lmSize = i.ReadNtohU16();
        NS_ASSERT_MSG(lmSize >= 4 && lmSize <= helloSizeLeft &&
                          (lmSize - 4) % IPV4_ADDRESS_SIZE == 0,
                      "Malformed HELLO link message size");
        for (int n = (lmSize - 4) / IPV4_ADDRESS_SIZE; n; --n)
        {
            lm.neighborInterfaceAddresses.emplace_back(i.ReadNtohU32());
        }
        helloSizeLeft -= lmSize;
        this->linkMessages.push_back(lm);
    }

    return messageSize;
}

// ---------------- OLSR TC Message -------------------------------

// Mode 5 private TC encoding: ANSN(2) + magic(2) + count(2) +
// count * [neighbor IPv4(4), improved ETX(8), energy(8), weight(8)].
// Legacy OLSR TC uses ANSN(2) + reserved(2) + IPv4 addresses.
namespace
{
constexpr uint16_t MODE5_TC_MAGIC = 0x4d54; // "MT"; experimental, not RFC compatible
}

uint32_t
MessageHeader::Tc::GetSerializedSize() const
{
    if (hasMode5Extension)
    {
        NS_ASSERT_MSG(mode5Metrics.size() <= 65535, "Too many Mode5 TC entries");
        return 6 + static_cast<uint32_t>(mode5Metrics.size()) * 28;
    }
    return 4 + this->neighborAddresses.size() * IPV4_ADDRESS_SIZE;
}

void
MessageHeader::Tc::Print(std::ostream& os) const
{
    os << " Adv. SeqNo: " << ansn << " [";
    bool first = true;
    for (const auto& addr : neighborAddresses)
    {
        if (!first) { os << ", "; }
        first = false;
        os << addr;
    }
    os << "]";
    if (hasMode5Extension) { os << " Mode5TC metrics=" << mode5Metrics.size(); }
}

void
MessageHeader::Tc::Serialize(Buffer::Iterator start) const
{
    Buffer::Iterator i = start;
    i.WriteHtonU16(ansn);
    i.WriteHtonU16(hasMode5Extension ? MODE5_TC_MAGIC : 0);
    if (hasMode5Extension)
    {
        NS_ASSERT_MSG(mode5Metrics.size() == neighborAddresses.size(),
                      "Mode5 TC metrics and advertised addresses differ");
        i.WriteHtonU16(static_cast<uint16_t>(mode5Metrics.size()));
        for (const auto& metric : mode5Metrics)
        {
            i.WriteHtonU32(metric.neighbor.Get());
            WriteMode5Double(i, metric.improvedEtx);
            WriteMode5Double(i, metric.residualEnergy);
            WriteMode5Double(i, metric.weight);
        }
        return;
    }
    for (const auto& addr : neighborAddresses)
    {
        i.WriteHtonU32(addr.Get());
    }
}

uint32_t
MessageHeader::Tc::Deserialize(Buffer::Iterator start, uint32_t messageSize)
{
    Buffer::Iterator i = start;
    neighborAddresses.clear();
    mode5Metrics.clear();
    hasMode5Extension = false;
    NS_ASSERT_MSG(messageSize >= 4, "Truncated OLSR TC");
    ansn = i.ReadNtohU16();
    const uint16_t reserved = i.ReadNtohU16();
    if (reserved == MODE5_TC_MAGIC)
    {
        NS_ASSERT_MSG(messageSize >= 6, "Truncated Mode5 TC count");
        const uint16_t count = i.ReadNtohU16();
        NS_ASSERT_MSG(static_cast<uint64_t>(messageSize) == 6ULL + 28ULL * count,
                      "Invalid Mode5 TC payload length");
        hasMode5Extension = true;
        for (uint16_t n = 0; n < count; ++n)
        {
            Mode5Metric metric;
            metric.neighbor = Ipv4Address(i.ReadNtohU32());
            metric.improvedEtx = ReadMode5Double(i);
            metric.residualEnergy = ReadMode5Double(i);
            metric.weight = ReadMode5Double(i);
            neighborAddresses.push_back(metric.neighbor);
            mode5Metrics.push_back(metric);
        }
        return messageSize;
    }
    NS_ASSERT_MSG(reserved == 0, "Unknown OLSR TC reserved field");
    NS_ASSERT_MSG((messageSize - 4) % IPV4_ADDRESS_SIZE == 0,
                  "Invalid legacy OLSR TC address length");
    for (uint32_t n = 0; n < (messageSize - 4) / IPV4_ADDRESS_SIZE; ++n)
    {
        neighborAddresses.emplace_back(i.ReadNtohU32());
    }
    return messageSize;
}

// ---------------- OLSR HNA Message -------------------------------

uint32_t
MessageHeader::Hna::GetSerializedSize() const
{
    return 2 * this->associations.size() * IPV4_ADDRESS_SIZE;
}

void
MessageHeader::Hna::Print(std::ostream& os) const
{
    os << " [";
    bool first = true;
    for (const auto& iAssoc : associations)
    {
        if (first)
        {
            first = false;
        }
        else
        {
            os << ", ";
        }
        os << iAssoc.address << "/" << iAssoc.mask.GetPrefixLength();
    }
    os << "]";
}

void
MessageHeader::Hna::Serialize(Buffer::Iterator start) const
{
    Buffer::Iterator i = start;

    for (size_t n = 0; n < this->associations.size(); ++n)
    {
        i.WriteHtonU32(this->associations[n].address.Get());
        i.WriteHtonU32(this->associations[n].mask.Get());
    }
}

uint32_t
MessageHeader::Hna::Deserialize(Buffer::Iterator start, uint32_t messageSize)
{
    Buffer::Iterator i = start;

    NS_ASSERT(messageSize % (IPV4_ADDRESS_SIZE * 2) == 0);
    int numAddresses = messageSize / IPV4_ADDRESS_SIZE / 2;
    this->associations.clear();
    for (int n = 0; n < numAddresses; ++n)
    {
        Ipv4Address address(i.ReadNtohU32());
        Ipv4Mask mask(i.ReadNtohU32());
        this->associations.push_back(Association{address, mask});
    }
    return messageSize;
}

} // namespace olsr
} // namespace ns3
