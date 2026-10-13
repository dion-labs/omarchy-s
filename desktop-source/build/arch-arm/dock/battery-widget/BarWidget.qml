import QtQuick
import Quickshell.Io
import qs.Commons
import qs.Ui

// Native S9+ gauge; intentionally no power-control or system-bus interface.
BarWidget {
  id: root
  moduleName: "omarchy.power"
  property int percentage: -1
  property string chargeState: "Unknown"
  readonly property string label: percentage < 0 ? "Battery —" : percentage + "%"
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  FileView {
    id: capacity
    path: "/sys/class/power_supply/max170xx_battery/capacity"
    onLoaded: {
      var raw = text().trim()
      var value = Number(raw)
      root.percentage = /^\d+$/.test(raw) && value >= 0 && value <= 100 ? value : -1
    }
    onLoadFailed: root.percentage = -1
  }
  FileView {
    id: status
    path: "/sys/class/power_supply/max170xx_battery/status"
    onLoaded: root.chargeState = text().trim() || "Unknown"
    onLoadFailed: root.chargeState = "Unknown"
  }
  Timer {
    interval: 15000
    running: true
    repeat: true
    onTriggered: { capacity.reload(); status.reload() }
  }
  ShellIpc {
    target: "omarchy.power"
    function portStatus(): string {
      return JSON.stringify({ percentage: root.percentage, state: root.chargeState, read_only: true })
    }
  }
  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: root.label
    labelVisible: true
    horizontalMargin: 8.75
    tooltipText: "Phone battery · " + root.chargeState
  }
}
