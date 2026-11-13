/**
 * Mode 5 V3 HELLO extension serialization round-trip tests.
 * Added without changing existing OLSR test cases.
 */
class OlsrMode5HelloV3TestCase : public TestCase
{
  public:
    OlsrMode5HelloV3TestCase()
        : TestCase("Mode 5 V3 HELLO extension round-trip: 15, 16, 29 ratios")
    {
    }

  private:
    void DoRun() override
    {
        for (uint32_t count : {15u, 16u, 29u})
        {
            Packet packet;
            olsr::MessageHeader input;
            auto& helloIn = input.GetHello();
            helloIn.SetHTime(Seconds(2));
            helloIn.willingness = olsr::Willingness::HIGH;
            helloIn.hasMode5Extension = true;

            for (uint32_t i = 0; i < 3; ++i)
            {
                helloIn.mode5Position[i] = 100.0 + i;
                helloIn.mode5Velocity[i] = 10.0 + i;
            }
            helloIn.mode5ResidualEnergy = 85.5;
            helloIn.mode5Degree = count;

            for (uint32_t i = 0; i < count; ++i)
            {
                Ipv4Address address(0x0a010100u + i + 1);
                double ratio = 0.5 + 0.01 * i;
                helloIn.mode5ReceptionRatios.emplace_back(address, ratio);
            }

            const uint32_t expectedSize = input.GetSerializedSize();
            packet.AddHeader(input);
            NS_TEST_ASSERT_MSG_EQ(packet.GetSize(), expectedSize,
                                  "Serialized message size mismatch");

            olsr::MessageHeader output;
            const uint32_t removedBytes = packet.RemoveHeader(output);
            const auto& helloOut = output.GetHello();

            NS_TEST_ASSERT_MSG_EQ(removedBytes, expectedSize,
                                  "Removed header size mismatch");
            NS_TEST_ASSERT_MSG_EQ(helloOut.hasMode5Extension, true,
                                  "Mode 5 extension missing");
            NS_TEST_ASSERT_MSG_EQ(helloOut.mode5ReceptionRatios.size(), count,
                                  "Reception ratio count mismatch");
            NS_TEST_ASSERT_MSG_EQ(output.GetSerializedSize(), expectedSize,
                                  "Deserialized size mismatch");
            NS_TEST_ASSERT_MSG_EQ(helloOut.mode5Degree, helloIn.mode5Degree,
                                  "Degree mismatch");
            NS_TEST_ASSERT_MSG_EQ_TOL(helloOut.mode5ResidualEnergy,
                                      helloIn.mode5ResidualEnergy, 1e-12,
                                      "Residual energy mismatch");

            for (uint32_t i = 0; i < 3; ++i)
            {
                NS_TEST_ASSERT_MSG_EQ_TOL(helloOut.mode5Position[i],
                                          helloIn.mode5Position[i], 1e-12,
                                          "Position mismatch");
                NS_TEST_ASSERT_MSG_EQ_TOL(helloOut.mode5Velocity[i],
                                          helloIn.mode5Velocity[i], 1e-12,
                                          "Velocity mismatch");
            }
            for (uint32_t i = 0; i < count; ++i)
            {
                NS_TEST_ASSERT_MSG_EQ(helloOut.mode5ReceptionRatios[i].first,
                                      helloIn.mode5ReceptionRatios[i].first,
                                      "Reception ratio address mismatch");
                NS_TEST_ASSERT_MSG_EQ_TOL(helloOut.mode5ReceptionRatios[i].second,
                                          helloIn.mode5ReceptionRatios[i].second,
                                          1e-12, "Reception ratio value mismatch");
            }
            NS_TEST_ASSERT_MSG_EQ(packet.GetSize(), 0u,
                                  "Unread bytes remain after deserialization");
        }
    }
};
