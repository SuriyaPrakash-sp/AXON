/* ===============================
   MAP SETUP – CHENNAI ONLY
================================ */

const chennaiBounds = [
  [12.90, 80.15], // SW
  [13.25, 80.35]  // NE
];

const map = L.map("map", {
  minZoom: 11,
  maxZoom: 18,
  maxBounds: chennaiBounds,
  maxBoundsViscosity: 1.0
}).fitBounds(chennaiBounds);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "© OpenStreetMap contributors"
}).addTo(map);

/* ===============================
   SENSOR NODES (20+ POINTS)
================================ */

const sensors = [
  { name: "Tondiarpet", coords: [13.13, 80.29], zone: "Red", color: "red", sos: true },
  { name: "Washermanpet", coords: [13.12, 80.28], zone: "Orange", color: "orange", sos: false },
  { name: "Royapuram", coords: [13.11, 80.30], zone: "Yellow", color: "yellow", sos: false },

  { name: "Egmore", coords: [13.08, 80.26], zone: "Orange", color: "orange", sos: false },
  { name: "Central", coords: [13.08, 80.27], zone: "Red", color: "red", sos: true },
  { name: "Triplicane", coords: [13.06, 80.28], zone: "Yellow", color: "yellow", sos: false },

  { name: "T Nagar", coords: [13.04, 80.23], zone: "Red", color: "red", sos: true },
  { name: "Kodambakkam", coords: [13.05, 80.22], zone: "Orange", color: "orange", sos: false },
  { name: "Ashok Nagar", coords: [13.03, 80.21], zone: "Yellow", color: "yellow", sos: false },

  { name: "Guindy", coords: [13.01, 80.21], zone: "Orange", color: "orange", sos: false },
  { name: "Saidapet", coords: [13.02, 80.23], zone: "Yellow", color: "yellow", sos: false },
  { name: "Velachery", coords: [12.98, 80.22], zone: "Red", color: "red", sos: true },

  { name: "Perungudi", coords: [12.97, 80.24], zone: "Orange", color: "orange", sos: false },
  { name: "Thoraipakkam", coords: [12.95, 80.24], zone: "Yellow", color: "yellow", sos: false },
  { name: "Sholinganallur", coords: [12.90, 80.23], zone: "Green", color: "green", sos: false },

  { name: "Anna Nagar", coords: [13.09, 80.21], zone: "Green", color: "green", sos: false },
  { name: "Mogappair", coords: [13.08, 80.18], zone: "Green", color: "green", sos: false },
  { name: "Ambattur", coords: [13.11, 80.16], zone: "Yellow", color: "yellow", sos: false },

  { name: "Porur", coords: [13.03, 80.16], zone: "Orange", color: "orange", sos: false },
  { name: "Poonamallee", coords: [13.05, 80.10], zone: "Green", color: "green", sos: false }
];

/* ===============================
   DRAINAGE NETWORK (GRAPH EDGES)
   → Dijkstra / BFS style
================================ */

const drainageEdges = [
  ["Tondiarpet", "Washermanpet"],
  ["Washermanpet", "Royapuram"],
  ["Royapuram", "Central"],
  ["Central", "Egmore"],
  ["Egmore", "Triplicane"],
  ["Triplicane", "T Nagar"],

  ["T Nagar", "Kodambakkam"],
  ["Kodambakkam", "Ashok Nagar"],
  ["Ashok Nagar", "Guindy"],
  ["Guindy", "Velachery"],
  ["Velachery", "Perungudi"],
  ["Perungudi", "Thoraipakkam"],
  ["Thoraipakkam", "Sholinganallur"],

  ["Egmore", "Anna Nagar"],
  ["Anna Nagar", "Mogappair"],
  ["Mogappair", "Ambattur"],

  ["Guindy", "Saidapet"],
  ["Saidapet", "T Nagar"],
  ["Porur", "Guindy"],
  ["Porur", "Poonamallee"]
];

// helper
function getSensorByName(name) {
  return sensors.find(s => s.name === name);
}

// draw drainage graph
drainageEdges.forEach(edge => {
  const a = getSensorByName(edge[0]);
  const b = getSensorByName(edge[1]);

  if (a && b) {
    L.polyline([a.coords, b.coords], {
      color: "#0066ff",
      weight: 3,
      opacity: 0.6,
      dashArray: "5,5"
    }).addTo(map);
  }
});

/* ===============================
   DRAW SENSOR NODES
================================ */

sensors.forEach(sensor => {
  const circle = L.circleMarker(sensor.coords, {
    radius: 9,
    fillColor: sensor.color,
    color: sensor.color,
    fillOpacity: 0.9
  }).addTo(map);

  const sos = sensor.sos
    ? `<span class="sos-red"></span>`
    : `<span class="sos-green"></span>`;

  circle.bindPopup(`
    <div class="popup-card">
      <b>Location:</b> ${sensor.name}<br>
      <b>Zone:</b> ${sensor.zone}<br>
      <b>SOS:</b> ${sos}
    </div>
  `);
});
