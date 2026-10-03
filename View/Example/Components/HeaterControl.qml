import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ScrollView {
    id: root
    signal settingsRequested(string room)
    contentWidth: availableWidth
    clip: true
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    GridLayout {
        width: root.availableWidth
        columns: width >= 840 ? 3 : (width >= 560 ? 2 : 1)
        columnSpacing: 16
        rowSpacing: 16
        Repeater {
            model: ["Juras", "Migacze", "Julia"]
            DeviceCard {
                id: card
                required property string modelData
                objectName: "card_" + modelData
                deviceName: modelData
                deviceKind: "Grzejnik"
                iconSource: "qrc:/icons128/heater_128_2.png"
                powerLabel: "Nadpisanie temperatury"
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: 0
                onSettingsRequested: root.settingsRequested(modelData)
                onPowerRequested: function(on) {
                    busy = true; failed = false; message = ""
                    backend.apply_device_power("heater", modelData, on)
                }
                Connections {
                    target: backend
                    function onHeaterCurrentTempChanged(room, value) { if (room === card.modelData) card.currentTemperature = value }
                    function onHeaterTargetTempChanged(room, value) { if (room === card.modelData) card.targetTemperature = value }
                    function onHeaterModeChanged(room, value) { if (room === card.modelData) card.mode = value }
                    function onHeaterOnlineChanged(room, value) { if (room === card.modelData) card.online = value }
                    function onHeaterPowerChanged(room, value) { if (room === card.modelData) card.powered = value }
                    function onDeviceStaleChanged(kind, room, stale) {
                        if (kind === "heater" && room === card.modelData) card.stale = stale
                    }
                    function onDevicePowerFinished(kind, room, success, message) {
                        if (kind !== "heater" || room !== card.modelData) return
                        card.busy = false; card.failed = !success; card.message = message
                    }
                    function onDeviceOperationBusyChanged(kind, room, busy) {
                        if (kind === "heater" && room === card.modelData) card.transportBusy = busy
                    }
                }
            }
        }
    }
}
