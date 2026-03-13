#!/usr/bin/env python3
"""
Route Table Viewer - CLI tool to view and inspect system routing tables.
"""

import argparse
import socket
import struct
import sys
from collections import namedtuple
from typing import List, Optional

RouteEntry = namedtuple(
    "RouteEntry",
    ["iface", "destination", "gateway", "flags", "metric", "mask", "mtu", "window", "irtt"],
)

FLAG_MAP = {
    0x0001: "UP",
    0x0002: "GATEWAY",
    0x0004: "HOST",
    0x0008: "REINSTATE",
    0x0010: "DYNAMIC",
    0x0020: "MODIFIED",
    0x0040: "ADDRCONF",
    0x0100: "CACHE",
    0x0200: "XRESOLVE",
}


def int_to_ip(ip_int: int) -> str:
    """Convert a 32-bit integer to dotted decimal IP address."""
    try:
        return socket.inet_ntoa(struct.pack("<I", ip_int))
    except struct.error:
        return "0.0.0.0"


def parse_flags(flag_value: int) -> str:
    """Convert numeric flag value to human-readable flag string."""
    flags = []
    for bit, name in FLAG_MAP.items():
        if flag_value & bit:
            flags.append(name)
    return "|".join(flags) if flags else "NONE"


def read_proc_route() -> List[RouteEntry]:
    """Read routing table from /proc/net/route."""
    routes = []
    try:
        with open("/proc/net/route", "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return routes
    except PermissionError:
        print("Error: Permission denied reading /proc/net/route", file=sys.stderr)
        return routes

    for line in lines[1:]:
        parts = line.strip().split()
        if len(parts) < 8:
            continue

        iface = parts[0]
        dest_hex = parts[1]
        gateway_hex = parts[2]
        flags_hex = parts[3]
        ref_cnt = parts[4]
        use_cnt = parts[5]
        metric_hex = parts[6]
        mask_hex = parts[7]

        mtu = "0"
        window = "0"
        irtt = "0"
        if len(parts) >= 11:
            mtu = parts[8]
            window = parts[9]
            irtt = parts[10]

        try:
            dest_int = int(dest_hex, 16)
            gateway_int = int(gateway_hex, 16)
            flags_int = int(flags_hex, 16)
            metric_int = int(metric_hex, 16)
            mask_int = int(mask_hex, 16)

            destination = int_to_ip(dest_int)
            gateway = int_to_ip(gateway_int)
            mask = int_to_ip(mask_int)

            entry = RouteEntry(
                iface=iface,
                destination=destination,
                gateway=gateway,
                flags=parse_flags(flags_int),
                metric=str(metric_int),
                mask=mask,
                mtu=mtu,
                window=window,
                irtt=irtt,
            )
            routes.append(entry)
        except ValueError:
            continue

    return routes


def get_default_gateway(routes: List[RouteEntry]) -> Optional[str]:
    """Find the default gateway from the routing table."""
    for route in routes:
        if route.destination == "0.0.0.0" and "GATEWAY" in route.flags:
            return route.gateway
    return None


def get_routes_by_interface(routes: List[RouteEntry], interface: str) -> List[RouteEntry]:
    """Filter routes by interface name."""
    return [r for r in routes if r.iface == interface]


def get_routes_for_network(routes: List[RouteEntry], network: str) -> List[RouteEntry]:
    """Filter routes that match a specific network or IP."""
    matching = []
    for route in routes:
        if route.destination == network or route.gateway == network:
            matching.append(route)
    return matching


def format_table(routes: List[RouteEntry], show_all: bool = True) -> str:
    """Format routes as a readable table."""
    if not routes:
        return "No routes found."

    headers = ["Destination", "Gateway", "Genmask", "Flags", "Metric", "Ref", "Use", "Iface"]
    
    col_widths = [
        max(len(headers[0]), max((len(r.destination) for r in routes), default=0)),
        max(len(headers[1]), max((len(r.gateway) for r in routes), default=0)),
        max(len(headers[2]), max((len(r.mask) for r in routes), default=0)),
        max(len(headers[3]), max((len(r.flags) for r in routes), default=0)),
        max(len(headers[4]), max((len(r.metric) for r in routes), default=0)),
        5,
        5,
        max(len(headers[7]), max((len(r.iface) for r in routes), default=0)),
    ]

    lines = []
    header_line = "  ".join(h.ljust(w) for h, w in zip(headers, col_widths))
    lines.append(header_line)
    lines.append("-" * len(header_line))

    for route in routes:
        row = [
            route.destination.ljust(col_widths[0]),
            route.gateway.ljust(col_widths[1]),
            route.mask.ljust(col_widths[2]),
            route.flags.ljust(col_widths[3]),
            route.metric.ljust(col_widths[4]),
            route.ref.ljust(col_widths[5]) if hasattr(route, 'ref') else "0".ljust(col_widths[5]),
            route.use.ljust(col_widths[6]) if hasattr(route, 'use') else "0".ljust(col_widths[6]),
            route.iface.ljust(col_widths[7]),
        ]
        lines.append("  ".join(row))

    return "\n".join(lines)


def format_detailed(routes: List[RouteEntry]) -> str:
    """Format routes with detailed information."""
    lines = []
    for i, route in enumerate(routes, 1):
        lines.append(f"Route #{i}")
        lines.append(f"  Interface:   {route.iface}")
        lines.append(f"  Destination: {route.destination}")
        lines.append(f"  Gateway:     {route.gateway}")
        lines.append(f"  Netmask:     {route.mask}")
        lines.append(f"  Flags:       {route.flags}")
        lines.append(f"  Metric:      {route.metric}")
        lines.append(f"  MTU:         {route.mtu}")
        lines.append(f"  IRTT:        {route.irtt}")
        lines.append("")
    return "\n".join(lines)


def list_interfaces(routes: List[RouteEntry]) -> List[str]:
    """Get unique interface names from routes."""
    interfaces = set()
    for route in routes:
        interfaces.add(route.iface)
    return sorted(interfaces)


def main():
    parser = argparse.ArgumentParser(
        description="View and inspect system routing tables",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Show all routes in table format
  %(prog)s --detailed         Show detailed route information
  %(prog)s --interface eth0   Filter routes by interface
  %(prog)s --default          Show only the default gateway
  %(prog)s --interfaces       List all network interfaces
        """,
    )

    parser.add_argument(
        "-d", "--detailed",
        action="store_true",
        help="Show detailed route information",
    )
    parser.add_argument(
        "-i", "--interface",
        type=str,
        metavar="IFACE",
        help="Filter routes by interface name",
    )
    parser.add_argument(
        "-n", "--network",
        type=str,
        metavar="NETWORK",
        help="Filter routes for a specific network or IP",
    )
    parser.add_argument(
        "--default",
        action="store_true",
        dest="show_default",
        help="Show only the default gateway",
    )
    parser.add_argument(
        "--interfaces",
        action="store_true",
        help="List all network interfaces with routes",
    )
    parser.add_argument(
        "--no-header",
        action="store_true",
        help="Suppress header output",
    )

    args = parser.parse_args()

    routes = read_proc_route()

    if not routes:
        print("No routing table entries found.", file=sys.stderr)
        sys.exit(1)

    if args.show_default:
        gateway = get_default_gateway(routes)
        if gateway:
            print(gateway)
        else:
            print("No default gateway found.", file=sys.stderr)
            sys.exit(1)
        return

    if args.interfaces:
        interfaces = list_interfaces(routes)
        for iface in interfaces:
            print(iface)
        return

    if args.interface:
        routes = get_routes_by_interface(routes, args.interface)
        if not routes:
            print(f"No routes found for interface: {args.interface}", file=sys.stderr)
            sys.exit(1)

    if args.network:
        routes = get_routes_for_network(routes, args.network)
        if not routes:
            print(f"No routes found for network: {args.network}", file=sys.stderr)
            sys.exit(1)

    if not args.no_header and not args.detailed:
        print(f"Routing Table ({len(routes)} entries)\n")

    if args.detailed:
        output = format_detailed(routes)
    else:
        output = format_table(routes)

    print(output)


if __name__ == "__main__":
    main()
