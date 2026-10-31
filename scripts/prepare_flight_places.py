"""Rebuild the lightweight geographical catalogue after preparing World flights."""
from dashboard.flight_places import prepare

if __name__ == '__main__':
    result = prepare()
    print(f"Prepared {len(result['places'])} places from {result['flights']} unique flights")
