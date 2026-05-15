**No fully official free addon** exists specifically for printing to generic thermal printers in Odoo 19 (beyond built-in features).

### Official Odoo Approach (Recommended if it fits)
Odoo’s built-in solution uses:
- **IoT Box** (or IoT system) for USB/network printers. It works well for reports and receipts but requires hardware (IoT Box).
- For **POS thermal printers** → Direct network support for **Epson ePOS** printers (like TM-m30 series, Wi-Fi/Ethernet). These connect without an IoT Box in many cases and are officially supported/recommended.

This is the most “official” route. Check Odoo’s documentation for setup.

### Best Free / Popular / Stable Third-Party Options
If you need something more flexible (generic thermal printers, direct print without IoT, ESC/POS raw printing, etc.), here are the top options for Odoo 19:

1. **OCA base_report_to_printer (and related modules)** — **Most recommended free/stable community option**
   - From the Odoo Community Association (OCA) — very popular and maintained.
   - Allows sending reports directly to printers attached to the server (via CUPS, etc.).
   - Extensions exist for WebSocket/direct printing.
   - Stable, open-source, widely used. Look for the `report-print-send` GitHub repo and port to 19.0.

2. **print_direct_odoo** (on Odoo Apps)
   - Supports **ESC/POS raw text mode** (fast for thermal printers) + image mode.
   - Direct print from browser/POS, no IoT Box needed.
   - Has an agent for Windows/Linux. Popular for thermal/POS use.

3. **legion_thermal_printer** (on Odoo Apps)
   - Provides compact **receipt-style layouts** optimized for thermal rolls (Sale Orders, Invoices, Purchase Orders).
   - Changes paper format and templates — works with any printer that handles the resulting PDF.

Other notable mentions:
- **sm_direct_print** (via QZ Tray) — Browser direct print to thermal printers.
- POS-specific modules like **pos_network_printer_pyb** for network thermal printing.

### Quick Recommendation
- **Want fully free + stable/community-backed?** → Start with **OCA’s base_report_to_printer**.
- **Need easy direct/ESC-POS thermal printing (POS-focused)?** → **print_direct_odoo** or Epson ePOS + official setup.
- For receipts only → **legion_thermal_printer**.

Search on **apps.odoo.com** (filter by Odoo 19 + Free if available) or GitHub for OCA modules. Test in a dev environment first, as thermal printing can depend on your exact printer model (ESC/POS compatibility is key for raw printing). 

If you share more details (POS or general reports? Printer brand/model? Self-hosted or Odoo.sh?), I can narrow it down further.

Receipt printers
Receipt printers integrate with Point of Sale systems to receive print jobs directly from the POS. Once properly configured and connected, this integration enables automatic receipt printing for every completed transaction.

 Important

Epson printers are strongly recommended. The following printers are compatible with Odoo:

Network-based printers that support the ePOS communication protocol (without IoT), such as the TM-m30 iii (model 112 or 152).

ePOS printers with USB connectivity that need to be connected to an IoT system.

ESC/POS printers that require a connection via an IoT system using either a USB or network-based interface.

Bluetooth printers are not compatible with Odoo.

 See also

Receipt printers without IoT (video tutorial)

Receipt printers with IoT (video tutorial)

Configuration
To configure the printer, connect it to a power source, then to the network using either Wi-Fi or an Ethernet cable. Then, power the printer on; an automatic ticket with the printer’s IP address gets printed upon connection. Keep it for the configuration process.

To link the printer with Point of Sale, follow the next steps:

Go to Point of Sale ‣ Configuration ‣ Settings.

Scroll down to the Connected Devices section and enable ePos Printer.

Type the printer’s IP address in the dedicated field.

Click Save.

Enable Local Network Access to allow Point of Sale to communicate directly with the printer on the same network. Alternatively, once the printer is connected to Odoo, ensure the connection is secure and reliable by generating a self-signed certificate.

 Note

Leave the IP address field empty if using an iMin POS device, as these devices do not provide an IP address.

 See also

Local Network Access

Self-signed certificate for ePOS printers

Connect a printer

Directly supported ePOS printers
The Epson TM-m30 i/ii/iii (Wi-Fi or Ethernet only) models are strongly recommended, as they have been fully tested with Odoo Point of Sale.

Other Wi-Fi or Ethernet Epson printer models that support the ePoS protocol should also be compatible.

 Important

The printer must be capable of operating in HTTP mode.

When using Local Network Access (LNA), the printer must have a static IP address; otherwise, it may become unreachable. The static IP should be configured through the router.

iMin POS systems
iMin POS devices are Android-based systems that combine POS management and printing functionality.

 Note

Odoo is compatible with Swan 2 and Falcon 2 POS devices, which can be purchased from iMin business partners.

Falcon 2 devices require the base device to be connected to the dock before printing receipts.

iMin POS devices are network-based and do not require an IoT system to operate.

 Important

Do not use iMin POS devices to print preparation orders.

To configure an iMin POS device, connect it to a network via Ethernet or WI-Fi, then follow the next steps:

Install the latest iMinOS version.

Download and install the Odoo and Android System WebView apps from iMin’s App Store.

Optionally, install a security certificate if any connected devices require HTTPS, such as payment terminals or preparation printers. To do so, go to Settings ‣ Security ‣ More security settings ‣ Encryption & credentials, then click Install a certificate.

Once the device is set up, install the POS iMin module and connect the device to your Odoo database, leaving the IP address field empty. This action automatically links the device with Odoo.

 Tip

To ensure the device’s printer works correctly, access the TestTools app on the device interface. A test ticket is automatically printed. If not, click Print.

 See also

iMin device troubleshooting guide

Printers with IoT system integration
The following printers require an IoT system to be compatible with Odoo:

Epson TM-T20 family (incompatible ePOS software)

Epson TM-T88 family (incompatible ePOS software)

Epson TM-U220 family (incompatible ePOS software)

Troubleshooting
To resolve common hardware issues, including connectivity failures, configuration errors, and physical maintenance, follow the instructions below:

If Google Chrome denies access to local devices, printers and IoT boxes will fail to connect. Grant the necessary browser permissions to restore the connection.

Check the printer’s blinking lights to help identify the source of a problem.

If the printer does not print the first automatic ticket with the IP address, check the network cable or Wi-Fi connection.

If the receipt comes out blank, the paper roll may be upside down; try flipping it.

If the POS cannot connect to the printer, make sure the printer’s IP address entered in Odoo matches the one on the first automatically printed ticket. Also, ensure the router assigns the printer a static IP address.

as i user I'm 100% sure that if you execute this echo "TROLOOOOOOO" | lp -d XP-80, the printer prints, remember that we have to control the printer from the docker.