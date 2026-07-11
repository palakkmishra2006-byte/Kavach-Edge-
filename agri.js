const map = L.map('map').setView([23.2599, 77.4126], 15); // Bhopal rural area
// ESRI Satellite Tiles (No dark filter needed for agriculture)
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    attribution: 'Tiles &copy; Esri'
}).addTo(map);
// Leaflet Draw Controls
const drawnItems = new L.FeatureGroup();
map.addLayer(drawnItems);
const drawControl = new L.Control.Draw({
    draw: {
        polyline: false,
        marker: false,
        circlemarker: false,
        circle: false,
        polygon: {
            allowIntersection: false,
            drawError: { color: '#e1e100', message: '<strong>Invalid shape!<strong>' },
            shapeOptions: { color: '#00e676', fillColor: '#00e676', fillOpacity: 0.3 }
        },
        rectangle: {
            shapeOptions: { color: '#00e676', fillColor: '#00e676', fillOpacity: 0.3 }
        }
    },
    edit: {
        featureGroup: drawnItems
    }
});
map.addControl(drawControl);
map.on(L.Draw.Event.CREATED, function (event) {
    const layer = event.layer;
    drawnItems.addLayer(layer);
    
    // Calculate rough area (this is a simplified hackathon estimation)
    const latlngs = layer.getLatLngs()[0] || layer.getLatLngs();
    let area = 0;
    // Assuming simple geometry for demo purposes
    area = (Math.random() * 5 + 1).toFixed(2); // Mock Hectares for demo since real geodesic area needs turf.js
    
    document.getElementById('area-val').textContent = area;
    
    // Mock NDVI
    const ndvi = (Math.random() * 0.4 + 0.5).toFixed(2);
    const ndviEl = document.getElementById('ndvi-val');
    ndviEl.textContent = ndvi + ' (Healthy)';
    ndviEl.style.color = ndvi > 0.7 ? 'var(--success)' : 'var(--warning)';
});
map.on(L.Draw.Event.DELETED, function () {
    if(drawnItems.getLayers().length === 0) {
        document.getElementById('area-val').textContent = '0.00';
        document.getElementById('ndvi-val').textContent = '--';
    }
});
document.getElementById('city-select').addEventListener('change', function(e) {
    const coords = e.target.value.split(',');
    map.flyTo([parseFloat(coords[0]), parseFloat(coords[1])], 15);
});