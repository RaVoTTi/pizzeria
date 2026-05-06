# Network & Hardware Setup — Pizzeria El Gordo

## Static IP Assignments

Assign these in your router's DHCP reservation / static binding table:

| Device | MAC Address | Static IP | Notes |
|--------|-------------|-----------|-------|
| Mini PC (Server) | _(find with `ip link`) | 192.168.1.100 | Must never change |
| Thermal Printer | _(check printer menu)_ | 192.168.1.200 | ESC/POS compatible, Ethernet only |
| Router | — | 192.168.1.1 | Default gateway |
| Tablet 1 | — | DHCP (dynamic OK) | Connects to elgordo.local |
| Tablet 2 | — | DHCP (dynamic OK) | Connects to elgordo.local |

### How to find your MAC address (Mini PC)

```bash
ip link
# Look for the ethernet interface (eth0, enp0s3, etc.)
# The "link/ether" field is your MAC address
```

### How to set static IPs on your router

1. Open browser → `http://192.168.1.1` (your router admin page)
2. Find **DHCP → Static Lease** or **Address Reservation**
3. For each device: enter MAC address → assign the IP from the table above
4. Save and reboot the router

## Local DNS Configuration

### Option A: Router DNS (Recommended)

Most routers allow you to add local DNS entries:

1. Go to router admin → **LAN → DNS Mapping** (or similar)
2. Add entry: `elgordo.local` → `192.168.1.100`
3. Save and apply

If your router doesn't support local DNS entries, use Option B.

### Option B: Android Tablet Hosts File (Alternative)

If you can't modify router DNS, configure each tablet:

1. **Root the tablet** (required for /etc/hosts modification)
2. Use a hosts editor app (e.g., "Hosts Editor" from F-Droid)
3. Add entry:
   ```
   192.168.1.100  elgordo.local
   ```
4. Or simply bookmark `http://192.168.1.100` in Chrome and add to home screen

### Option C: Local DNS Server on the Mini PC

If neither A nor B works, install `dnsmasq` on the Mini PC:

```bash
sudo apt install dnsmasq
echo "address=/elgordo.local/192.168.1.100" | sudo tee -a /etc/dnsmasq.conf
sudo systemctl restart dnsmasq
```

Then configure your router's DHCP to advertise `192.168.1.100` as the DNS server.

## Hardware Checklist

### Server (Mini PC)

- [ ] Mini PC with at least **4GB RAM** and **64GB SSD**
  - Recommended: Intel NUC, Dell Optiplex Micro, or Lenovo ThinkCentre Tiny
  - Refurbished units work great and cost $100-200
- [ ] Ubuntu Server 22.04 LTS installed
- [ ] Docker + Docker Compose installed (`sudo apt install docker.io docker-compose-plugin`)
- [ ] Ethernet connection (NOT WiFi — reliability matters)

### Tablets (1-2x)

- [ ] Android tablet with Chrome browser
  - Minimum 8" screen for POS readability
  - Samsung Galaxy Tab A8 or similar recommended
- [ ] Connected to the same LAN as the server

### Thermal Printer

- [ ] **ESC/POS compatible** thermal printer with **Ethernet port**
  - Recommended: Epson TM-T20III or Star TSP143IV
  - DO NOT use Bluetooth or USB printers — they fail under load
- [ ] Connected to LAN via Ethernet cable
- [ ] Static IP set: `192.168.1.200`
- [ ] Paper width: 80mm standard

### UPS (Uninterruptible Power Supply)

- [ ] Minimum **600VA** UPS (covers: Mini PC + Router + Printer)
  - Recommended: 1000VA for comfortable runtime (APC Back-UPS or CyberPower)
- [ ] Connected devices:
  1. Mini PC (server)
  2. Router
  3. Thermal Printer (if it has a power brick; skip if it draws too much)
- [ ] Test: unplug UPS from wall, verify server stays on for at least 15 minutes

## Ubuntu Server Setup (Quick Reference)

```bash
# After installing Ubuntu Server, run:
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose-plugin

# Add your user to docker group
sudo usermod -aG docker $USER

# Clone/copy the project
mkdir -p ~/pizzeria && cd ~/pizzeria

# Copy docker-compose.yml, .env, config/, scripts/

# Start the stack
docker compose up -d

# Verify
docker compose ps
curl http://elgordo.local
```

## Cron Job — Nightly Backups

```bash
# Edit crontab
crontab -e

# Add this line (runs every night at 3:00 AM):
0 3 * * * /home/YOUR_USER/pizzeria/scripts/backup.sh >> /home/YOUR_USER/pizzeria/backups/backup.log 2>&1
```