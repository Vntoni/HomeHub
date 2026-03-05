import QtQuick 6.8
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls.Basic 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Effects
import "."

Rectangle {
    property real currentTempSalon: NaN
    property real currentTempJadalnia: NaN
    property real currentTempBoiler: NaN
    property bool acSalonPower: false
    property bool acJadalniaPower: false
    property bool waterHeaterPower: false

    Material.theme: Material.Dark
    Material.accent: Material.Pink
    color: "transparent"



    Component.onCompleted: {
        backend.refresh_connection()
        Qt.callLater(function (){
        backend.get_water_heater_power()
        backend.get_mode_operation(salonRect.room)
        backend.get_mode_operation(jadalniaRect.room)
        backend.get_temp_indoor(salonRect.room)
        backend.get_temp_indoor(jadalniaRect.room)
        backend.get_water_temp()})
    }
    ColumnLayout {
        id: mainCol
        anchors.fill: parent
        spacing: 20

    RowLayout {

        spacing: 20
        Layout.alignment: Qt.AlignHCenter

        Rectangle {
            id: salonRect
            width: 300
            height: 400
            color: "#222"
            radius: 10
            border.color: salonRect.online ? "white": "#E53935"
            border.width: 1
            property string room: "Salon"
            property bool online: true
            layer.enabled: true
            layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowOpacity: 0.35     // 0.28–0.40
                    shadowBlur: 0.30
                    shadowHorizontalOffset: 7
                    shadowVerticalOffset: 4
                    saturation: 0.2


                    }

            signal clicked(string room)


            // Etykieta opisująca temperaturę
            Label {
                text: qsTr("Living Room")
                color: Material.foreground
                font.pixelSize: 30
                anchors.top: parent.top
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.topMargin: 10
                layer.enabled: true

                }

            // Wartość temperatury


            MultiPointTouchArea {
                anchors.fill: parent
                minimumTouchPoints: 1
                maximumTouchPoints: 1

                property double lastTapTime: 0
                property double doubleTapThreshold: 400 // ms

                onPressed: {
                    var currentTime = Date.now();
                    if (currentTime - lastTapTime < doubleTapThreshold && salonRect.online === true) {
                        // Double tap detected
                        acPopup.room = "Salon"
                        acPopup.open();
                    }
                    lastTapTime = currentTime;
                }
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
                    text: salonRect.online ? currentTempSalon.toFixed(1) + "°C" : "OFFLINE"
                    color: salonRect.online ? "#17a81a"  :  Material.color(Material.Red)  // zielony, żeby odróżnić
                    font.pixelSize: 34
                    anchors.top: parent.top
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.topMargin: 34
                }
                Image {
                source: "qrc:/icons128/air-conditioner_128.png"
                width: 128; height: 128
                fillMode: Image.PreserveAspectFit
                cache: Image.Always
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.topMargin: 44
                layer.enabled: true
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowOpacity: 0.25     // 0.28–0.40
                    shadowBlur: 0.60
                    shadowHorizontalOffset: 3
                    shadowVerticalOffset: 3
                    saturation: 0.1


                    }
        }

                Switch {
                    id: saloncontrol
                    enabled: salonRect.online
                    anchors.horizontalCenter: parent.horizontalCenter
                    onToggled: {
                        saloncontrol.checked ? backend.turn_on_ac('Salon') :
                            backend.turn_off_ac('Salon')
                    }
                    layer.enabled: true
                    layer.effect: MultiEffect {
                        shadowEnabled: true
                        shadowOpacity: 0.35     // 0.28–0.40
                        shadowBlur: 0.40
                        shadowHorizontalOffset: 4
                        shadowVerticalOffset: 3
                        saturation: 0.1


                    }

                    indicator: Rectangle {
                        implicitWidth: 48 *1.5
                        implicitHeight: 26 *1.5
                        x: saloncontrol.leftPadding
                        y: parent.height / 2 - height / 2
                        radius: 13 *1.5
                        color: saloncontrol.checked ? "#17a81a" : "#ffffff"
                        border.color: saloncontrol.checked ? "#17a81a" : "#cccccc"

                        Rectangle {
                            x: saloncontrol.checked ? parent.width - width : 0
                            width: 26 *1.5
                            height: 26 *1.5
                            radius: 13 *1.5
                            color: saloncontrol.down ? "#cccccc" : "#ffffff"
                            border.color: saloncontrol.checked ? (saloncontrol.down ? "#17a81a" : "#21be2b") : "#999999"
                        }
                    }

                    contentItem: Text {
                        text: saloncontrol.text
                        font: saloncontrol.font
                        opacity: enabled ? 1.0 : 0.3
                        color: saloncontrol.down ? "#17a81a" : "#21be2b"
                        verticalAlignment: Text.AlignVCenter
                        leftPadding: saloncontrol.indicator.width + saloncontrol.spacing
                    }
                }
            }
            Timer {
                id: tempTimerSalon
                interval: 5000; running: true; repeat: true
                onTriggered: backend.get_temp_indoor(salonRect.room)
            }
        }

        Rectangle {
            id: jadalniaRect
            width: 300
            height: 400
            color: "#222"
            radius: 10
            border.color: jadalniaRect.online ? "white": "#E53935"
            border.width: 1
            property string room: "Jadalnia"
            property bool online: true
            layer.enabled: true
            layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowOpacity: 0.35     // 0.28–0.40
                    shadowBlur: 0.30
                    shadowHorizontalOffset: 7
                    shadowVerticalOffset: 4
                    saturation: 0.2


                    }
            signal clicked(string room)


            // Etykieta opisująca temperaturę
            Label {
                text: qsTr("Dining Room")
                color: "white"
                font.pixelSize: 30
                anchors.top: parent.top
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.topMargin: 10
            }
            // Wartość temperatury


            MultiPointTouchArea {
                anchors.fill: parent
                minimumTouchPoints: 1
                maximumTouchPoints: 1

                property double lastTapTime: 0
                property double doubleTapThreshold: 400 // ms

                onPressed: {
                    var currentTime = Date.now();
                    if (currentTime - lastTapTime < doubleTapThreshold && jadalniaRect.online === true){
                        // Double tap detected
                        acPopup.room = "Jadalnia"
                        acPopup.open();
                    }
                    lastTapTime = currentTime;
                }
            }
            ColumnLayout {
                anchors.fill: parent
                anchors.topMargin: 50
                spacing: 12

                Label {
                    text: "Room Temperature"
                    font.pixelSize: 21
                    color: "#BBB"
                    horizontalAlignment: Text.AlignHCenter
                    Layout.alignment: Qt.AlignHCenter
                }
                Label {
                text: jadalniaRect.online ? currentTempJadalnia.toFixed(1) + "°C" : "OFFLINE"
                color: jadalniaRect.online ? "#17a81a"  :  Material.color(Material.Red)
                font.pixelSize: 34
                anchors.top: parent.top
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.topMargin: 34
            }

                Image {
                    source: "qrc:/icons128/air-conditioner_128.png"
                    width: 128; height: 128
                    fillMode: Image.PreserveAspectFit
                    cache: Image.Always
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.topMargin: 44
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
                    id: jadalniacontrol
                    enabled: jadalniaRect.online
                    anchors.horizontalCenter: parent.horizontalCenter
                    onToggled: {
                        jadalniacontrol.checked ? backend.turn_on_ac('Jadalnia') :
                            backend.turn_off_ac('Jadalnia')
                    }
                    layer.enabled: true
                    layer.effect: MultiEffect {
                        shadowEnabled: true
                        shadowOpacity: 0.35     // 0.28–0.40
                        shadowBlur: 0.40
                        shadowHorizontalOffset: 4
                        shadowVerticalOffset: 3
                        saturation: 0.1


                    }

                    indicator: Rectangle {
                        implicitWidth: 48 *1.5
                        implicitHeight: 26 *1.5
                        x: jadalniacontrol.leftPadding
                        y: parent.height / 2 - height / 2
                        radius: 13 *1.5
                        color: jadalniacontrol.checked ? "#17a81a" : "#ffffff"
                        border.color: jadalniacontrol.checked ? "#17a81a" : "#cccccc"

                        Rectangle {
                            x: jadalniacontrol.checked ? parent.width - width : 0
                            width: 26 *1.5
                            height: 26 *1.5
                            radius: 13 *1.5
                            color: jadalniacontrol.down ? "#cccccc" : "#ffffff"
                            border.color: jadalniacontrol.checked ? (jadalniacontrol.down ? "#17a81a" : "#21be2b") : "#999999"
                        }
                    }

                    contentItem: Text {
                        text: jadalniacontrol.text
                        font: jadalniacontrol.font
                        opacity: enabled ? 1.0 : 0.3
                        color: jadalniacontrol.down ? "#17a81a" : "#21be2b"
                        verticalAlignment: Text.AlignVCenter
                        leftPadding: jadalniacontrol.indicator.width + jadalniacontrol.spacing
                    }
                }
            }
            Timer {
                id: tempTimerJadalnia
                interval: 5000; running: true; repeat: true
                onTriggered: backend.get_temp_indoor(jadalniaRect.room)
            }


        }

        Rectangle {
            id: boilerRect
            width: 300
            height: 400
            color: "#222"
            radius: 10
            border.color: boilerRect.online ? "white": "#E53935"
            border.width: 1
            property string room: "Boiler"
            property bool online: true
            layer.enabled: true
            layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowOpacity: 0.35     // 0.28–0.40
                    shadowBlur: 0.30
                    shadowHorizontalOffset: 7
                    shadowVerticalOffset: 4
                    saturation: 0.2


                    }
            signal clicked(string room)


            // Etykieta opisująca temperaturę
            Label {
                text: qsTr("Water Heater")
                color: "white"
                font.pixelSize: 31
                anchors.top: parent.top
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.topMargin: 10
            }
            // Wartość temperatury


            MultiPointTouchArea {
                anchors.fill: parent
                minimumTouchPoints: 1
                maximumTouchPoints: 1

                property double lastTapTime: 0
                property double doubleTapThreshold: 400 // ms

                onPressed: {
                    var currentTime = Date.now();
                    if (currentTime - lastTapTime < doubleTapThreshold && boilerRect.online === true) {
                        // Double tap detected
                        waterHeaterPopup.open();
                    }
                    lastTapTime = currentTime;
                }
            }
            ColumnLayout {
                anchors.fill: parent
                anchors.topMargin: 50
                spacing: 10

                Label {
                    text: "Water Temperature"
                    font.pixelSize: 21
                    color: "#BBB"
                    horizontalAlignment: Text.AlignHCenter
                    Layout.alignment: Qt.AlignHCenter
                }

                Label {
                text: boilerRect.online ? currentTempBoiler.toFixed(1) + "°C" : "OFFLINE"
                color: boilerRect.online ? "#17a81a"   :  Material.color(Material.Red)
                font.pixelSize: 34
                anchors.top: parent.top
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.topMargin: 34
            }
                Image {
                    source: "qrc:/icons128/boiler_128.png"
                    width: 64; height: 64
                    fillMode: Image.PreserveAspectFit
                    cache: Image.Always
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.topMargin: 44
                    layer.enabled: true
                    layer.effect: MultiEffect {
                        shadowEnabled: true
                        shadowOpacity: 0.25     // 0.28–0.40
                        shadowBlur: 0.60
                        shadowHorizontalOffset: 3
                        shadowVerticalOffset: 3
                        saturation: 0.1


                    }
                    }
                Switch {
                    id: boilerControl
                    enabled: boilerRect.online
                    anchors.horizontalCenter: parent.horizontalCenter
                    onToggled: {
                        boilerControl.checked ? backend.turn_on_ac('Boiler') :
                        backend.turn_off_ac('Boiler')
                            }
                    layer.enabled: true
                    layer.effect: MultiEffect {
                        shadowEnabled: true
                        shadowOpacity: 0.35     // 0.28–0.40
                        shadowBlur: 0.40
                        shadowHorizontalOffset: 4
                        shadowVerticalOffset: 3
                        saturation: 0.1


                    }

                    indicator: Rectangle {
                        implicitWidth: 48 *1.5
                        implicitHeight: 26 *1.5
                        x: boilerControl.leftPadding
                        y: parent.height / 2 - height / 2
                        radius: 13 *1.5
                        color: boilerControl.checked ? "#f57c00"  : "#ffffff"
                        border.color: boilerControl.checked ? "#f57c00"  : "#cccccc"

                        Rectangle {
                            x: boilerControl.checked ? parent.width - width : 0
                            width: 26 *1.5
                            height: 26 *1.5
                            radius: 13 *1.5
                            color: boilerControl.down ? "#cccccc" : "#ffffff"
                            border.color: boilerControl.checked ? (boilerControl.down ? "#f57c00"  : "#21be2b") : "#999999"
                        }
                    }

                    contentItem: Text {
                        text: boilerControl.text
                        font: boilerControl.font
                        opacity: enabled ? 1.0 : 0.3
                        color: boilerControl.down ? "#f57c00"  : "#21be2b"
                        verticalAlignment: Text.AlignVCenter
                        leftPadding: boilerControl.indicator.width + boilerControl.spacing
                    }
                }
            }
            Timer {
                id: tempTimerBoiler
                interval: 5000; running: true; repeat: true
                onTriggered: backend.get_water_temp()
            }
        }

    }
    // Pralka na dole - wycentrowana
    WasherMachine {
        id: washerBadge
        showWhenIdle: true
        Layout.alignment: Qt.AlignHCenter
        Layout.topMargin: 10
    }

    }  // Zamknięcie mainCol ColumnLayout

    Connections {
        target: backend

        function onTempIndoorChanged(roomName, temperature) {
            if (roomName === jadalniaRect.room) {
                currentTempJadalnia = temperature
            } else if (roomName === salonRect.room) {
                currentTempSalon = temperature
            }
        }

        function onWaterTemp(boiler, temperature) {
            currentTempBoiler = temperature
        }

        function onPowerStatus(power) {
            if (power === false) {
                boilerControl.checked = false;
            } else {
                boilerControl.checked = true;
            }
        }


    function onModeReceived(room, mode) {
        if (room === salonRect.room) {
            saloncontrol.checked = mode !== "OFF";
        } else if (room === jadalniaRect.room) {
            jadalniacontrol.checked = mode !== "OFF";
        }
    }

    function onAcSalonOnlineChanged(status) {
        salonRect.online = status;
    }
    function onAcJadalniaOnlineChanged(status) {
        jadalniaRect.online = status;
    }
    function onBoilerOnlineChanged(status) {
        boilerRect.online = status;
    }


}
}







