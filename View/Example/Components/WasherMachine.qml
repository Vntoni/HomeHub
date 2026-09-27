import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    objectName: "washerStatus"
    property bool online: false
    property int remaining: -1
    property string lastSeen: ""
    implicitHeight: 76
    radius: 16
    color: "#202b36"
    border.color: "#334352"
    RowLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 16
        Image { source: "qrc:/icons128/laundry-machine_128.png"; Layout.preferredWidth: 36; Layout.preferredHeight: 36; fillMode: Image.PreserveAspectFit }
        Label { text: "Pralka"; color: "#eef5fa"; font.pixelSize: 19; font.bold: true }
        Item { Layout.fillWidth: true }
        Label {
            objectName: "washerStatusText"
            text: !root.online ? "Brak połączenia" : (root.remaining > 0 ? "Pozostało " + root.remaining + " min" : (root.remaining === 0 ? "Nieaktywna" : "Oczekiwanie na odczyt"))
            color: root.online && root.remaining > 0 ? "#82d5ba" : "#a9b8c6"
            font.pixelSize: 18
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignRight
            wrapMode: Text.WordWrap
        }
    }
    Connections {
        target: backend
        function onWasherOnlineChanged(value) { root.online = value; if (!value) root.remaining = -1 }
        function onWasherRemainingChanged(value) { root.remaining = value }
        function onWasherLastSeenChanged(value) { root.lastSeen = value }
    }
}
