import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "Ui.js" as Ui

SettingsPopup {
    id: root
    objectName: "boilerPopup"
    operationKind: "boiler"
    property string selectedMode: ""
    heading: "Ciepła woda"
    subtitle: "Temperatura i tryb bojlera"
    canApply: loaded && isFinite(temperature.value) && selectedMode !== ""
    onOpened: { reset(); backend.load_device_settings("boiler", "boiler") }
    onApplyRequested: backend.apply_water_heater_settings(temperature.value, selectedMode)
    TemperatureStepper { id: temperature; minimum: 40; maximum: 65; Layout.fillWidth: true }
    Label { id: current; color: "#a9b8c6"; font.pixelSize: 16 }
    Label { text: "Tryb pracy"; color: "#a9b8c6"; font.pixelSize: 16 }
    GridLayout {
        columns: 2
        Layout.fillWidth: true
        Repeater {
            model: ["GREEN", "IMEMORY", "BOOST", "PROGRAM"]
            PanelButton {
                text: Ui.mode(modelData)
                checkable: true
                checked: root.selectedMode === modelData
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.preferredHeight: 56
                font.pixelSize: 15
                onClicked: root.selectedMode = modelData
            }
        }
    }
    Connections {
        target: backend
        function onDeviceSettingsReceived(kind, room, values) {
            if (!root.opened || kind !== "boiler") return
            temperature.value = values.target
            current.text = "Aktualnie: " + Ui.temperature(values.current)
            root.selectedMode = values.mode
            root.loaded = true
        }
        function onDeviceSettingsFailed(kind, room, message) {
            if (root.opened && kind === "boiler") root.finish(false, message)
        }
        function onBoilerSettingsFinished(success, message) { root.finish(success, message) }
    }
}
