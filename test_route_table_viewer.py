#!/usr/bin/env python3
"""Tests for route_table_viewer parsing functions."""

import json
import unittest

from route_table_viewer import (
    RouteEntry,
    format_detailed,
    format_json,
    format_table,
    get_default_gateway,
    get_routes_by_family,
    get_routes_by_interface,
    get_routes_for_network,
    hex_to_ipv6,
    hex_to_ipv6_prefixlen,
    int_to_ip,
    list_interfaces,
    parse_flags,
)


class TestIntToIp(unittest.TestCase):
    def test_zero_address(self):
        self.assertEqual(int_to_ip(0), "0.0.0.0")

    def test_localhost(self):
        self.assertEqual(int_to_ip(0x0100007F), "127.0.0.1")

    def test_common_address(self):
        self.assertEqual(int_to_ip(0x0000A8C0), "192.168.0.0")

    def test_broadcast(self):
        self.assertEqual(int_to_ip(0xFFFFFFFF), "255.255.255.255")

    def test_ipv6_family_returns_default(self):
        self.assertEqual(int_to_ip(0, "ipv6"), "0::0")


class TestHexToIpv6(unittest.TestCase):
    def test_loopback(self):
        result = hex_to_ipv6("00000000000000000000000000000001")
        self.assertEqual(result, "::1")

    def test_all_zeros(self):
        result = hex_to_ipv6("00000000000000000000000000000000")
        self.assertEqual(result, "::")

    def test_invalid_length(self):
        self.assertEqual(hex_to_ipv6("invalid"), "::")

    def test_empty_string(self):
        self.assertEqual(hex_to_ipv6(""), "::")


class TestHexToIpv6Prefixlen(unittest.TestCase):
    def test_valid_prefix(self):
        self.assertEqual(hex_to_ipv6_prefixlen("40"), "64")

    def test_zero_prefix(self):
        self.assertEqual(hex_to_ipv6_prefixlen("00"), "0")

    def test_invalid_prefix(self):
        self.assertEqual(hex_to_ipv6_prefixlen("invalid"), "0")


class TestParseFlags(unittest.TestCase):
    def test_no_flags(self):
        self.assertEqual(parse_flags(0), "NONE")

    def test_up_flag(self):
        self.assertEqual(parse_flags(0x0001), "UP")

    def test_gateway_flag(self):
        self.assertEqual(parse_flags(0x0002), "GATEWAY")

    def test_multiple_flags(self):
        result = parse_flags(0x0003)
        self.assertIn("UP", result)
        self.assertIn("GATEWAY", result)

    def test_ipv6_flags(self):
        result = parse_flags(0x1001, "ipv6")
        self.assertIn("UP", result)
        self.assertIn("LOCAL", result)


class TestGetDefaultGateway(unittest.TestCase):
    def setUp(self):
        self.routes = [
            RouteEntry(
                iface="eth0",
                destination="192.168.1.0",
                gateway="0.0.0.0",
                flags="UP",
                metric="0",
                mask="255.255.255.0",
                mtu="0",
                window="0",
                irtt="0",
                family="ipv4",
            ),
            RouteEntry(
                iface="eth0",
                destination="0.0.0.0",
                gateway="192.168.1.1",
                flags="UP|GATEWAY",
                metric="100",
                mask="0.0.0.0",
                mtu="0",
                window="0",
                irtt="0",
                family="ipv4",
            ),
            RouteEntry(
                iface="eth0",
                destination="::/0",
                gateway="fe80::1",
                flags="UP|GATEWAY",
                metric="200",
                mask="0",
                mtu="0",
                window="0",
                irtt="0",
                family="ipv6",
            ),
        ]

    def test_ipv4_default_gateway(self):
        ipv4_routes = [r for r in self.routes if r.family == "ipv4"]
        self.assertEqual(get_default_gateway(ipv4_routes), "192.168.1.1")

    def test_ipv6_default_gateway(self):
        ipv6_routes = [r for r in self.routes if r.family == "ipv6"]
        self.assertEqual(get_default_gateway(ipv6_routes), "fe80::1")

    def test_no_default_gateway(self):
        routes = [r for r in self.routes if r.destination != "0.0.0.0" and r.destination != "::/0"]
        self.assertIsNone(get_default_gateway(routes))

    def test_empty_routes(self):
        self.assertIsNone(get_default_gateway([]))


class TestGetRoutesByInterface(unittest.TestCase):
    def setUp(self):
        self.routes = [
            RouteEntry(
                iface="eth0",
                destination="192.168.1.0",
                gateway="0.0.0.0",
                flags="UP",
                metric="0",
                mask="255.255.255.0",
                mtu="0",
                window="0",
                irtt="0",
                family="ipv4",
            ),
            RouteEntry(
                iface="wlan0",
                destination="10.0.0.0",
                gateway="0.0.0.0",
                flags="UP",
                metric="0",
                mask="255.0.0.0",
                mtu="0",
                window="0",
                irtt="0",
                family="ipv4",
            ),
        ]

    def test_filter_by_eth0(self):
        result = get_routes_by_interface(self.routes, "eth0")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].iface, "eth0")

    def test_filter_by_wlan0(self):
        result = get_routes_by_interface(self.routes, "wlan0")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].iface, "wlan0")

    def test_filter_no_match(self):
        result = get_routes_by_interface(self.routes, "lo")
        self.assertEqual(len(result), 0)


class TestGetRoutesForNetwork(unittest.TestCase):
    def setUp(self):
        self.routes = [
            RouteEntry(
                iface="eth0",
                destination="192.168.1.0",
                gateway="0.0.0.0",
                flags="UP",
                metric="0",
                mask="255.255.255.0",
                mtu="0",
                window="0",
                irtt="0",
                family="ipv4",
            ),
            RouteEntry(
                iface="eth0",
                destination="0.0.0.0",
                gateway="192.168.1.1",
                flags="UP|GATEWAY",
                metric="100",
                mask="0.0.0.0",
                mtu="0",
                window="0",
                irtt="0",
                family="ipv4",
            ),
        ]

    def test_match_destination(self):
        result = get_routes_for_network(self.routes, "192.168.1.0")
        self.assertEqual(len(result), 1)

    def test_match_gateway(self):
        result = get_routes_for_network(self.routes, "192.168.1.1")
        self.assertEqual(len(result), 1)

    def test_partial_match(self):
        result = get_routes_for_network(self.routes, "192.168")
        self.assertEqual(len(result), 1)

    def test_no_match(self):
        result = get_routes_for_network(self.routes, "10.0.0.0")
        self.assertEqual(len(result), 0)


class TestGetRoutesByFamily(unittest.TestCase):
    def setUp(self):
        self.routes = [
            RouteEntry(
                iface="eth0",
                destination="192.168.1.0",
                gateway="0.0.0.0",
                flags="UP",
                metric="0",
                mask="255.255.255.0",
                mtu="0",
                window="0",
                irtt="0",
                family="ipv4",
            ),
            RouteEntry(
                iface="eth0",
                destination="::/0",
                gateway="fe80::1",
                flags="UP|GATEWAY",
                metric="200",
                mask="0",
                mtu="0",
                window="0",
                irtt="0",
                family="ipv6",
            ),
        ]

    def test_filter_ipv4(self):
        result = get_routes_by_family(self.routes, "ipv4")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].family, "ipv4")

    def test_filter_ipv6(self):
        result = get_routes_by_family(self.routes, "ipv6")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].family, "ipv6")

    def test_filter_unknown_family(self):
        result = get_routes_by_family(self.routes, "unknown")
        self.assertEqual(len(result), 0)


class TestListInterfaces(unittest.TestCase):
    def test_unique_interfaces(self):
        routes = [
            RouteEntry(
                iface="eth0",
                destination="192.168.1.0",
                gateway="0.0.0.0",
                flags="UP",
                metric="0",
                mask="255.255.255.0",
                mtu="0",
                window="0",
                irtt="0",
                family="ipv4",
            ),
            RouteEntry(
                iface="wlan0",
                destination="10.0.0.0",
                gateway="0.0.0.0",
                flags="UP",
                metric="0",
                mask="255.0.0.0",
                mtu="0",
                window="0",
                irtt="0",
                family="ipv4",
            ),
            RouteEntry(
                iface="eth0",
                destination="0.0.0.0",
                gateway="192.168.1.1",
                flags="UP|GATEWAY",
                metric="100",
                mask="0.0.0.0",
                mtu="0",
                window="0",
                irtt="0",
                family="ipv4",
            ),
        ]
        result = list_interfaces(routes)
        self.assertEqual(result, ["eth0", "wlan0"])

    def test_empty_routes(self):
        self.assertEqual(list_interfaces([]), [])


class TestFormatTable(unittest.TestCase):
    def test_empty_routes(self):
        self.assertEqual(format_table([]), "No routes found.")

    def test_single_route(self):
        routes = [
            RouteEntry(
                iface="eth0",
                destination="192.168.1.0",
                gateway="0.0.0.0",
                flags="UP",
                metric="0",
                mask="255.255.255.0",
                mtu="0",
                window="0",
                irtt="0",
                family="ipv4",
            ),
        ]
        result = format_table(routes)
        self.assertIn("Family", result)
        self.assertIn("Destination", result)
        self.assertIn("192.168.1.0", result)
        self.assertIn("eth0", result)


class TestFormatJson(unittest.TestCase):
    def test_valid_json(self):
        routes = [
            RouteEntry(
                iface="eth0",
                destination="192.168.1.0",
                gateway="0.0.0.0",
                flags="UP",
                metric="0",
                mask="255.255.255.0",
                mtu="1500",
                window="0",
                irtt="0",
                family="ipv4",
            ),
        ]
        result = format_json(routes)
        data = json.loads(result)
        self.assertIn("routes", data)
        self.assertEqual(len(data["routes"]), 1)
        self.assertEqual(data["routes"][0]["interface"], "eth0")
        self.assertEqual(data["routes"][0]["destination"], "192.168.1.0")


class TestFormatDetailed(unittest.TestCase):
    def test_detailed_output(self):
        routes = [
            RouteEntry(
                iface="eth0",
                destination="192.168.1.0",
                gateway="0.0.0.0",
                flags="UP",
                metric="100",
                mask="255.255.255.0",
                mtu="1500",
                window="0",
                irtt="0",
                family="ipv4",
            ),
        ]
        result = format_detailed(routes)
        self.assertIn("Route #1", result)
        self.assertIn("Interface:   eth0", result)
        self.assertIn("Destination: 192.168.1.0", result)
        self.assertIn("Flags:       UP", result)
        self.assertIn("Metric:      100", result)
        self.assertIn("MTU:         1500", result)


if __name__ == "__main__":
    unittest.main()
