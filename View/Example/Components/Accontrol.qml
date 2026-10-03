import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ScrollView {
    id: root
    signal acSettingsRequested(string room)
    signal boilerSettingsRequested()
    contentWidth: availableWidth
    clip: true
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    GridLayout {
        width: root.availableWidth
        columns: width >= 840 ? 3 : (width >= 560 ? 2 : 1)
        columnSpacing: 16
        rowSpacing: 16
        Repeater {
            model: ["Salon", "Jadalnia", "boiler"]
            DeviceCard {
                id: card
                required property string modelData
                property bool isBoiler: modelData === "boiler"
                objectName: "card_" + modelData
                deviceName: isBoiler ? "Ciepła woda" : modelData
                deviceKind: isBoiler ? "Bojler" : "Klimatyzacja"
                iconSource: isBoiler ? "qrc:/icons128/boiler_128.png" : "qrc:/icons128/air-conditioner_128.png"
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: 0
                onSettingsRequested: {
                    if (isBoiler) root.boilerSettingsRequested()
                    else root.acSettingsRequested(modelData)
                }
                onPowerRequested: function(on) {
                    busy = true; failed = false; message = ""
                    backend.apply_device_power(isBoiler ? "boiler" : "ac", modelData, on)
                }
                Connections {
                    target: backend
                    function onTempIndoorChanged(room, value) { if (!card.isBoiler && room === card.modelData) card.currentTemperature = value }
                    function onTargetTemperatureReceived(room, value) { if (room === card.modelData) card.targetTemperature = value }
                    function onModeReceived(room, value) {
                        if (!card.isBoiler && room === card.modelData) { card.mode = value; card.powered = value !== "OFF" && value !== "UNKNOWN" }
                    }
                    function onWaterTemp(room, value) { if (card.isBoiler) card.currentTemperature = value }
                    function onModeOperating(value) { if (card.isBoiler) card.mode = value }
                    function onPowerStatus(value) { if (card.isBoiler) card.powered = value }
                    function onAcSalonOnlineChanged(value) { if (card.modelData === "Salon") card.online = value }
                    function onAcJadalniaOnlineChanged(value) { if (card.modelData === "Jadalnia") card.online = value }
                    function onBoilerOnlineChanged(value) { if (card.isBoiler) card.online = value }
                    function onDevicePowerFinished(kind, room, success, message) {
                        if (room !== card.modelData || kind !== (card.isBoiler ? "boiler" : "ac")) return
                        card.busy = false; card.failed = !success; card.message = message
                    }
                    function onDeviceOperationBusyChanged(kind, room, busy) {
                        if (room === card.modelData && kind === (card.isBoiler ? "boiler" : "ac")) card.transportBusy = busy
                    }
                }
            }
        }
    }
}
