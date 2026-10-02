import requests

BASE = "http://127.0.0.1:5000"

routes = [
    "/",
    "/login",
    "/api/admin/overview",
    "/api/admin/stats",
    "/api/admin/logs",
    "/api/people",
    "/api/branches",
    "/api/system/health"
]

print("\n=== NSAMIZI SYSTEM TEST ===\n")

for route in routes:

    try:

        r = requests.get(BASE + route)

        print(
            f"{route:<35} "
            f"STATUS {r.status_code}"
        )

    except Exception as e:

        print(
            f"{route:<35} "
            f"ERROR {e}"
        )

print("\nFinished.\n")