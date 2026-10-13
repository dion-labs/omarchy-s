"""Adapt pinned Omarchy networking to shared phone NetworkManager ownership."""
def adapt(text):
 text=text.replace('readonly property bool canShareWifi: info.type === "wifi" && canShareNetwork(connectedWifiNetwork)','readonly property bool canShareWifi: false')
 text=text.replace('readonly property bool canRunSpeedTest: !!info.iface','readonly property bool canRunSpeedTest: false')
 begin=text.index('      Column {\n        width: parent.width\n        spacing: Style.space(10)\n\n        PanelSectionHeader {\n          text: "DNS PROVIDER"')
 end=text.index('      // Wi-Fi networks',begin)
 text=text[:begin]+'      // Global DNS remains managed by the phone.\n'+text[end:]
 begin=text.index('          } else if (root.focusSection === "dns") {')
 end=text.index('          } else {  // wifi',begin)
 text=text[:begin]+text[end:]
 text=text.replace('else if (root.focusSection === "dns") root.selectDnsByDelta(dx)','')
 text=text.replace('else if (root.focusSection === "dns") root.activateDns()','')
 text=text.replace('property string focusSection: "dns"','property string focusSection: "header"')
 text=text.replace('root.focusSection = "dns"','root.focusSection = root.wifiNetworks.length > 0 ? "wifi" : "header"')
 text=text.replace('focusSection = "dns"','focusSection = "header"')
 text=text.replace(': "dns"',': "header"')
 text=text.replace('''if (dy < 0 && root.selectedIndex <= 0) {
              root.focusSection = root.wifiNetworks.length > 0 ? "wifi" : "header"''','''if (dy < 0 && root.selectedIndex <= 0) {
              root.focusSection = root.canSelectBand ? "band" : (root.hasCaptivePortal ? "portal" : "header")
              root.bandAutoFocused = !root.bandPillsVisible''')
 block='''    if (!dnsProc.running) {
      dnsProc.command = ["bash", "-c", root.dnsCommand("")]
      dnsProc.running = true
    }
'''
 assert text.count(block)==1;text=text.replace(block,'')
 text=text.replace('''  onWifiDeviceChanged: {
    setScannerEnabled(true)''','''  onWifiDeviceChanged: {
    setScannerEnabled(root.opened)''')
 text=text.replace('    target: "omarchy.network"','''    target: "omarchy.network"
    function portStatus(): string {
      return JSON.stringify({network_manager: root.networkManagerAvailable, wifi_present: !!root.wifiDevice, wifi_enabled: Networking.wifiEnabled, connected: !!root.connectedWifiNetwork, kind: root.kind})
    }''')
 return text
