import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "Ui.js" as Ui

SettingsPopup {
    id: root
    objectName: "heaterPopup"
    property string room: ""
    operationKind: "heater"
    operationRoom: room
    property string selectedMode: ""
    property int durationMinutes: 120
    heading: room + " · Grzejnik"
    subtitle: "Ustawienia temperatury"
    canApply: loaded && isFinite(temperature.value) && (selectedMode === "manual" || selectedMode === "program")
    onOpened: { reset(); backend.load_device_settings("heater", room) }
    onApplyRequested: backend.apply_heater_settings(room, temperature.value, selectedMode, durationMinutes)
    TemperatureStepper { id: temperature; minimum: 7; maximum: 28; Layout.fillWidth: true }
    Label { id: current; color: "#a9b8c6"; font.pixelSize: 16 }
    Label { text: "Tryb pracy"; color: "#a9b8c6"; font.pixelSize: 16 }
    RowLayout {
        Layout.fillWidth: true
        Repeater {
            model: ["manual", "program"]
            PanelButton {
                text: Ui.mode(modelData)
                checkable: true
                checked: root.selectedMode === modelData
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.preferredHeight: 52
                onClicked: root.selectedMode = modelData
            }
        }
    }
    Label { text: "Czas nadpisania temperatury"; color: "#a9b8c6"; font.pixelSize: 16 }
    GridLayout {
        columns: 4
        Layout.fillWidth: true
        Repeater {
            model: [30, 60, 120, 240]
            PanelButton {
                text: modelData < 60 ? modelData + " min" : modelData / 60 + " godz."
                checkable: true
                checked: root.durationMinutes === modelData
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.preferredHeight: 52
                onClicked: root.durationMinutes = modelData
            }
        }
    }
    Label {
        text: "Ustawienie temperatury korzysta z czasowego nadpisania. Anulowanie nadpisania może przywrócić harmonogram."
        color: "#a9b8c6"
        font.pixelSize: 14
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }
    Connections {
        target: backend
        function onDeviceSettingsReceived(kind, room, values) {
            if (!root.opened || kind !== "heater" || room !== root.room) return
            temperature.value = values.target
            current.text = "Aktualnie: " + Ui.temperature(values.current)
            root.selectedMode = values.mode
            root.loaded = true
        }
        function onDeviceSettingsFailed(kind, room, message) {
            if (root.opened && kind === "heater" && room === root.room) root.finish(false, message)
        }
        function onHeaterSettingsFinished(room, success, message) {
            if (room === root.room) root.finish(success, message)
        }
    }
}
