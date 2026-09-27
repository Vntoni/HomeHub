import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Layouts 1.15
import "Ui.js" as Ui

Rectangle {
    id: root
    property string deviceName: ""
    property string deviceKind: ""
    property url iconSource
    property real currentTemperature: NaN
    property real targetTemperature: NaN
    property string mode: ""
    property bool online: false
    property bool powered: false
    property bool busy: false
    property string powerLabel: "Włączone"
    property string message: ""
    property bool failed: false
    signal settingsRequested()
    signal powerRequested(bool on)
    implicitHeight: body.implicitHeight + 32
    radius: 20
    color: "#202b36"
    border.color: "#334352"
    ColumnLayout {
        id: body
        anchors.fill: parent
        anchors.margins: 16
        spacing: 8
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Label { text: root.deviceName; font.pixelSize: 25; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                Label { text: root.deviceKind; color: "#a9b8c6"; font.pixelSize: 14 }
            }
            Image { source: root.iconSource; Layout.preferredWidth: 40; Layout.preferredHeight: 40; fillMode: Image.PreserveAspectFit }
        }
        Label { text: "Aktualnie"; color: "#a9b8c6"; font.pixelSize: 14 }
        Label {
            text: Ui.temperature(root.currentTemperature)
            color: root.online ? "#eef5fa" : "#a9b8c6"
            font.pixelSize: 42
            font.bold: true
        }
        Label { text: "Ustawiono " + Ui.temperature(root.targetTemperature); color: "#c9d6e2"; font.pixelSize: 18 }
        Label { text: "Tryb: " + Ui.mode(root.mode); color: "#a9b8c6"; font.pixelSize: 16; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: "#334352" }
        Switch {
            objectName: "devicePower"
            text: root.powerLabel
            checked: root.powered
            enabled: root.online && !root.busy
            Layout.fillWidth: true
            Layout.minimumHeight: 48
            font.pixelSize: 15
            onToggled: {
                root.powerRequested(checked)
                checked = Qt.binding(function() { return root.powered })
            }
        }
        Label {
            text: root.busy ? "Wysyłanie…" : (root.message || (root.online ? "Połączono" : "Brak połączenia"))
            color: root.failed ? "#ffb4ab" : "#a9b8c6"
            font.pixelSize: 13
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }
        PanelButton {
            objectName: "deviceSettings"
            text: "Ustawienia  ›"
            enabled: root.online && !root.busy
            Layout.fillWidth: true
            Layout.preferredHeight: 52
            font.pixelSize: 17
            onClicked: root.settingsRequested()
        }
    }
}
