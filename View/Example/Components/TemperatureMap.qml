import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Effects

// Popup z mapą temperatury – rzut parteru z lotu ptaka
Popup {
    id: tempMapPopup
    Material.theme: Material.Dark
    Material.accent: Material.Green

    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    width: 700
    height: 480

    // Dane temperatur – ustawiać z zewnątrz lub przez backend
    property real tempSalon:    NaN
    property real tempJadalnia: NaN
    property real tempPrzedpokoj: NaN
    property real tempWC:       NaN

    property real humSalon:    NaN
    property real humJadalnia: NaN

    enter: Transition { NumberAnimation { property: "opacity"; from: 0.0; to: 1.0; duration: 200 } }
    exit:  Transition { NumberAnimation { property: "opacity"; from: 1.0; to: 0.0; duration: 150 } }

    onOpened: {
        tempMapPopup.x = (parent.width  - tempMapPopup.width)  / 2
        tempMapPopup.y = (parent.height - tempMapPopup.height) / 2
    }

    background: Rectangle {
        anchors.fill: parent
        color: "#1e1e1e"
        radius: 14
        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowBlur: 0.8
            shadowOpacity: 0.6
            shadowHorizontalOffset: 5
            shadowVerticalOffset: 4
        }
    }

    // ── Pomocnicza funkcja: kolor pokoju wg temperatury ──────────────────
    // Zimno (< 18°C) → niebieskawa, komfort (20–22°C) → zielonkawa, ciepło (> 24°C) → czerwonawa
    function roomColor(temp) {
        if (isNaN(temp)) return "#2a2a2a"
        if (temp < 16)   return "#1a3a5c"   // zimno – ciemny niebieski
        if (temp < 18)   return "#1e4d6b"   // chłodno
        if (temp < 20)   return "#1a4a3a"   // lekko chłodno – niebieskozielony
        if (temp < 22)   return "#1a3d2a"   // komfort – ciemnozielony
        if (temp < 24)   return "#3d3a1a"   // lekko ciepło – oliwkowy
        if (temp < 26)   return "#4a2a1a"   // ciepło – brązowy
        return "#5c1a1a"                     // gorąco – ciemnoczerwony
    }

    function tempText(temp) {
        return isNaN(temp) ? "—" : temp.toFixed(1) + "°C"
    }

    function humText(hum) {
        return isNaN(hum) ? "" : hum.toFixed(0) + "%"
    }

    // ── Zawartość ────────────────────────────────────────────────────────
    Item {
        anchors.fill: parent
        anchors.margins: 16

        // Nagłówek
        Text {
            id: header
            text: "Map temperature"
            color: "#ffffff"
            font.pixelSize: 18
            font.bold: true
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
        }

        // ── Canvas – ściany ──────────────────────────────────────────────
        Canvas {
            id: floorCanvas
            anchors.top: header.bottom
            anchors.topMargin: 12
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: closeBtn.top
            anchors.bottomMargin: 12

            // Odśwież canvas gdy temperatury się zmienią
            onTempSalonChanged:      requestPaint()
            onTempJadalniaChanged:   requestPaint()
            onTempPrzedpokojChanged: requestPaint()
            onTempWCChanged:         requestPaint()

            // Przekazanie property z parenta do canvas (Canvas nie dziedziczy)
            property real tempSalon:     tempMapPopup.tempSalon
            property real tempJadalnia:  tempMapPopup.tempJadalnia
            property real tempPrzedpokoj:tempMapPopup.tempPrzedpokoj
            property real tempWC:        tempMapPopup.tempWC
            property real humSalon:      tempMapPopup.humSalon
            property real humJadalnia:   tempMapPopup.humJadalnia

            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()

                var W = width
                var H = height

                // ── Proporcje z planu (dopasowane do zdjęcia) ────────────
                // Cały budynek: szerokość W, wysokość H
                // Przedpokoj + Suszarnia + WC  → górny pas ~35% H
                // Salon (lewo) + Jadalnia (prawo) → dolny pas ~65% H
                // Salon ~55% W, Jadalnia ~45% W
                // Przedpokoj ~50% W, Suszarnia ~15% W, WC ~35% W

                var topH   = H * 0.35     // wysokość górnego pasa
                var botH   = H * 0.65     // wysokość dolnego pasa
                var botY   = topH         // Y początku dolnego pasa

                var salonW    = W * 0.54
                var jadW      = W - salonW
                var przedW    = W * 0.50
                var suszW     = W * 0.15
                var wcW       = W - przedW - suszW

                var wall   = 3            // grubość ściany
                var radius = 6            // zaokrąglenie narożników

                // Pomocnicza: wypełniony pokój z zaokrąglonymi narożnikami
                function roundRect(x, y, w, h, r, fillColor) {
                    ctx.beginPath()
                    ctx.moveTo(x + r, y)
                    ctx.lineTo(x + w - r, y)
                    ctx.quadraticCurveTo(x + w, y, x + w, y + r)
                    ctx.lineTo(x + w, y + h - r)
                    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h)
                    ctx.lineTo(x + r, y + h)
                    ctx.quadraticCurveTo(x, y + h, x, y + h - r)
                    ctx.lineTo(x, y + r)
                    ctx.quadraticCurveTo(x, y, x + r, y)
                    ctx.closePath()
                    ctx.fillStyle = fillColor
                    ctx.fill()
                    ctx.strokeStyle = "#555555"
                    ctx.lineWidth = wall
                    ctx.stroke()
                }

                // ── Pokoje ────────────────────────────────────────────────
                // Przedpokój
                roundRect(0, 0, przedW, topH, radius, tempMapPopup.roomColor(tempPrzedpokoj))
                // Suszarnia
                roundRect(przedW, 0, suszW, topH, radius, "#252525")
                // WC
                roundRect(przedW + suszW, 0, wcW, topH, radius, tempMapPopup.roomColor(tempWC))
                // Salon
                roundRect(0, botY, salonW, botH, radius, tempMapPopup.roomColor(tempSalon))
                // Jadalnia/Kuchnia
                roundRect(salonW, botY, jadW, botH, radius, tempMapPopup.roomColor(tempJadalnia))

                // ── Etykiety pokoi ────────────────────────────────────────
                ctx.textAlign    = "center"
                ctx.textBaseline = "middle"

                // Nazwa pokoju – mały, szary
                function drawLabel(label, temp, hum, cx, cy) {
                    // Nazwa
                    ctx.font = "bold 13px sans-serif"
                    ctx.fillStyle = "#aaaaaa"
                    ctx.fillText(label, cx, cy - 18)

                    // Temperatura – duża, biała
                    ctx.font = "bold 22px sans-serif"
                    ctx.fillStyle = isNaN(temp) ? "#555555" : "#ffffff"
                    ctx.fillText(tempMapPopup.tempText(temp), cx, cy + 4)

                    // Wilgotność – mała, szaroniebieska
                    if (!isNaN(hum)) {
                        ctx.font = "12px sans-serif"
                        ctx.fillStyle = "#78b0d0"
                        ctx.fillText("💧 " + tempMapPopup.humText(hum), cx, cy + 24)
                    }
                }

                drawLabel("Przedpokój", tempPrzedpokoj, NaN,
                          przedW / 2,       topH / 2)

                drawLabel("Suszarnia",  NaN, NaN,
                          przedW + suszW / 2, topH / 2)

                drawLabel("WC",         tempWC, NaN,
                          przedW + suszW + wcW / 2, topH / 2)

                drawLabel("Salon",      tempSalon, humSalon,
                          salonW / 2,     botY + botH / 2)

                drawLabel("Jadalnia /\nKuchnia", tempJadalnia, humJadalnia,
                          salonW + jadW / 2, botY + botH / 2)

                // ── Ikona termometru w lewym górnym rogu każdego pokoju ──
                ctx.font = "16px sans-serif"
                ctx.fillStyle = "#888888"
                ctx.textAlign = "left"
                if (!isNaN(tempSalon))    ctx.fillText("🌡", 8,         botY + 8)
                if (!isNaN(tempJadalnia)) ctx.fillText("🌡", salonW + 6, botY + 8)
                if (!isNaN(tempPrzedpokoj)) ctx.fillText("🌡", 8,       8)
                if (!isNaN(tempWC))       ctx.fillText("🌡", przedW + suszW + 4, 8)
            }
        }

        // Legenda kolorów
        Row {
            id: legend
            anchors.bottom: closeBtn.top
            anchors.bottomMargin: 4
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 20

            Repeater {
                model: [
                    {color: "#1a3a5c", label: "< 18°C"},
                    {color: "#1a3d2a", label: "20–22°C"},
                    {color: "#3d3a1a", label: "22–24°C"},
                    {color: "#5c1a1a", label: "> 26°C"}
                ]
                Row {
                    spacing: 4
                    Rectangle {
                        width: 12; height: 12
                        color: modelData.color
                        radius: 2
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: modelData.label
                        color: "#888888"
                        font.pixelSize: 11
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }
        }
    }
}

