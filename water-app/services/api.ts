/**
 * Backend base URL — set this to your dev machine LAN IP when testing on a device.
 * Wrong IP → failed fetch → dashboard shows 0%.
 */
export const API_BASE_URL = "http://192.168.2.208:8000";

export async function getForecast() {
  const res = await fetch(`${API_BASE_URL}/forecast/BLD_001`);
  return res.json();
}

export async function runSupervisor() {
  const res = await fetch(
    `${API_BASE_URL}/water/run?building_id=BLD_001&mode=latest`,
    { method: "POST" }
  );
  return res.json();
}

export async function getTasks() {
  const res = await fetch(`${API_BASE_URL}/tasks?building_id=BLD_001&limit=5`);
  return res.json();
}

export async function getNotifications() {
  const res = await fetch(`${API_BASE_URL}/notifications`);
  return res.json();
}
