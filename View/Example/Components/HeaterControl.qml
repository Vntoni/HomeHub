import QtQuick 6.8
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls.Basic 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Effects
import "."

Rectangle {
    // Właściwości dla temperatur i statusów
    property real currentTempJuras: NaN
    property real targetTempJuras: NaN
    property real currentTempMigacze: NaN
    property real targetTempMigacze: NaN
    property real currentTempJulia: NaN
    property real targetTempJulia: NaN

    property string modeJuras: "unknown"
    property string modeMigacze: "unknown"
    property string modeJulia: "unknown"

    property bool heaterJurasOnline: true
    property bool heaterMigaczeOnline: true
    property bool heaterJuliaOnline: true
    property bool heaterJurasisOn: true
    property bool heaterMigaczeisOn: true
    property bool heaterJuliaisOn: true

    Material.theme: Material.Dark
    Material.accent: Material.Pink
    color: "transparent"

    Component.onCompleted: {
        // Odśwież dane grzejników przy starcie
        backend.get_heater_current_temp("Juras")
        backend.get_heater_target_temp("Juras")
        backend.get_heater_mode("Juras")
        backend.get_heater_power("Juras")

        backend.get_heater_current_temp("Migacze")
        backend.get_heater_target_temp("Migacze")
        backend.get_heater_mode("Migacze")
        backend.get_heater_power("Migacze")

        backend.get_heater_current_temp("Julia")
        backend.get_heater_target_temp("Julia")
        backend.get_heater_mode("Julia")
        backend.get_heater_power("Julia")
    }

    // Połączenia z backendem - odbieranie sygnałów
    Connections {
        target: backend

        // Temperatura aktualna
        function onHeaterCurrentTempChanged(room, temp) {
            if (room === "Juras") currentTempJuras = temp
            else if (room === "Migacze") currentTempMigacze = temp
            else if (room === "Julia") currentTempJulia = temp
        }

        // Temperatura docelowa
        function onHeaterTargetTempChanged(room, temp) {
            if (room === "Juras") targetTempJuras = temp
            else if (room === "Migacze") targetTempMigacze = temp
            else if (room === "Julia") targetTempJulia = temp
        }

        // Tryb pracy
        function onHeaterModeChanged(room, mode) {
            if (room === "Juras") modeJuras = mode
            else if (room === "Migacze") modeMigacze = mode
            else if (room === "Julia") modeJulia = mode
        }

        // Status online
        function onHeaterOnlineChanged(room, online) {
            if (room === "Juras") heaterJurasOnline = online
            else if (room === "Migacze") heaterMigaczeOnline = online
            else if (room === "Julia") heaterJuliaOnline = online
        }

        //Status włączony/wyłączony
        function onHeaterPowerChanged(room, isOn) {
            if (room === "Juras") {
                heaterJurasisOn = isOn
                jurasControl.checked = isOn
            }
            else if (room === "Migacze"){
                heaterMigaczeisOn = isOn
                migaczeControl.checked = isOn
            }
            else if (room === "Julia"){
                heaterJuliaisOn = isOn
                juliaControl.checked = isOn
                console.log("Julia heater power changed:", isOn)
            }
        }
    }

    ColumnLayout {
        id: mainCol
        anchors.fill: parent
        spacing: 20

        RowLayout {
            spacing: 20
            Layout.alignment: Qt.AlignHCenter

            // ============================================
            // GRZEJNIK 1 - JURAS
            // ============================================
            Rectangle {
                id: jurasRect
                width: 300
                height: 400
                color: "#222"
                radius: 10
                border.color: heaterJurasOnline ? "white" : "#E53935"
                border.width: 1
                property string room: "Juras"

                layer.enabled: true
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowOpacity: 0.35
                    shadowBlur: 0.30
                    shadowHorizontalOffset: 7
                    shadowVerticalOffset: 4
                    saturation: 0.2
                }
                MultiPointTouchArea {
                anchors.fill: parent
                minimumTouchPoints: 1
                maximumTouchPoints: 1

                property double lastTapTime: 0
                property double doubleTapThreshold: 400 // ms

                onPressed: {
                    var currentTime = Date.now();
                    if (currentTime - lastTapTime < doubleTapThreshold && heaterJurasOnline === true) {
                        // Double tap detected
                        heaterPopup.room = "Juras"
                        heaterPopup.open()
                    }
                    lastTapTime = currentTime;
                }
            }

                // Nazwa pokoju - POZA ColumnLayout (jak w Downstairs!)
                Label {
                    text: "Juras"
                    color: Material.foreground
                    font.pixelSize: 30
                    anchors.top: parent.top
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.topMargin: 10
                }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.topMargin: 50
                    spacing: 10

                    Label {
                        text: "Room Temperature"
                        font.pixelSize: 21
                        color: "#BBB"
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Label {
                        text: heaterJurasOnline ?
                              (isNaN(currentTempJuras) ? "---" : currentTempJuras.toFixed(1) + "°C") :
                              "OFFLINE"
                        color: heaterJurasOnline ? "#17a81a" : Material.color(Material.Red)
                        font.pixelSize: 34
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Image {
                        source: "qrc:/icons128/heater_128_2.png"
                        width: 64
                        height: 64
                        fillMode: Image.PreserveAspectFit
                        Layout.alignment: Qt.AlignHCenter
                        layer.enabled: true
                        layer.effect: MultiEffect {
                            shadowEnabled: true
                            shadowOpacity: 0.25
                            shadowBlur: 0.60
                            shadowHorizontalOffset: 3
                            shadowVerticalOffset: 3
                            saturation: 0.1
                        }
                    }

                    Switch {
                        id: jurasControl
                        enabled: heaterJurasisOn
                        Layout.alignment: Qt.AlignHCenter
                        onToggled: {
                            jurasControl.checked ? backend.turn_on_heater("Juras") :
                                backend.turn_off_heater("Juras")
                        }
                        layer.enabled: true
                        layer.effect: MultiEffect {
                            shadowEnabled: true
                            shadowOpacity: 0.35
                            shadowBlur: 0.40
                            shadowHorizontalOffset: 4
                            shadowVerticalOffset: 3
                            saturation: 0.1
                        }

                        indicator: Rectangle {
                            implicitWidth: 48 * 1.5
                            implicitHeight: 26 * 1.5
                            x: jurasControl.leftPadding
                            y: parent.height / 2 - height / 2
                            radius: 13 * 1.5
                            color: jurasControl.checked ? "#FF9800" : "#ffffff"
                            border.color: jurasControl.checked ? "#FF9800" : "#cccccc"

                            Rectangle {
                                x: jurasControl.checked ? parent.width - width : 0
                                width: 26 * 1.5
                                height: 26 * 1.5
                                radius: 13 * 1.5
                                color: jurasControl.down ? "#cccccc" : "#ffffff"
                                border.color: jurasControl.checked ? (jurasControl.down ? "#FF9800" : "#FFA726") : "#999999"
                            }
                        }

                        contentItem: Text {
                            text: jurasControl.text
                            font: jurasControl.font
                            opacity: enabled ? 1.0 : 0.3
                            color: jurasControl.down ? "#FF9800" : "#FFA726"
                            verticalAlignment: Text.AlignVCenter
                            leftPadding: jurasControl.indicator.width + jurasControl.spacing
                        }
                    }
                }

                // Timer - odświeżanie co 10 sekund
                Timer {
                    interval: 10000
                    running: true
                    repeat: true
                    onTriggered: {
                        backend.get_heater_current_temp("Juras")
                        backend.get_heater_target_temp("Juras")
                        backend.get_heater_mode("Juras")
                        backend.get_heater_power("Juras")
                    }
                }
            }

            // ============================================
            // GRZEJNIK 2 - MIGACZE
            // ============================================
            Rectangle {
                id: migaczeRect
                width: 300
                height: 400
                color: "#222"
                radius: 10
                border.color: heaterMigaczeOnline ? "white" : "#E53935"
                border.width: 1
                property string room: "Migacze"

                layer.enabled: true
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowOpacity: 0.35
                    shadowBlur: 0.30
                    shadowHorizontalOffset: 7
                    shadowVerticalOffset: 4
                    saturation: 0.2
                }
                MultiPointTouchArea {
                anchors.fill: parent
                minimumTouchPoints: 1
                maximumTouchPoints: 1

                property double lastTapTime: 0
                property double doubleTapThreshold: 400 // ms

                onPressed: {
                    var currentTime = Date.now();
                    if (currentTime - lastTapTime < doubleTapThreshold && heaterMigaczeOnline === true) {
                        // Double tap detected
                        heaterPopup.room = "Migacze"
                        heaterPopup.open()
                    }
                    lastTapTime = currentTime;
                }
            }

                // Nazwa pokoju - POZA ColumnLayout
                Label {
                    text: "Migacze"
                    color: Material.foreground
                    font.pixelSize: 30
                    anchors.top: parent.top
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.topMargin: 10
                }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.topMargin: 50
                    spacing: 10

                    Label {
                        text: "Room Temperature"
                        font.pixelSize: 21
                        color: "#BBB"
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Label {
                        text: heaterMigaczeOnline ?
                              (isNaN(currentTempMigacze) ? "---" : currentTempMigacze.toFixed(1) + "°C") :
                              "OFFLINE"
                        color: heaterMigaczeOnline ? "#17a81a" : Material.color(Material.Red)
                        font.pixelSize: 34
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Image {
                        source: "qrc:/icons128/heater_128_2.png"
                        width: 64
                        height: 64
                        fillMode: Image.PreserveAspectFit
                        Layout.alignment: Qt.AlignHCenter
                        layer.enabled: true
                        layer.effect: MultiEffect {
                            shadowEnabled: true
                            shadowOpacity: 0.25
                            shadowBlur: 0.60
                            shadowHorizontalOffset: 3
                            shadowVerticalOffset: 3
                            saturation: 0.1
                        }
                    }

                    Switch {
                        id: migaczeControl
                        enabled: heaterMigaczeisOn
                        Layout.alignment: Qt.AlignHCenter
                        onToggled: {
                            migaczeControl.checked ? backend.turn_on_heater("Migacze") :
                                backend.turn_off_heater("Migacze")
                        }
                        layer.enabled: true
                        layer.effect: MultiEffect {
                            shadowEnabled: true
                            shadowOpacity: 0.35
                            shadowBlur: 0.40
                            shadowHorizontalOffset: 4
                            shadowVerticalOffset: 3
                            saturation: 0.1
                        }

                        indicator: Rectangle {
                            implicitWidth: 48 * 1.5
                            implicitHeight: 26 * 1.5
                            x: migaczeControl.leftPadding
                            y: parent.height / 2 - height / 2
                            radius: 13 * 1.5
                            color: migaczeControl.checked ? "#FF9800" : "#ffffff"
                            border.color: migaczeControl.checked ? "#FF9800" : "#cccccc"

                            Rectangle {
                                x: migaczeControl.checked ? parent.width - width : 0
                                width: 26 * 1.5
                                height: 26 * 1.5
                                radius: 13 * 1.5
                                color: migaczeControl.down ? "#cccccc" : "#ffffff"
                                border.color: migaczeControl.checked ? (migaczeControl.down ? "#FF9800" : "#FFA726") : "#999999"
                            }
                        }

                        contentItem: Text {
                            text: migaczeControl.text
                            font: migaczeControl.font
                            opacity: enabled ? 1.0 : 0.3
                            color: migaczeControl.down ? "#FF9800" : "#FFA726"
                            verticalAlignment: Text.AlignVCenter
                            leftPadding: migaczeControl.indicator.width + migaczeControl.spacing
                        }
                    }
                }

                // Timer
                Timer {
                    interval: 10000
                    running: true
                    repeat: true
                    onTriggered: {
                        backend.get_heater_current_temp("Migacze")
                        backend.get_heater_target_temp("Migacze")
                        backend.get_heater_mode("Migacze")
                        backend.get_heater_power("Migacze")
                    }
                }
            }

            // ============================================
            // GRZEJNIK 3 - JULIA
            // ============================================
            Rectangle {
                id: juliaRect
                width: 300
                height: 400
                color: "#222"
                radius: 10
                border.color: heaterJuliaOnline ? "white" : "#E53935"
                border.width: 1
                property string room: "Julia"

                layer.enabled: true
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowOpacity: 0.35
                    shadowBlur: 0.30
                    shadowHorizontalOffset: 7
                    shadowVerticalOffset: 4
                    saturation: 0.2
                }
                MultiPointTouchArea {
                anchors.fill: parent
                minimumTouchPoints: 1
                maximumTouchPoints: 1

                property double lastTapTime: 0
                property double doubleTapThreshold: 400 // ms

                onPressed: {
                    var currentTime = Date.now();
                    if (currentTime - lastTapTime < doubleTapThreshold && heaterJuliaOnline === true) {
                        // Double tap detected
                        heaterPopup.room = "Julia"
                        heaterPopup.open()
                    }
                    lastTapTime = currentTime;
                }
            }

                // Nazwa pokoju - POZA ColumnLayout
                Label {
                    text: "Julia"
                    color: Material.foreground
                    font.pixelSize: 30
                    anchors.top: parent.top
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.topMargin: 10
                }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.topMargin: 50
                    spacing: 10

                    Label {
                        text: "Room Temperature"
                        font.pixelSize: 21
                        color: "#BBB"
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Label {
                        text: heaterJuliaOnline ?
                              (isNaN(currentTempJulia) ? "---" : currentTempJulia.toFixed(1) + "°C") :
                              "OFFLINE"
                        color: heaterJuliaOnline ? "#17a81a" : Material.color(Material.Red)
                        font.pixelSize: 34
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Image {
                        source: "qrc:/icons128/heater_128_2.png"
                        width: 64
                        height: 64
                        fillMode: Image.PreserveAspectFit
                        Layout.alignment: Qt.AlignHCenter
                        layer.enabled: true
                        layer.effect: MultiEffect {
                            shadowEnabled: true
                            shadowOpacity: 0.25
                            shadowBlur: 0.60
                            shadowHorizontalOffset: 3
                            shadowVerticalOffset: 3
                            saturation: 0.1
                        }
                    }

                    Switch {
                        id: juliaControl
                        enabled: heaterJuliaisOn
                        Layout.alignment: Qt.AlignHCenter
                        onToggled: {
                            juliaControl.checked ? backend.turn_on_heater("Julia") :
                                backend.turn_off_heater("Julia")
                        }
                        layer.enabled: true
                        layer.effect: MultiEffect {
                            shadowEnabled: true
                            shadowOpacity: 0.35
                            shadowBlur: 0.40
                            shadowHorizontalOffset: 4
                            shadowVerticalOffset: 3
                            saturation: 0.1
                        }

                        indicator: Rectangle {
                            implicitWidth: 48 * 1.5
                            implicitHeight: 26 * 1.5
                            x: juliaControl.leftPadding
                            y: parent.height / 2 - height / 2
                            radius: 13 * 1.5
                            color: juliaControl.checked ? "#FF9800" : "#ffffff"
                            border.color: juliaControl.checked ? "#FF9800" : "#cccccc"

                            Rectangle {
                                x: juliaControl.checked ? parent.width - width : 0
                                width: 26 * 1.5
                                height: 26 * 1.5
                                radius: 13 * 1.5
                                color: juliaControl.down ? "#cccccc" : "#ffffff"
                                border.color: juliaControl.checked ? (juliaControl.down ? "#FF9800" : "#FFA726") : "#999999"
                            }
                        }

                        contentItem: Text {
                            text: juliaControl.text
                            font: juliaControl.font
                            opacity: enabled ? 1.0 : 0.3
                            color: juliaControl.down ? "#FF9800" : "#FFA726"
                            verticalAlignment: Text.AlignVCenter
                            leftPadding: juliaControl.indicator.width + juliaControl.spacing
                        }
                    }
                }

                // Timer
                Timer {
                    interval: 10000
                    running: true
                    repeat: true
                    onTriggered: {
                        backend.get_heater_current_temp("Julia")
                        backend.get_heater_target_temp("Julia")
                        backend.get_heater_mode("Julia")
                        backend.get_heater_power("Julia")
                    }
                }
            }
        }

        // Pusty element na dole - wyrównanie z Downstairs (pralka ma ~170px)
        Item {
            Layout.preferredHeight: 170
            Layout.alignment: Qt.AlignHCenter
        }
    }
}