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

    Material.theme: Material.Dark
    Material.accent: Material.Pink
    color: "transparent"

    Component.onCompleted: {
        // Odśwież dane grzejników przy starcie
        backend.get_heater_current_temp("Juras")
        backend.get_heater_target_temp("Juras")
        backend.get_heater_mode("Juras")

        backend.get_heater_current_temp("Migacze")
        backend.get_heater_target_temp("Migacze")
        backend.get_heater_mode("Migacze")

        backend.get_heater_current_temp("Julia")
        backend.get_heater_target_temp("Julia")
        backend.get_heater_mode("Julia")
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
                width: 280
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

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 15
                    spacing: 10

                    // Nazwa pokoju
                    Label {
                        text: "Juras"
                        color: Material.foreground
                        font.pixelSize: 28
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    // Temperatura pomieszczenia (aktualna)
                    Label {
                        text: "Room Temperature"
                        font.pixelSize: 16
                        color: "#BBB"
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Label {
                        text: heaterJurasOnline ?
                              (isNaN(currentTempJuras) ? "---" : currentTempJuras.toFixed(1) + "°C") :
                              "OFFLINE"
                        color: heaterJurasOnline ? "#FF9800" : Material.color(Material.Red)
                        font.pixelSize: 32
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    // Separator
                    Rectangle {
                        Layout.preferredHeight: 1
                        Layout.fillWidth: true
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        color: "#444"
                    }

                    // Temperatura ustawiona (docelowa)
                    Label {
                        text: "Target Temperature"
                        font.pixelSize: 16
                        color: "#BBB"
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Label {
                        text: isNaN(targetTempJuras) ? "---" : targetTempJuras.toFixed(1) + "°C"
                        color: "#17a81a"
                        font.pixelSize: 28
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    // Separator
                    Rectangle {
                        Layout.preferredHeight: 1
                        Layout.fillWidth: true
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        color: "#444"
                    }

                    // Tryb pracy
                    Label {
                        text: "Mode"
                        font.pixelSize: 16
                        color: "#BBB"
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Label {
                        text: modeJuras === "manual" ? "Manual" :
                              modeJuras === "program" ? "Program" :
                              "Unknown"
                        color: modeJuras === "manual" ? "#2196F3" : "#9C27B0"
                        font.pixelSize: 20
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Item { Layout.fillHeight: true }
                }

                // Timer - odświeżanie co 10 sekund
                Timer {
                    interval: 10000
                    running: true
                    repeat: true
                    onTriggered: {
                        backend.get_heater_current_temp("Juras")
                        backend.get_heater_target_temp("Juras")
                    }
                }
            }

            // ============================================
            // GRZEJNIK 2 - MIGACZE
            // ============================================
            Rectangle {
                id: migaczeRect
                width: 280
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

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 15
                    spacing: 10

                    // Nazwa pokoju
                    Label {
                        text: "Migacze"
                        color: Material.foreground
                        font.pixelSize: 28
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    // Temperatura pomieszczenia
                    Label {
                        text: "Room Temperature"
                        font.pixelSize: 16
                        color: "#BBB"
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Label {
                        text: heaterMigaczeOnline ?
                              (isNaN(currentTempMigacze) ? "---" : currentTempMigacze.toFixed(1) + "°C") :
                              "OFFLINE"
                        color: heaterMigaczeOnline ? "#FF9800" : Material.color(Material.Red)
                        font.pixelSize: 32
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    // Separator
                    Rectangle {
                        Layout.preferredHeight: 1
                        Layout.fillWidth: true
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        color: "#444"
                    }

                    // Temperatura ustawiona
                    Label {
                        text: "Target Temperature"
                        font.pixelSize: 16
                        color: "#BBB"
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Label {
                        text: isNaN(targetTempMigacze) ? "---" : targetTempMigacze.toFixed(1) + "°C"
                        color: "#17a81a"
                        font.pixelSize: 28
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    // Separator
                    Rectangle {
                        Layout.preferredHeight: 1
                        Layout.fillWidth: true
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        color: "#444"
                    }

                    // Tryb pracy
                    Label {
                        text: "Mode"
                        font.pixelSize: 16
                        color: "#BBB"
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Label {
                        text: modeMigacze === "manual" ? "Manual" :
                              modeMigacze === "program" ? "Program" :
                              "Unknown"
                        color: modeMigacze === "manual" ? "#2196F3" : "#9C27B0"
                        font.pixelSize: 20
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Item { Layout.fillHeight: true }
                }

                // Timer
                Timer {
                    interval: 10000
                    running: true
                    repeat: true
                    onTriggered: {
                        backend.get_heater_current_temp("Migacze")
                        backend.get_heater_target_temp("Migacze")
                    }
                }
            }

            // ============================================
            // GRZEJNIK 3 - JULIA
            // ============================================
            Rectangle {
                id: juliaRect
                width: 280
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

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 15
                    spacing: 10

                    // Nazwa pokoju
                    Label {
                        text: "Julia"
                        color: Material.foreground
                        font.pixelSize: 28
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    // Temperatura pomieszczenia
                    Label {
                        text: "Room Temperature"
                        font.pixelSize: 16
                        color: "#BBB"
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Label {
                        text: heaterJuliaOnline ?
                              (isNaN(currentTempJulia) ? "---" : currentTempJulia.toFixed(1) + "°C") :
                              "OFFLINE"
                        color: heaterJuliaOnline ? "#FF9800" : Material.color(Material.Red)
                        font.pixelSize: 32
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    // Separator
                    Rectangle {
                        Layout.preferredHeight: 1
                        Layout.fillWidth: true
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        color: "#444"
                    }

                    // Temperatura ustawiona
                    Label {
                        text: "Target Temperature"
                        font.pixelSize: 16
                        color: "#BBB"
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Label {
                        text: isNaN(targetTempJulia) ? "---" : targetTempJulia.toFixed(1) + "°C"
                        color: "#17a81a"
                        font.pixelSize: 28
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    // Separator
                    Rectangle {
                        Layout.preferredHeight: 1
                        Layout.fillWidth: true
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        color: "#444"
                    }

                    // Tryb pracy
                    Label {
                        text: "Mode"
                        font.pixelSize: 16
                        color: "#BBB"
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Label {
                        text: modeJulia === "manual" ? "Manual" :
                              modeJulia === "program" ? "Program" :
                              "Unknown"
                        color: modeJulia === "manual" ? "#2196F3" : "#9C27B0"
                        font.pixelSize: 20
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Item { Layout.fillHeight: true }
                }

                // Timer
                Timer {
                    interval: 10000
                    running: true
                    repeat: true
                    onTriggered: {
                        backend.get_heater_current_temp("Julia")
                        backend.get_heater_target_temp("Julia")
                    }
                }
            }
        }
    }
}
