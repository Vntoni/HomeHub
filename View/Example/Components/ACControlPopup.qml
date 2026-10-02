import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "Ui.js" as Ui

SettingsPopup {
    id: root
    objectName: "acPopup"
    property string room: ""
    property string selectedMode: ""
    property string loadedMode: ""
    readonly property bool deviceOn: ["COOL", "HEAT", "FAN", "DRY", "AUTO"].indexOf(loadedMode) >= 0
    property string selectedFanSpeed: ""
    property string currentFanSpeed: ""
    property bool fanSpeedEdited: false
    heading: room + " · Klimatyzacja"
    subtitle: "Temperatura, tryb pracy i nawiew"
    canApply: loaded && deviceOn && (selectedMode === "OFF" || selectedMode === "FAN" || isFinite(temperature.value)) && selectedMode !== ""
    onOpened: { reset(); loadedMode = ""; backend.load_device_settings("ac", room) }
    onApplyRequested: backend.apply_ac_settings(room, temperature.value, selectedMode, economy.checked, powerful.checked, quiet.checked, fanSpeedEdited ? selectedFanSpeed : "")
    TemperatureStepper { id: temperature; Layout.fillWidth: true; enabled: root.selectedMode !== "OFF" && root.selectedMode !== "FAN" }
    Label {
        objectName: "acSettingsBlockedReason"
        visible: root.loaded && !root.deviceOn
        text: "Zapis jest zablokowany. Włącz klimatyzator przełącznikiem i odśwież odczyt."
        color: "#ffb4ab"
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }
    Label { text: "Tryb pracy"; color: "#a9b8c6"; font.pixelSize: 16 }
    GridLayout {
        columns: width >= 440 ? 3 : 2
        Layout.fillWidth: true
        Repeater {
            model: ["COOL", "HEAT", "FAN", "DRY", "AUTO", "OFF"]
            PanelButton {
                objectName: "acMode_" + modelData
                text: Ui.mode(modelData)
                checkable: true
                autoExclusive: true
                checked: root.selectedMode === modelData
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.preferredHeight: 50
                font.pixelSize: 16
                onClicked: root.selectedMode = modelData
            }
        }
    }
    Label { text: "Poziom nawiewu"; color: "#a9b8c6"; font.pixelSize: 16 }
    GridLayout {
        columns: width >= 500 ? 5 : (width >= 340 ? 3 : 2)
        Layout.fillWidth: true
        enabled: root.selectedMode !== "OFF"
        Repeater {
            model: ["QUIET", "LOW", "MEDIUM", "HIGH", "AUTO"]
            PanelButton {
                objectName: "fanSpeed_" + modelData
                text: Ui.fanSpeed(modelData)
                checkable: true
                autoExclusive: true
                checked: root.selectedFanSpeed === modelData
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.preferredHeight: 50
                onClicked: { root.selectedFanSpeed = modelData; root.fanSpeedEdited = true }
            }
        }
    }
    Label {
        objectName: "fanSpeedReadback"
        text: "Odczyt nawiewu: " + Ui.fanSpeed(root.currentFanSpeed)
        color: "#a9b8c6"
        font.pixelSize: 14
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
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
            root.loadedMode = values.mode
            root.selectedFanSpeed = values.fan_speed
            root.currentFanSpeed = values.fan_speed
            root.fanSpeedEdited = false
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
        function onAcFanSpeedReceived(room, speed) {
            if (root.opened && room === root.room) root.currentFanSpeed = speed
        }
        function onAcSettingsFinished(room, success, message) {
            if (room === root.room) root.finish(success, message)
        }
        function onModeReceived(room, mode) {
            if (root.opened && room === root.room) root.loadedMode = mode
        }
    }
}
