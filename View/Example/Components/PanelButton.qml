import QtQuick 2.15
import QtQuick.Controls 2.15

Button {
    id: root
    property bool primary: false
    implicitWidth: Math.max(52, contentItem.implicitWidth + 28)
    implicitHeight: 52
    padding: 12
    topInset: 0
    bottomInset: 0
    leftInset: 0
    rightInset: 0
    font.pixelSize: 16
    background: Rectangle {
        radius: 12
        color: !root.enabled ? "#293540" : (root.primary || root.checked ? (root.down ? "#68bda2" : "#82d5ba") : (root.down ? "#425565" : "#30414f"))
        border.width: root.activeFocus ? 2 : 1
        border.color: root.activeFocus ? "#eef5fa" : (root.checked ? "#82d5ba" : "#405362")
    }
    contentItem: Text {
        text: root.text
        font: root.font
        color: !root.enabled ? "#8b9aa7" : (root.primary || root.checked ? "#112b23" : "#eef5fa")
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        wrapMode: Text.WordWrap
    }
}
