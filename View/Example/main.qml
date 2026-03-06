import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15
import QtQuick.Controls.Material 2.15
import "Components"

ApplicationWindow {
    id: appWindow
    visible: true
    width: Screen.width
    height: Screen.height
    visibility: Window.FullScreen
    title: qsTr("Baza domowa")
    Material.theme: Material.Dark
    Material.accent: Material.Green
    color: Material.background
    property bool isReady: false



    Component.onCompleted: {
        console.log("APP WINDOW SIZE:", width, height)
    }



        ACControlPopup {
            id: acPopup
        }
        WaterHeaterControlPopup {
            id: waterHeaterPopup
        }
        HeaterControlPopup {
            id: heaterPopup
        }
        TemperatureMap {
            id: tempMapPopup
        }
        // Busy Indicator Overlay
        Rectangle {
            id: loadingOverlay
            anchors.fill: parent
            color: "#303030"
            visible: !appWindow.isReady
            z: 99

            Column {
                anchors.centerIn: parent
                spacing: 20

                // Twój niestandardowy BusyIndicator
                BusyIndicator {
                    id: control

                    contentItem: Item {
                        implicitWidth: 64
                        implicitHeight: 64

                        Item {
                            id: item
                            x: parent.width / 2 - 32
                            y: parent.height / 2 - 32
                            width: 64
                            height: 64
                            opacity: control.running ? 1 : 0

                            Behavior on opacity {
                                OpacityAnimator {
                                    duration: 250
                                }
                            }

                            RotationAnimator {
                                target: item
                                running: control.visible && control.running
                                from: 0
                                to: 360
                                loops: Animation.Infinite
                                duration: 1250
                            }

                            Repeater {
                                id: repeater
                                model: 6

                                Rectangle {
                                    id: delegate
                                    x: item.width / 2 - width / 2
                                    y: item.height / 2 - height / 2
                                    implicitWidth: 10
                                    implicitHeight: 10
                                    radius: 5
                                    color: "#21be2b"

                                    required property int index

                                    transform: [
                                        Translate {
                                            y: -Math.min(item.width, item.height) * 0.5 + 5
                                        },
                                        Rotation {
                                            angle: delegate.index / repeater.count * 360
                                            origin.x: 5
                                            origin.y: 5
                                        }
                                    ]
                                }
                            }
                        }
                    }

                    running: true
                }
            }
        }

        ColumnLayout {
            anchors.fill: parent

            // Pasek zakładek + przycisk wyjścia
            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 100

                TabBar {
                    id: tabBar
                    Layout.preferredHeight: 100
                    Layout.preferredWidth: 300

                    TabButton {
                        text: qsTr("Downstairs")
                        font.pixelSize: 20
                        onClicked: {
                            contentLoader.source = "Components/Accontrol.qml"
                        }
                    }
                    TabButton {
                        text: qsTr("Upstairs")
                        font.pixelSize: 20
                        onClicked: {
                            contentLoader.source = "Components/HeaterControl.qml"
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                // Przycisk mapy temperatury – widoczny tylko w zakładce Downstairs
                Button {
                    id: tempMapBtn
                    icon.source: "qrc:/icons64/temperature-control_32.png"
                    icon.width: 32
                    icon.height: 32
                    icon.color: "transparent"   // wyłącz monochromatyczne kolorowanie przez Qt
                    Layout.preferredWidth: 50
                    Layout.preferredHeight: 50
                    Layout.alignment: Qt.AlignVCenter
                    opacity: 0.9
                    Material.accent: Material.Green
                    visible: tabBar.currentIndex === 0   // tylko Downstairs

                    ToolTip.visible: hovered
                    ToolTip.text: "Mapa temperatury"

                    onClicked: tempMapPopup.open()
                    HoverHandler { onHoveredChanged: parent.opacity = hovered ? 1.0 : 0.7 }
                }

                // Przycisk wyjścia – dyskretny, w prawym górnym rogu
                Button {
                    text: "x"
                    font.pixelSize: 18
                    Layout.preferredWidth: 50
                    Layout.preferredHeight: 50
                    Layout.rightMargin: 10
                    Layout.alignment: Qt.AlignVCenter
                    opacity: 0.5
                    Material.accent: Material.Red

                    ToolTip.visible: hovered
                    ToolTip.text: "Zamknij aplikację"

                    onClicked: Qt.quit()

                    // Podświetl przy hover/press
                    HoverHandler { onHoveredChanged: parent.opacity = hovered ? 1.0 : 0.5 }
                }



            }



            Rectangle {
                Layout.fillHeight: true
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignHCenter
                color: Material.background
                anchors.margins: 10

                // Loader do dynamicznego ładowania widoków
                Loader {
                    id: contentLoader
                    anchors.fill: parent
                    anchors.margins: 10

                    onStatusChanged: {
                        console.log("Loader status changed:", status)
                        if (status === Loader.Error) {
                            console.error("Loader error:", contentLoader.sourceComponent)
                        }
                        if (status === Loader.Ready) {
                            console.log("Loader ready, item:", contentLoader.item)
                        }
                    }
                }
            }
        }


        Connections {
            target: backend

            function onReady(ready) {
                if (ready && !isReady) {
                    // Ustaw domyślny widok TYLKO przy pierwszym uruchomieniu
                    contentLoader.source = "Components/Accontrol.qml"
                }
                isReady = ready
            }
        }
}
