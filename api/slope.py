import json
import requests
from geopy.distance import geodesic

def handler(request):
    try:
        body = request.json()
        origin = tuple(body["origin"])         # [lat, lon]
        destination = tuple(body["destination"])

        # Get route from OSRM
        osrm_url = f"http://router.project-osrm.org/route/v1/driving/{origin[1]},{origin[0]};{destination[1]},{destination[0]}?overview=full&geometries=geojson"
        res = requests.get(osrm_url).json()
        coordinates = res['routes'][0]['geometry']['coordinates']
        coordinates = [(lat, lon) for lon, lat in coordinates]

        # Sample every 0.25 km
        sampled_points = [coordinates[0]]
        accum_dist = 0
        for i in range(1, len(coordinates)):
            last = sampled_points[-1]
            current = coordinates[i]
            dist = geodesic(last, current).km
            accum_dist += dist
            if accum_dist >= 0.25:
                sampled_points.append(current)
                accum_dist = 0

        # Get elevation
        locations = [{"latitude": lat, "longitude": lon} for lat, lon in sampled_points]
        elev_res = requests.post("https://api.open-elevation.com/api/v1/lookup", json={"locations": locations})
        elevations = [pt["elevation"] for pt in elev_res.json()["results"]]

        # Analyze slope
        flat = uphill = steep = 0
        for i in range(1, len(sampled_points)):
            d = geodesic(sampled_points[i-1], sampled_points[i]).km
            diff = elevations[i] - elevations[i-1]

            if diff < 7:
                flat += d
            elif 7 <= diff < 15:
                uphill += d
            else:
                steep += d

        total_distance_km = geodesic(origin, destination).km
        total_tagged = flat + uphill + steep

        return {
            "statusCode": 200,
            "body": json.dumps({
                "origin": f"{origin[1]},{origin[0]}",
                "destination": f"{destination[1]},{destination[0]}",
                "flat_km": round(flat, 2),
                "uphill_km": round(uphill, 2),
                "steep_uphill_km": round(steep, 2),
                "total_distance_km": round(total_tagged, 2)
            }),
            "headers": {
                "Content-Type": "application/json"
            }
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
