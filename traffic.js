const map = L.map('map').setView([28.6139, 77.2090], 13); // Delhi
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    className: 'map-tiles'
}).addTo(map);
document.querySelector('.leaflet-layer').style.filter = 'invert(100%) hue-rotate(180deg) brightness(95%) contrast(90%)';
// Draw random roads
const roads = [];
for(let i=0; i<15; i++) {
    const lat1 = 28.6139 + (Math.random() - 0.5) * 0.1;
    const lng1 = 77.2090 + (Math.random() - 0.5) * 0.1;
    const lat2 = lat1 + (Math.random() - 0.5) * 0.02;
    const lng2 = lng1 + (Math.random() - 0.5) * 0.02;
    
    const polyline = L.polyline([[lat1, lng1], [lat2, lng2]], {
        color: '#00e676', weight: 5, opacity: 0.7
    }).addTo(map);
    roads.push(polyline);
}
// Simulate traffic congestion
setInterval(() => {
    roads.forEach(r => {
        if(Math.random() > 0.8) {
            r.setStyle({color: Math.random() > 0.5 ? '#ffab00' : '#ff1744'});
        } else {
            r.setStyle({color: '#00e676'});
        }
    });
}, 3000);
// Unregistered Vehicle Feed
const feed = document.getElementById('vehicle-feed');
const states = ['DL', 'HR', 'UP', 'MH', 'KA'];
const cams = ['Connaught Place Cam 4', 'Ring Road Entry', 'NH-8 Checkpoint', 'India Gate Circle'];
setInterval(() => {
    if(Math.random() > 0.7) {
        const plate = `${states[Math.floor(Math.random()*states.length)]} ${Math.floor(Math.random()*99)} ${String.fromCharCode(65+Math.floor(Math.random()*26))}${String.fromCharCode(65+Math.floor(Math.random()*26))} ${Math.floor(Math.random()*9000)+1000}`;
        const cam = cams[Math.floor(Math.random()*cams.length)];
        
        const card = document.createElement('div');
        card.className = 'plate-card';
        card.innerHTML = `
            <div>
                <div class="plate-no">${plate}</div>
                <div class="cam-loc">Spotted at: ${cam}</div>
            </div>
            <button style="background:rgba(255,23,68,0.2); color:#ff1744; border:1px solid #ff1744; padding:5px 10px; border-radius:4px; cursor:pointer;">FLAG</button>
        `;
        feed.prepend(card);
        if(feed.children.length > 20) feed.lastChild.remove();
    }
}, 2500);
document.getElementById('city-select').addEventListener('change', function(e) {
    const coords = e.target.value.split(',');
    map.flyTo([parseFloat(coords[0]), parseFloat(coords[1])], 13);
});
