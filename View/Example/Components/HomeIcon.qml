// HomeIcon.qml
import QtQuick 2.15
import QtQuick.Shapes 1.15

Item {
    id: homeIcon
    width: 40
    height: 40

    Shape {
        anchors.fill: parent

        // Kształt dachu – trójkąt
        ShapePath {
            strokeWidth: 1
            strokeColor: "white"
            fillColor: "#656839" // kolor dachu, można dostosować
                // Tworzymy trójkątowy dach
                startX: width / 2; startY: 0
                PathLine { x: width; y: height * 0.5 }
                PathLine { x: 0; y: height * 0.5 }
                PathLine { x: width / 2; y: 0 }

        }

        // Kształt budynku – prostokąt
        ShapePath {
            strokeWidth: 1
            strokeColor: "white"
            fillColor: "#CAB7A2" // kolor podstawy budynku
                startX: homeIcon.width *0.25 ; startY: homeIcon.height * 0.5
                PathLine { x: (homeIcon.width) * 0.75; y: homeIcon.height * 0.5 }
                PathLine { x: (homeIcon.width) * 0.75; y: homeIcon.height * 0.95 }
                PathLine { x: (homeIcon.width) * 0.25; y: homeIcon.height * 0.95 }
                PathLine { x: (homeIcon.width) * 0.25; y: homeIcon.height * 0.5 }
        }
    }
}