import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Layouts 1.15

Popup {
    id: root
    default property alias fields: form.data
    property string heading: "Ustawienia"
    property string subtitle: ""
    property bool saving: false
    property bool loaded: false
    property bool failed: false
    property string message: ""
    property bool canApply: loaded
    property string operationKind: ""
    property string operationRoom: "boiler"
    property bool transportBusy: false
    signal applyRequested()
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(560, parent.width - 32)
    height: Math.min(implicitHeight, parent.height - 32)
    implicitHeight: layout.implicitHeight + topPadding + bottomPadding
    padding: 20
    modal: true
    focus: true
    closePolicy: saving ? Popup.NoAutoClose : Popup.CloseOnEscape
    Material.theme: Material.Dark
    Material.accent: "#82d5ba"
    Material.background: "#202b36"
    background: Rectangle { color: "#202b36"; radius: 22; border.color: "#405160" }
    Overlay.modal: Rectangle { color: "#b3000000" }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 140 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 100 } }
    contentItem: ColumnLayout {
        id: layout
        spacing: 12
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                Label { text: root.heading; font.pixelSize: 24; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                Label { text: root.subtitle; color: "#a9b8c6"; font.pixelSize: 15; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            }
            PanelButton {
                objectName: "closeSettings"
                text: "×"
                font.pixelSize: 28
                Layout.preferredWidth: 52
                Layout.preferredHeight: 52
                enabled: !root.saving
                Accessible.name: "Zamknij ustawienia"
                onClicked: root.close()
            }
        }
        ScrollView {
            id: scroller
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: form.implicitHeight
            Layout.minimumHeight: 80
            clip: true
            contentWidth: availableWidth
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ColumnLayout {
                id: form
                width: scroller.availableWidth
                spacing: 12
                enabled: root.loaded && !root.saving
            }
        }
        Label {
            objectName: "saveResult"
            text: root.saving ? "Zapisywanie ustawień…" : (root.message || (root.loaded ? "" : "Wczytywanie ustawień…"))
            visible: text.length > 0
            color: root.failed ? "#ffb4ab" : "#a9dcca"
            font.pixelSize: 15
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }
        PanelButton {
            objectName: "applySettings"
            text: root.saving ? "Zapisywanie…" : "Zastosuj"
            enabled: root.canApply && !root.saving && !root.transportBusy
            Layout.fillWidth: true
            Layout.preferredHeight: 56
            font.pixelSize: 18
            primary: true
            onClicked: { root.saving = true; root.message = ""; root.failed = false; root.applyRequested() }
        }
    }
    function reset() { loaded = false; failed = false; message = "" }
    function finish(success, text) { saving = false; failed = !success; message = text }
    Connections {
        target: backend
        function onDeviceOperationBusyChanged(kind, room, busy) {
            if (kind === root.operationKind && room === root.operationRoom) root.transportBusy = busy
        }
    }
}
