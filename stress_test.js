import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = 'http://localhost:8000';
const headers = { 'Content-Type': 'application/json' };

export const options = {
  stages: [
    { duration: '1m', target: 100 },
    { duration: '2m', target: 300 },
    { duration: '2m', target: 500 },
    { duration: '1m', target: 500 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'],
    http_req_failed: ['rate<0.05'],
  },
};

export default function () {

  const arrivals = http.get(
    `${BASE_URL}/fr2-2/arrivals?stop_id=3&gender=male&minutes_ahead=60`
  );
  check(arrivals, {
    'arrivals 200': (r) => r.status === 200,
    'arrivals under 2s': (r) => r.timings.duration < 2000,
  });

  const graph = http.get(
    `${BASE_URL}/graph?gender=male&objective=shortest`
  );
  check(graph, {
    'graph 200': (r) => r.status === 200,
    'graph under 2s': (r) => r.timings.duration < 2000,
  });

  const gets = http.batch([
    ['GET', `${BASE_URL}/fr2-2/timetable-simple`],
    ['GET', `${BASE_URL}/graph/summary`],
    ['GET', `${BASE_URL}/fr2-4/routes`],
    ['GET', `${BASE_URL}/fr2-4/stops`],
  ]);
  gets.forEach((res) => {
    check(res, {
      'GET 200': (r) => r.status === 200,
      'GET under 2s': (r) => r.timings.duration < 2000,
    });
  });

  const walkNearest = http.post(
    `${BASE_URL}/fr:walking steps+transfer points/walk-to-nearest`,
    JSON.stringify({ lat: 24.9004187, lon: 67.1963745 }),
    { headers }
  );
  check(walkNearest, {
    'walk-to-nearest 200': (r) => r.status === 200,
    'walk-to-nearest under 3s': (r) => r.timings.duration < 3000,
  });

  const walkFromStop = http.post(
    `${BASE_URL}/fr:walking steps+transfer points/walk-from-stop-to-pin`,
    JSON.stringify({ stop_id: 5, pin_lat: 24.8844268, pin_lon: 67.1745528 }),
    { headers }
  );
  check(walkFromStop, {
    'walk-from-stop 200': (r) => r.status === 200,
    'walk-from-stop under 3s': (r) => r.timings.duration < 3000,
  });

  const computeTrip = http.post(
    `${BASE_URL}/compute-trip`,
    JSON.stringify({
      input_mode: "text",
      origin: { text: "Numaish Chowrangi" },
      destination: { text: "Malir Halt" },
      gender: "male",
      objective: "shortest",
      include_polyline: false
    }),
    { headers }
  );
  check(computeTrip, {
    'compute-trip 200': (r) => r.status === 200,
    'compute-trip under 5s': (r) => r.timings.duration < 5000,
  });

  const stopSearch = http.get(`${BASE_URL}/stop-suggestions?q=Malir`);
  check(stopSearch, {
    'stop-suggestions 200': (r) => r.status === 200,
    'stop-suggestions under 1s': (r) => r.timings.duration < 1000,
  });

  sleep(1);
}

//Compute-trip was tested without polyline rendering to isolate our backend's performance from the external OSRM dependency