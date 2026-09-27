import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "Ui.js" as Ui

ColumnLayout {
    id: root
    property real value: NaN
    property real minimum: 10
    property real maximum: 30
    property real step: 0.5
    signal edited()
    spacing: 4
    Label { text: "Temperatura zadana"; color: "#a9b8c6"; font.pixelSize: 16 }
    RowLayout {
        spacing: 16
        Layout.fillWidth: true
        PanelButton {
            objectName: "temperatureMinus"
            text: "−"
            font.pixelSize: 32
            Layout.preferredWidth: 64
            Layout.preferredHeight: 64
            enabled: isFinite(root.value) && root.value > root.minimum
            Accessible.name: "Zmniejsz temperaturę"
            onClicked: { root.value = Math.max(root.minimum, Math.round((root.value - root.step) * 10) / 10); root.edited() }
        }
        Label {
            text: Ui.temperature(root.value)
            font.pixelSize: 40
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            Layout.fillWidth: true
            Accessible.name: "Temperatura zadana " + text
        }
        PanelButton {
            objectName: "temperaturePlus"
            text: "+"
            font.pixelSize: 32
            Layout.preferredWidth: 64
            Layout.preferredHeight: 64
            enabled: isFinite(root.value) && root.value < root.maximum
            Accessible.name: "Zwiększ temperaturę"
            onClicked: { root.value = Math.min(root.maximum, Math.round((root.value + root.step) * 10) / 10); root.edited() }
        }
    }
}
