const map = L.map('map').setView([19.0760, 72.8777], 11); // Mumbai
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    className: 'map-tiles'
}).addTo(map);
document.querySelector('.leaflet-layer').style.filter = 'invert(100%) hue-rotate(180deg) brightness(95%) contrast(90%)';
const sensors = [
    {id: 1, name: 'Bandra Kurla Complex', lat: 19.0619, lng: 72.8658, aqi: 85},
    {id: 2, name: 'Andheri East', lat: 19.1136, lng: 72.8697, aqi: 150},
    {id: 3, name: 'Chembur Industrial', lat: 19.0330, lng: 72.8966, aqi: 310},
    {id: 4, name: 'Borivali National Park', lat: 19.2290, lng: 72.8687, aqi: 45}
];
const markers = {};
const grid = document.getElementById('sensor-grid');
function getAqiColor(aqi) {
    if(aqi <= 50) return '#00e676';
    if(aqi <= 200) return '#ffab00';
    return '#ff1744';
}
function getAqiClass(aqi) {
    if(aqi <= 50) return 'good';
    if(aqi <= 200) return 'moderate';
    return 'poor';
}
function render() {
    grid.innerHTML = '';
    sensors.forEach(s => {
        // Map marker (Circles representing heatmap spread)
        if(markers[s.id]) map.removeLayer(markers[s.id]);
        markers[s.id] = L.circle([s.lat, s.lng], {
            color: getAqiColor(s.aqi),
            fillColor: getAqiColor(s.aqi),
            fillOpacity: 0.4,
            radius: 3000
        }).addTo(map);
        markers[s.id].bindPopup(`<b>${s.name}</b><br>AQI: ${s.aqi}`);
        // Sidebar card
        const card = document.createElement('div');
        card.className = 'sensor-card';
        card.innerHTML = `
            <div style="font-size:0.8rem; color:var(--text-secondary)">${s.name}</div>
            <div class="aqi-value ${getAqiClass(s.aqi)}">${s.aqi}</div>
            <div style="font-size:0.75rem;">PM2.5: ${Math.floor(s.aqi * 0.4)} µg/m³</div>
        `;
        grid.appendChild(card);
    });
}
// Simulate changing AQI
setInterval(() => {
    sensors.forEach(s => {
        s.aqi += Math.floor((Math.random() - 0.5) * 10);
        if(s.aqi < 10) s.aqi = 10;
        if(s.aqi > 500) s.aqi = 500;
    });
    render();
}, 4000);
render();
document.getElementById('city-select').addEventListener('change', function(e) {
    const coords = e.target.value.split(',');
    map.flyTo([parseFloat(coords[0]), parseFloat(coords[1])], 11);
});
