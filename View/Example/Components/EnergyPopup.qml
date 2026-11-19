import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Popup {
    id: root
    objectName: "energyPopup"
    property var energy: null
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(1000, parent.width - 24)
    height: Math.min(760, parent.height - 24)
    padding: 18
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape
    background: Rectangle { color: "#202b36"; radius: 22; border.color: "#405160" }
    Overlay.modal: Rectangle { color: "#b3000000" }
    onOpened: if (energy) energy.opened()
    contentItem: ColumnLayout {
        spacing: 10
        RowLayout {
            Layout.fillWidth: true
            Label { text: "Zużycie prądu"; font.pixelSize: 26; font.bold: true; Layout.fillWidth: true }
            PanelButton {
                objectName: "refreshEnergy"
                text: root.energy && root.energy.busy ? "Pobieranie…" : "Odśwież"
                enabled: root.energy && !root.energy.busy
                onClicked: root.energy.refresh()
            }
            PanelButton { objectName: "closeEnergy"; text: "×"; font.pixelSize: 26; onClicked: root.close(); Accessible.name: "Zamknij statystyki prądu" }
        }
        Label {
            text: "Pobór z sieci · kWh · aktualizacja codziennie około 12:00 (Polska)"
            color: "#a9b8c6"; font.pixelSize: 14; wrapMode: Text.WordWrap; Layout.fillWidth: true
        }
        TabBar {
            id: energyTabs
            implicitWidth: 360
            clip: true
            Layout.fillWidth: true
            onCurrentIndexChanged: if (root.energy) root.energy.setMode(["hour", "day", "month"][currentIndex])
            TabButton { width: energyTabs.width / 3; objectName: "energyHours"; text: "Godziny"; implicitHeight: 48 }
            TabButton { width: energyTabs.width / 3; objectName: "energyDays"; text: "Dni"; implicitHeight: 48 }
            TabButton { width: energyTabs.width / 3; objectName: "energyMonths"; text: "Miesiące"; implicitHeight: 48 }
        }
        RowLayout {
            Layout.fillWidth: true
            PanelButton { text: "‹"; font.pixelSize: 24; enabled: root.energy && root.energy.canPrevious; onClicked: root.energy.move(-1); Accessible.name: "Poprzedni okres" }
            Label { text: root.energy ? root.energy.period : ""; font.pixelSize: 22; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true }
            PanelButton { text: "›"; font.pixelSize: 24; enabled: root.energy && root.energy.canNext; onClicked: root.energy.move(1); Accessible.name: "Następny okres" }
        }
        Label { text: root.energy ? root.energy.total : "Brak danych"; color: "#82d5ba"; font.pixelSize: 24; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        ListView {
            id: readings
            objectName: "energyReadings"
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 50
            clip: true
            spacing: 6
            model: root.energy ? root.energy.rows : []
            ScrollBar.vertical: ScrollBar {}
            delegate: Rectangle {
                required property var modelData
                width: readings.width
                height: 48
                color: "#18232d"
                radius: 8
                Rectangle {
                    height: parent.height
                    width: modelData.value === null ? 0 : parent.width * 0.65 * modelData.value / root.energy.maximum
                    color: "#2d594e"
                    radius: 8
                }
                RowLayout {
                    anchors.fill: parent; anchors.margins: 10
                    Label { text: modelData.label; font.pixelSize: 16; Layout.fillWidth: true }
                    Label {
                        text: modelData.value === null ? "Brak danych" : Number(modelData.value).toLocaleString(Qt.locale("pl_PL"), 'f', 3) + " kWh" + (modelData.complete ? "" : " *")
                        font.pixelSize: 16; color: modelData.complete ? "#eef5fa" : "#f3c78a"
                    }
                }
            }
        }
        Label {
            text: "Ostatnie pobranie: " + (root.energy ? root.energy.updated : "—") + " · Dane do wczoraj. * Niepełny okres."
            color: "#a9b8c6"; font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true
        }
        Label {
            text: root.energy ? root.energy.message : ""
            visible: text.length > 0; color: "#f3c78a"; font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true
        }
    }
}
