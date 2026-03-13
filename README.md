# route-table-viewer

A simple CLI tool to view and inspect your system's routing table. Because sometimes `ip route` gives you too much and `netstat -rn` feels too old-school.

## What it does

Reads `/proc/net/route` and displays your routing table in a clean, readable format. Also lets you filter by interface, find the default gateway, or get detailed info about specific routes.

## Installation

No installation needed really. Just grab the script and run it.

```bash
chmod +x route_table_viewer.py
./route_table_viewer.py
```

Or if you want to be fancy:

```bash
sudo pip install -r requirements.txt
python3 route_table_viewer.py
```

## Usage

Show all routes:
```bash
python3 route_table_viewer.py
```

Detailed view with all the juicy details:
```bash
python3 route_table_viewer.py --detailed
```

Filter by interface:
```bash
python3 route_table_viewer.py --interface eth0
```

Just give me the default gateway:
```bash
python3 route_table_viewer.py --default
```

List all interfaces that have routes:
```bash
python3 route_table_viewer.py --interfaces
```

## Output format

The default table output looks like:

```
Routing Table (5 entries)

Destination      Gateway          Genmask         Flags   Metric  Ref  Use  Iface
---------------------------------------------------------------------------
0.0.0.0          192.168.1.1      0.0.0.0         UP|GATEWAY  0    0    0    eth0
192.168.1.0      0.0.0.0          255.255.255.0   UP        0    0    0    eth0
```

## Why I wrote this

Honestly, I just wanted something that:
- Shows the routing table without a million options
- Has a `--default` flag to quickly grab the gateway
- Is easy to script against
- Doesn't require parsing `ip route` output which changes between distros

## Requirements

- Python 3.6+
- Linux (reads `/proc/net/route`)
- Root or read access to `/proc/net/route`

## Notes

- This only works on Linux since it reads `/proc/net/route` directly
- IPv6 routes are not supported (yet)
- The flags are decoded from the numeric values in the proc file

## License

Do whatever you want with it.
