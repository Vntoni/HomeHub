import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15
import QtQuick.Controls.Material 2.15
import "Components"

ApplicationWindow {
    id: appWindow
    visible: true
    width: demoMode ? 1200 : Screen.width
    height: demoMode ? 800 : Screen.height
    visibility: demoMode ? Window.Windowed : Window.FullScreen
    title: demoMode ? "HomeHub — DEMO (symulowane urządzenia)" : "HomeHub"
    Material.theme: Material.Dark
    Material.accent: "#82d5ba"
    Material.background: "#202b36"
    Material.foreground: "#eef5fa"
    color: "#141d26"
    property bool isReady: false
    property bool refreshing: false
    property int deviceRefreshIntervalMs: 900000

    ACControlPopup { id: acPopup }
    WaterHeaterControlPopup { id: waterHeaterPopup }
    HeaterControlPopup { id: heaterPopup }
    TemperatureMap { id: tempMapPopup }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: appWindow.width < 700 ? 16 : 28
        spacing: 16
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                spacing: 2
                Label { text: "Dom"; font.pixelSize: 30; font.bold: true }
                Label { text: demoMode ? "Tryb demo · symulowane urządzenia" : "Temperatura i urządzenia"; color: "#a9b8c6"; font.pixelSize: 14 }
            }
            Item { Layout.fillWidth: true }
            MicrophoneStatus {
                connected: backend ? backend.respeakerConnected : false
                statusText: backend ? backend.respeakerStatusText : "ReSpeaker niepodłączony"
                Layout.preferredWidth: 52
                Layout.preferredHeight: 52
            }
            PanelButton {
                objectName: "refreshDevices"
                text: appWindow.refreshing ? "Odświeżanie…" : "Odśwież"
                enabled: appWindow.isReady && !appWindow.refreshing
                Layout.preferredHeight: 52
                onClicked: { appWindow.refreshing = true; backend.refresh_connection() }
            }
            PanelButton {
                text: "×"
                font.pixelSize: 26
                Layout.preferredWidth: 52
                Layout.preferredHeight: 52
                Accessible.name: "Zamknij aplikację"
                onClicked: Qt.quit()
            }
        }
        RowLayout {
            Layout.fillWidth: true
            TabBar {
                id: tabBar
                Layout.fillWidth: true
                Layout.maximumWidth: 380
                TabButton { objectName: "downstairsTab"; text: "Parter"; font.pixelSize: 20; implicitHeight: 56 }
                TabButton { objectName: "upstairsTab"; text: "Piętro"; font.pixelSize: 20; implicitHeight: 56 }
            }
            Item { Layout.fillWidth: true }
            PanelButton {
                objectName: "openMap"
                text: "Mapa temperatury"
                Layout.preferredWidth: 190
                visible: tabBar.currentIndex === 0
                enabled: appWindow.isReady
                Layout.preferredHeight: 52
                onClicked: tempMapPopup.open()
            }
        }
        StackLayout {
            id: pages
            currentIndex: tabBar.currentIndex
            Layout.fillWidth: true
            Layout.fillHeight: true
            Accontrol {
                onAcSettingsRequested: function(room) { acPopup.room = room; acPopup.open() }
                onBoilerSettingsRequested: waterHeaterPopup.open()
            }
            HeaterControl {
                onSettingsRequested: function(room) { heaterPopup.room = room; heaterPopup.open() }
            }
        }
        WasherMachine { Layout.fillWidth: true }
    }
    Rectangle {
        anchors.fill: parent
        color: "#141d26"
        visible: !appWindow.isReady
        z: 99
        Column {
            anchors.centerIn: parent
            spacing: 16
            BusyIndicator { anchors.horizontalCenter: parent.horizontalCenter; running: parent.parent.visible }
            Label { text: "Wczytywanie urządzeń…"; font.pixelSize: 20 }
        }
    }
    Timer {
        objectName: "deviceRefreshTimer"
        interval: appWindow.deviceRefreshIntervalMs
        repeat: true
        running: appWindow.isReady && !appWindow.refreshing
        onTriggered: { appWindow.refreshing = true; backend.refresh_connection() }
    }
    Connections {
        target: backend
        function onReady(ready) {
            appWindow.isReady = ready
            appWindow.refreshing = false
            if (ready) backend.publish_dashboard()
        }
    }
}
