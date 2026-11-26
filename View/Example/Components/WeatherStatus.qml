import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    objectName: "weatherStatus"
    property var weather: null
    property string icon: weather ? weather.icon : "unknown"
    implicitWidth: 160
    implicitHeight: 64
    radius: 12
    color: "#202f3b"
    border.color: weather && weather.stale ? "#c9a567" : "#344755"
    Accessible.name: "Pogoda: " + (weather ? weather.temperature + ", " + weather.details : "brak danych")
    RowLayout {
        anchors.fill: parent
        anchors.margins: 7
        spacing: 6
        Canvas {
            id: pictogram
            Layout.preferredWidth: 44
            Layout.preferredHeight: 44
            onPaint: {
                var c = getContext("2d"); c.reset(); c.lineWidth = 2.5; c.lineCap = "round";
                function line(x1,y1,x2,y2,color) { c.strokeStyle=color; c.beginPath(); c.moveTo(x1,y1); c.lineTo(x2,y2); c.stroke(); }
                function circle(x,y,r,color) { c.fillStyle=color; c.beginPath(); c.arc(x,y,r,0,Math.PI*2); c.fill(); }
                var k = root.icon;
                if (k === "sun" || k === "partly") {
                    var x = k === "sun" ? 22 : 13, y = k === "sun" ? 22 : 13;
                    circle(x,y,8,"#ffd166");
                    for (var i=0;i<8;i++) { var a=i*Math.PI/4; line(x+11*Math.cos(a),y+11*Math.sin(a),x+15*Math.cos(a),y+15*Math.sin(a),"#ffd166"); }
                }
                if (k === "moon") { circle(22,22,14,"#e1e9fa"); circle(28,17,12,root.color); }
                if (["cloud","partly","rain","snow","storm","fog"].indexOf(k) >= 0) {
                    circle(13,24,8,"#c4d7e6"); circle(23,19,10,"#c4d7e6"); circle(33,25,7,"#c4d7e6");
                    c.fillStyle="#c4d7e6"; c.fillRect(13,24,20,8);
                }
                if (k === "rain") for (var j=0;j<3;j++) line(14+j*9,35,12+j*9,40,"#78c7f5");
                if (k === "snow") for (var j=0;j<3;j++) { var sx=12+j*11; line(sx-3,38,sx+3,38,"#e1f4ff"); line(sx,35,sx,41,"#e1f4ff"); }
                if (k === "storm") { line(24,30,19,37,"#ffd166"); line(19,37,25,37,"#ffd166"); line(25,37,20,43,"#ffd166"); }
                if (k === "fog") { line(9,36,35,36,"#a9b8c6"); line(13,41,31,41,"#a9b8c6"); }
                if (k === "unknown") { c.fillStyle="#a9b8c6"; c.font="28px sans-serif"; c.fillText("?",14,32); }
            }
            Connections { target: root; function onIconChanged() { pictogram.requestPaint() } }
        }
        ColumnLayout {
            spacing: 0
            Label { text: root.weather ? root.weather.temperature : "—°C"; font.pixelSize: 24; font.bold: true }
            Label { text: root.weather ? root.weather.status : "Brak danych"; font.pixelSize: 11; color: "#a9b8c6" }
        }
    }
    MouseArea { anchors.fill: parent; onClicked: info.open() }
    Popup {
        id: info
        y: root.height + 8
        width: 300
        padding: 16
        ColumnLayout {
            width: parent.width
            Label { text: "Pogoda na zewnątrz"; font.bold: true }
            Label { text: root.weather ? root.weather.details : "Brak danych"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            Label { text: "Aktualizacja co godzinę"; color: "#a9b8c6" }
            Label { text: "Dane: Open-Meteo · CC BY 4.0"; color: "#82d5ba"; font.pixelSize: 12
                MouseArea { anchors.fill: parent; onClicked: Qt.openUrlExternally("https://open-meteo.com/") }
            }
        }
    }
}
