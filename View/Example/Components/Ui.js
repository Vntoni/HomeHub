.pragma library
function temperature(value) {
    return isFinite(value) ? Number(value).toLocaleString(Qt.locale("pl_PL"), "f", 1) + "°C" : "—"
}
function mode(value) {
    var labels = {COOL: "Chłodzenie", HEAT: "Ogrzewanie", FAN: "Wentylacja", DRY: "Osuszanie",
        AUTO: "Automatyczny", OFF: "Wyłączony", GREEN: "Eco", IMEMORY: "Pamięć",
        BOOST: "Szybkie nagrzewanie", PROGRAM: "Harmonogram", manual: "Ręczny", program: "Harmonogram"}
    return labels[value] || "Nieznany"
}

function fanSpeed(value) {
    var labels = {QUIET: "Cisza", LOW: "Niska", MEDIUM: "Średnia", HIGH: "Wysoka", AUTO: "Auto",
        MEDIUM_LOW: "Pośrednia: niska / średnia", MEDIUM_HIGH: "Pośrednia: średnia / wysoka"}
    return labels[value] || "Brak odczytu"
}
