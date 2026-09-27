import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "Ui.js" as Ui

SettingsPopup {
    id: root
    objectName: "acPopup"
    property string room: ""
    property string selectedMode: ""
    heading: room + " · Klimatyzacja"
    subtitle: "Temperatura i tryb pracy"
    canApply: loaded && isFinite(temperature.value) && selectedMode !== ""
    onOpened: { reset(); backend.load_device_settings("ac", room) }
    onApplyRequested: backend.apply_ac_settings(room, temperature.value, selectedMode, economy.checked, powerful.checked, quiet.checked)
    TemperatureStepper { id: temperature; Layout.fillWidth: true }
    Label { text: "Tryb pracy"; color: "#a9b8c6"; font.pixelSize: 16 }
    GridLayout {
        columns: 2
        Layout.fillWidth: true
        Repeater {
            model: ["COOL", "HEAT", "FAN", "DRY", "AUTO", "OFF"]
            PanelButton {
                text: Ui.mode(modelData)
                checkable: true
                checked: root.selectedMode === modelData
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.preferredHeight: 50
                font.pixelSize: 16
                onClicked: root.selectedMode = modelData
            }
        }
    }
    CheckBox { id: economy; property bool available: false; text: "Tryb ekonomiczny"; Layout.fillWidth: true; enabled: available && !powerful.checked }
    CheckBox { id: powerful; property bool available: false; enabled: available; text: "Zwiększona moc"; Layout.fillWidth: true; onToggled: { if (checked) economy.checked = false } }
    CheckBox { id: quiet; property bool available: false; enabled: available; text: "Cicha jednostka zewnętrzna"; Layout.fillWidth: true }
    Connections {
        target: backend
        function onDeviceSettingsReceived(kind, room, values) {
            if (!root.opened || kind !== "ac" || room !== root.room) return
            temperature.value = values.target
            root.selectedMode = values.mode
            economy.available = values.economy !== null
            economy.checked = !!values.economy
            powerful.available = values.powerful !== null
            powerful.checked = !!values.powerful
            quiet.available = values.quiet !== null
            quiet.checked = !!values.quiet
            root.loaded = true
        }
        function onDeviceSettingsFailed(kind, room, message) {
            if (root.opened && kind === "ac" && room === root.room) root.finish(false, message)
        }
        function onAcSettingsFinished(room, success, message) {
            if (room === root.room) root.finish(success, message)
        }
    }
}
