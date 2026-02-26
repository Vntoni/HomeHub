import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Window 2.15
import QtQuick.Controls.Material 2.15

ApplicationWindow {
    visible: true
    width: 1200
    height: 800
    title: "HeaterControl Test"

    Material.theme: Material.Dark

    Loader {
        id: testLoader
        anchors.fill: parent
        source: "HeaterControl.qml"

        onStatusChanged: {
            console.log("Test Loader status:", status)
            if (status === Loader.Error) {
                console.error("ERROR loading HeaterControl.qml")
            }
            if (status === Loader.Ready) {
                console.log("SUCCESS! HeaterControl.qml loaded")
            }
        }
    }

    Component.onCompleted: {
        console.log("Test window started")
    }
}
