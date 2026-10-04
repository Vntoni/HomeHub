import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: root
    objectName: "microphoneStatus"
    property bool connected: false
    property string statusText: "ReSpeaker niepodłączony"
    implicitWidth: 52
    implicitHeight: 52
    Accessible.role: Accessible.Indicator
    Accessible.name: statusText
    Rectangle {
        anchors.fill: parent
        radius: 16
        color: root.connected ? "#173c37" : "#c1c9cf"
        border.color: root.connected ? "#318774" : "#909da6"
    }
    Image {
        objectName: "microphoneIcon"
        anchors.centerIn: parent
        width: 32
        height: 32
        sourceSize.width: 64
        sourceSize.height: 64
        source: root.connected ? "../Assets/microphone-connected.svg" : "../Assets/microphone-disconnected.svg"
        fillMode: Image.PreserveAspectFit
    }
    MouseArea {
        id: interaction
        anchors.fill: parent
        hoverEnabled: true
        onClicked: tip.open()
    }
    ToolTip {
        id: tip
        text: root.statusText
        visible: interaction.containsMouse
        timeout: 3500
    }
}
