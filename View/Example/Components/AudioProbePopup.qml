import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Popup {
    id: root
    objectName: "audioProbePopup"
    property var probe: null
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(600, parent.width - 32)
    height: Math.min(implicitHeight, parent.height - 24)
    implicitHeight: body.implicitHeight + heading.implicitHeight + 42
    padding: 16
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape
    background: Rectangle { color: "#202b36"; radius: 20; border.color: "#405160" }
    Overlay.modal: Rectangle { color: "#b3000000" }
    onOpened: {
        input.currentIndex = -1
        output.currentIndex = -1
        if (probe) probe.openPanel()
    }
    onAboutToHide: if (probe) probe.closePanel()
    Connections {
        target: root.probe
        function onDevicesChanged() { input.currentIndex = -1; output.currentIndex = -1 }
    }
    contentItem: ColumnLayout {
      spacing: 10
      RowLayout {
        id: heading
        Layout.fillWidth: true
        Label { text: "Test mikrofonu"; font.pixelSize: 24; font.bold: true; Layout.fillWidth: true }
        PanelButton { objectName: "closeAudioProbe"; text: "×"; Layout.preferredWidth: 48; onClicked: root.close() }
      }
      ScrollView {
        id: scroll
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.preferredHeight: body.implicitHeight
        clip: true
        contentWidth: availableWidth
        ColumnLayout {
            id: body
            width: scroll.availableWidth
            spacing: 10
            Label {
                text: "Nagraj do 5 sekund, potem odsłuchaj. Próbka pozostaje w pamięci i znika po zamknięciu panelu."
                wrapMode: Text.WordWrap; Layout.fillWidth: true; color: "#a9b8c6"
            }
            ComboBox {
                id: input
                objectName: "audioInputSelector"
                Layout.fillWidth: true
                model: root.probe ? root.probe.inputs : []
                textRole: "label"; valueRole: "id"
                currentIndex: -1
                onModelChanged: currentIndex = -1
                displayText: currentIndex < 0 ? "Wybierz mikrofon ReSpeaker" : currentText
                enabled: root.probe && !root.probe.busy
            }
            ProgressBar {
                objectName: "audioLevel"
                Layout.fillWidth: true
                from: 0; to: 1
                value: root.probe ? root.probe.level : 0
                Accessible.name: "Poziom sygnału mikrofonu"
            }
            RowLayout {
                Layout.fillWidth: true
                PanelButton {
                    objectName: "recordAudioProbe"
                    text: root.probe && root.probe.state === "recording" ? "Nagrywanie…" : "Nagraj 5 s"
                    Layout.fillWidth: true
                    enabled: root.probe && !root.probe.busy && input.currentIndex >= 0
                    onClicked: root.probe.record(input.currentValue)
                }
                PanelButton {
                    objectName: "stopAudioProbe"; text: "Stop"
                    Layout.preferredWidth: 100
                    enabled: root.probe && root.probe.busy
                    onClicked: root.probe.stop()
                }
            }
            ComboBox {
                id: output
                objectName: "audioOutputSelector"
                Layout.fillWidth: true
                model: root.probe ? root.probe.outputs : []
                textRole: "label"; valueRole: "id"
                currentIndex: -1
                onModelChanged: currentIndex = -1
                displayText: currentIndex < 0 ? "Wybierz głośnik / słuchawki ReSpeaker" : currentText
                enabled: root.probe && !root.probe.busy
            }
            RowLayout {
                Layout.fillWidth: true
                PanelButton {
                    objectName: "playAudioProbe"; text: "Odsłuchaj"
                    Layout.fillWidth: true
                    enabled: root.probe && !root.probe.busy && root.probe.hasRecording && output.currentIndex >= 0
                    onClicked: root.probe.play(output.currentValue)
                }
                PanelButton {
                    objectName: "clearAudioProbe"; text: "Usuń"
                    Layout.preferredWidth: 100
                    enabled: root.probe && !root.probe.busy && root.probe.hasRecording
                    onClicked: root.probe.clear()
                }
            }
            Label {
                objectName: "audioProbeMessage"
                text: root.probe ? root.probe.message : "Audio niedostępne"
                color: root.probe && root.probe.state === "error" ? "#ffb5ae" : "#b8e7d7"
                wrapMode: Text.WordWrap; Layout.fillWidth: true
            }
            PanelButton {
                text: "Odśwież urządzenia audio"
                Layout.fillWidth: true
                enabled: root.probe && !root.probe.busy
                onClicked: root.probe.refresh()
            }
        }
      }
    }
}
