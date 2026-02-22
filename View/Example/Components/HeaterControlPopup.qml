import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Layouts 1.15
import QtQuick.Effects

Popup {
    id: heaterPopup
    Material.theme: Material.Dark
    Material.accent: Material.BlueGrey

    property string room: ""  // "Juras", "Migacze", "Julia"
    property string currentMode: "program"
    property real initialTemperature: 20.0
    property real currentTemperature: 20.0
    property int durationMinutes: 120

    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    width: 400 * 1.5
    height: 520 * 1.5

    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0.0; to: 0.9 }
    }

    background: Rectangle {
        id: bg
        anchors.fill: parent
        color: Material.background
        radius: 14
        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowBlur: 0.8
            shadowOpacity: 0.5
            shadowHorizontalOffset: 5
            shadowVerticalOffset: 4
        }
    }

    onOpened: {
        heaterPopup.x = (parent.width - heaterPopup.width) / 2
        heaterPopup.y = (parent.height - heaterPopup.height) / 2

        // Pobierz aktualne dane
        backend.get_heater_target_temp(room)
        backend.get_heater_current_temp(room)
        backend.get_heater_mode(room)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 28

        // === NAGŁÓWEK ===
        Label {
            text: room
            font.pixelSize: 32
            font.bold: true
            color: Material.foreground
            horizontalAlignment: Text.AlignHCenter
            Layout.alignment: Qt.AlignHCenter
        }

        // === DIAL - Temperatura ===
        Item {
            Layout.preferredWidth: 200
            Layout.preferredHeight: 200
            Layout.alignment: Qt.AlignHCenter

            Dial {
                id: tempDial
                anchors.fill: parent
                from: 7
                to: 28
                stepSize: 0.5
                snapMode: Dial.SnapAlways
                value: initialTemperature

                // Tło okręgu
                background: Rectangle {
                    x: tempDial.width / 2 - width / 2
                    y: tempDial.height / 2 - height / 2
                    implicitWidth: 140
                    implicitHeight: 140
                    width: Math.max(64, Math.min(tempDial.width, tempDial.height))
                    height: width
                    color: "transparent"
                    radius: width / 2
                    border.color: tempDial.pressed ? "#FF9800" : "#FFA726"
                    border.width: 3
                    opacity: tempDial.enabled ? 1 : 0.3
                }

                // Obracający się uchwyt
                handle: Rectangle {
                    id: handleItem
                    x: tempDial.background.x + tempDial.background.width / 2 - width / 2
                    y: tempDial.background.y + tempDial.background.height / 2 - height / 2
                    width: 16
                    height: 16
                    color: tempDial.pressed ? "#FF9800" : "#FFA726"
                    radius: 8
                    antialiasing: true
                    opacity: tempDial.enabled ? 1 : 0.3

                    transform: [
                        Translate {
                            y: -Math.min(tempDial.background.width, tempDial.background.height) * 0.4 + handleItem.height / 2
                        },
                        Rotation {
                            angle: tempDial.angle
                            origin.x: handleItem.width / 2
                            origin.y: handleItem.height / 2
                        }
                    ]
                }

                // Tekst temperatury TARGET
                contentItem: Item {
                    anchors.centerIn: parent

                    Column {
                        anchors.centerIn: parent
                        spacing: 5

                        Text {
                            text: tempDial.value.toFixed(1) + "°C"
                            font.pixelSize: 32
                            font.bold: true
                            color: "#FF9800"
                            horizontalAlignment: Text.AlignHCenter
                            anchors.horizontalCenter: parent.horizontalCenter
                        }

                        Text {
                            text: "Target"
                            font.pixelSize: 14
                            color: "#BBB"
                            horizontalAlignment: Text.AlignHCenter
                            anchors.horizontalCenter: parent.horizontalCenter
                        }
                    }
                }
            }
        }

        // === Aktualna temperatura (tylko odczyt) ===
        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 10

            Label {
                text: "Current:"
                font.pixelSize: 18
                color: "#BBB"
            }

            Label {
                text: currentTemperature.toFixed(1) + "°C"
                font.pixelSize: 24
                font.bold: true
                color: "#17a81a"
            }
        }

        // === TRYB - Manual / Program ===
        ColumnLayout {
            spacing: 12
            Layout.alignment: Qt.AlignHCenter
            Layout.fillWidth: true

            Label {
                text: "Mode"
                font.pixelSize: 18
                color: "#BBB"
                horizontalAlignment: Text.AlignHCenter
                Layout.alignment: Qt.AlignHCenter
            }

            RowLayout {
                spacing: 12
                Layout.alignment: Qt.AlignHCenter
                Layout.fillWidth: true

                ButtonGroup { id: modeGroup }

                Button {
                    id: manualButton
                    text: "MANUAL"
                    font.pixelSize: 18
                    checkable: true
                    checked: currentMode === "manual"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 68
                    ButtonGroup.group: modeGroup

                    onClicked: currentMode = "manual"

                    Material.background: checked ? "#2196F3" : "#546e7a"
                    Material.foreground: "white"
                    Material.elevation: checked ? 3 : 1

                    contentItem: Text {
                        text: manualButton.text
                        color: "white"
                        font.pixelSize: 18
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                Button {
                    id: programButton
                    text: "PROGRAM"
                    font.pixelSize: 18
                    checkable: true
                    checked: currentMode === "program"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 68
                    ButtonGroup.group: modeGroup

                    onClicked: currentMode = "program"

                    Material.background: checked ? "#9C27B0" : "#546e7a"
                    Material.foreground: "white"
                    Material.elevation: checked ? 3 : 1

                    contentItem: Text {
                        text: programButton.text
                        color: "white"
                        font.pixelSize: 18
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }

        // === Duration (tylko dla trybu program) ===
        ColumnLayout {
            spacing: 8
            Layout.alignment: Qt.AlignHCenter
            Layout.fillWidth: true
            visible: currentMode === "program"

            Label {
                text: "Exception Duration"
                font.pixelSize: 16
                color: "#BBB"
                horizontalAlignment: Text.AlignHCenter
                Layout.alignment: Qt.AlignHCenter
            }

            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 15

                Button {
                    text: "30 min"
                    font.pixelSize: 14
                    onClicked: durationMinutes = 30
                    Material.background: durationMinutes === 30 ? "#FF9800" : "#424242"
                    Material.foreground: "white"
                }

                Button {
                    text: "1 h"
                    font.pixelSize: 14
                    onClicked: durationMinutes = 60
                    Material.background: durationMinutes === 60 ? "#FF9800" : "#424242"
                    Material.foreground: "white"
                }

                Button {
                    text: "2 h"
                    font.pixelSize: 14
                    onClicked: durationMinutes = 120
                    Material.background: durationMinutes === 120 ? "#FF9800" : "#424242"
                    Material.foreground: "white"
                }

                Button {
                    text: "4 h"
                    font.pixelSize: 14
                    onClicked: durationMinutes = 240
                    Material.background: durationMinutes === 240 ? "#FF9800" : "#424242"
                    Material.foreground: "white"
                }
            }

            Label {
                text: durationMinutes + " minutes"
                font.pixelSize: 14
                color: "#FFA726"
                horizontalAlignment: Text.AlignHCenter
                Layout.alignment: Qt.AlignHCenter
            }
        }

        Item { Layout.fillHeight: true }

        // === Przycisk SET ===
        Button {
            text: "SET TEMPERATURE"
            font.pixelSize: 18
            font.bold: true
            Layout.fillWidth: true
            Layout.preferredHeight: 68

            onClicked: {
                console.log("Setting heater:", room)
                console.log("  Temperature:", tempDial.value)
                console.log("  Mode:", currentMode)
                console.log("  Duration:", durationMinutes)

                // Ustaw tryb
                backend.set_heater_mode(room, currentMode)

                // Ustaw temperaturę z duration (dla trybu program używa exception mode)
                backend.set_heater_target_temp(room, tempDial.value, durationMinutes)

                heaterPopup.close()
            }

            Material.background: "#FF9800"
            Material.foreground: "#0f1217"
            Material.elevation: 4
        }
    }

    // === CONNECTIONS - odbieranie danych z backendu ===
    Connections {
        target: backend

        function onHeaterTargetTempChanged(r, temp) {
            if (r === room) {
                initialTemperature = temp
                tempDial.value = temp
            }
        }

        function onHeaterCurrentTempChanged(r, temp) {
            if (r === room) {
                currentTemperature = temp
            }
        }

        function onHeaterModeChanged(r, mode) {
            if (r === room) {
                currentMode = mode
                manualButton.checked = (mode === "manual")
                programButton.checked = (mode === "program")
            }
        }
    }
}
