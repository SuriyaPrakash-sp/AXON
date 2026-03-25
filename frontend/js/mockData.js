/**
 * Fallback preset — same JSON shape as GET /api/predictions from backend.
 */
window.ML_SAMPLE_OUTPUT = {
  meta: {
    modelId: "chennai-flood-risk-v0",
    modelVersion: "0.4.2-demo",
    generatedAt: "2025-03-25T08:30:00+05:30",
    source: "preset"
  },
  city: {
    overallRisk: "elevated",
    riskScore: 62,
    activeSosCount: 4,
    sensorsOnline: 20,
    sensorsTotal: 20
  },
  zoneCounts: {
    Green: 4,
    Yellow: 6,
    Orange: 6,
    Red: 4
  },
  predictions: [
    { location: "Tondiarpet", zone: "Red", floodProbability: 0.82, waterLevelCm: 118, sos: true },
    { location: "Washermanpet", zone: "Orange", floodProbability: 0.58, waterLevelCm: 72, sos: false },
    { location: "Royapuram", zone: "Yellow", floodProbability: 0.41, waterLevelCm: 48, sos: false },
    { location: "Egmore", zone: "Orange", floodProbability: 0.55, waterLevelCm: 68, sos: false },
    { location: "Central", zone: "Red", floodProbability: 0.79, waterLevelCm: 105, sos: true },
    { location: "Triplicane", zone: "Yellow", floodProbability: 0.38, waterLevelCm: 42, sos: false },
    { location: "T Nagar", zone: "Red", floodProbability: 0.85, waterLevelCm: 124, sos: true },
    { location: "Kodambakkam", zone: "Orange", floodProbability: 0.52, waterLevelCm: 65, sos: false },
    { location: "Ashok Nagar", zone: "Yellow", floodProbability: 0.35, waterLevelCm: 38, sos: false },
    { location: "Guindy", zone: "Orange", floodProbability: 0.49, waterLevelCm: 61, sos: false },
    { location: "Saidapet", zone: "Yellow", floodProbability: 0.33, waterLevelCm: 36, sos: false },
    { location: "Velachery", zone: "Red", floodProbability: 0.77, waterLevelCm: 98, sos: true },
    { location: "Perungudi", zone: "Orange", floodProbability: 0.54, waterLevelCm: 69, sos: false },
    { location: "Thoraipakkam", zone: "Yellow", floodProbability: 0.36, waterLevelCm: 40, sos: false },
    { location: "Sholinganallur", zone: "Green", floodProbability: 0.18, waterLevelCm: 22, sos: false },
    { location: "Anna Nagar", zone: "Green", floodProbability: 0.15, waterLevelCm: 18, sos: false },
    { location: "Mogappair", zone: "Green", floodProbability: 0.12, waterLevelCm: 15, sos: false },
    { location: "Ambattur", zone: "Yellow", floodProbability: 0.31, waterLevelCm: 34, sos: false },
    { location: "Porur", zone: "Orange", floodProbability: 0.47, waterLevelCm: 58, sos: false },
    { location: "Poonamallee", zone: "Green", floodProbability: 0.14, waterLevelCm: 16, sos: false }
  ]
};
