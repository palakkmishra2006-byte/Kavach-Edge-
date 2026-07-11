const map = L.map('map').setView([12.9716, 77.5946], 13); // Bangalore
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    className: 'map-tiles'
}).addTo(map);
document.querySelector('.leaflet-layer').style.filter = 'invert(100%) hue-rotate(180deg) brightness(95%) contrast(90%)';
// Ambulances
const ambIcon = L.divIcon({
    className: 'custom-icon',
    html: '<div style="font-size:20px; background:#fff; border-radius:50%; padding:2px; box-shadow:0 0 10px #fff">🚑</div>',
    iconSize: [25, 25]
});
const ambulances = [
    {id: 1, lat: 12.9716, lng: 77.5946, tLat: 12.9816, tLng: 77.6046, marker: null},
    {id: 2, lat: 12.9516, lng: 77.5746, tLat: 12.9316, tLng: 77.5846, marker: null},
    {id: 3, lat: 12.9916, lng: 77.5546, tLat: 12.9816, tLng: 77.5246, marker: null}
];
ambulances.forEach(a => {
    a.marker = L.marker([a.lat, a.lng], {icon: ambIcon}).addTo(map);
});
let corridorActive = false;
let corridorLine = null;
setInterval(() => {
    ambulances.forEach(a => {
        // Move towards target
        const speed = corridorActive ? 0.001 : 0.0002;
        if(Math.abs(a.tLat - a.lat) > 0.0001) a.lat += (a.tLat > a.lat ? speed : -speed);
        if(Math.abs(a.tLng - a.lng) > 0.0001) a.lng += (a.tLng > a.lng ? speed : -speed);
        
        // Randomly pick new target if reached
        if(Math.abs(a.tLat - a.lat) < 0.001 && Math.abs(a.tLng - a.lng) < 0.001) {
            a.tLat = a.lat + (Math.random() - 0.5) * 0.05;
            a.tLng = a.lng + (Math.random() - 0.5) * 0.05;
        }
        
        a.marker.setLatLng([a.lat, a.lng]);
    });
    
    if(corridorActive && !corridorLine) {
        // Draw green line to target for Ambulance 1
        const a = ambulances[0];
        corridorLine = L.polyline([[a.lat, a.lng], [a.tLat, a.tLng]], {
            color: '#00e676', weight: 8, opacity: 0.8, dashArray: '10, 10'
        }).addTo(map);
    } else if (corridorActive && corridorLine) {
        const a = ambulances[0];
        corridorLine.setLatLngs([[a.lat, a.lng], [a.tLat, a.tLng]]);
    }
}, 200);
document.getElementById('btn-corridor').onclick = () => {
    corridorActive = !corridorActive;
    const btn = document.getElementById('btn-corridor');
    if(corridorActive) {
        btn.textContent = '🛑 CANCEL CORRIDOR';
        btn.style.background = 'var(--danger)';
        showToast('Green Corridor Initiated! Traffic signals synced to Green.', 'success');
    } else {
        btn.textContent = '🟢 INITIATE GREEN CORRIDOR';
        btn.style.background = 'var(--success)';
        if(corridorLine) map.removeLayer(corridorLine);
        corridorLine = null;
        showToast('Green Corridor Cancelled.', 'warning');
    }
};
function showToast(msg, type='info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = msg;
    document.getElementById('toast-container').appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}
document.getElementById('city-select').addEventListener('change', function(e) {
    const coords = e.target.value.split(',');
    map.flyTo([parseFloat(coords[0]), parseFloat(coords[1])], 13);
});
