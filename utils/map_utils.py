"""Helper class that all things map related"""
import logging
import requests
import numpy as np
import pandas as pd
import os
from typing import Union, Tuple

import geopandas as gpd
from geopy.distance import geodesic

from requests.exceptions import ConnectTimeout, ReadTimeout

POSTAL_DISTRICT = pd.read_csv(
    "./data/postal_district.csv", dtype={"postal_prefix": str}
)


def get_address_details(location: str, logger=None):  # -> tuple[float, float, str]:
    """Calls OneMap API to retrieve the latitude, longitude, and postal code of a location.

    Args:
        location (str): The address or location to search for.
        logger (Optional): Logger object for logging. Defaults to None.

    Returns:
        tuple[float, float, str]: A tuple containing the latitude, longitude, and postal code.
                                  If the details cannot be obtained, an empty string is returned.

    Raises:
        ConnectTimeout: If the connection times out while making the API request.
        ReadTimeout: If the read operation times out while receiving the API response.
    """
    try:
        url = f"https://developers.onemap.sg/commonapi/search?searchVal={location}&returnGeom=Y&getAddrDetails=Y&pageNum=1"
        req = requests.get(url, timeout=15.0)
        resultsdict = eval(req.text)

        if len(resultsdict["results"]) > 0:
            lat = resultsdict["results"][0]["LATITUDE"]
            long = resultsdict["results"][0]["LONGITUDE"]
            postal = resultsdict["results"][0]["POSTAL"]
            address = (
                resultsdict["results"][0]["BLK_NO"]
                + " "
                + resultsdict["results"][0]["ROAD_NAME"]
            )
            buildingname = resultsdict["results"][0]["BUILDING"]
            print(resultsdict["results"][0])
            return lat, long, postal, address, buildingname

    except ConnectTimeout:
        if logger != None:
            logger.info("Request has connection timed out")

    except ReadTimeout:
        if logger != None:
            logger.info("Request has read timed out")

    return "", "", "", ""


def get_district_and_zone(postal_code: str):  # -> tuple[str, str]:
    """Retrieve the district and zone based on a postal code.

    Args:
        postal_code (str): The postal code to retrieve district and zone information.

    Returns:
        tuple[str, str]: A tuple containing the zone and district of the postal code.
                        If the information is not available, an empty string is returned.
    """
    if len(postal_code) > 2:
        postal_id = postal_code[:2]
        result = POSTAL_DISTRICT.loc[
            POSTAL_DISTRICT["postal_prefix"] == postal_id, ["zone", "district"]
        ]
        return result.iloc[0, 0], result.iloc[0, 1]

    return "", ""


def get_nearest_facility(
    location_latitude: float, location_longitude: float, facilities: str
):  # -> Tuple[Union[float, str], str, float, float]:
    """Finds the nearest facility to a given location.

    Args:
        location_latitude (float): The latitude of the location.
        location_longitude (float): The longitude of the location.
        facilities (str): The type of facility to search for. Valid strings accepted are "schools", "hawker_centres_markets", "shopping_malls" or "stations".

    Returns:
        Tuple[Union[float, str], str, float, float]: A tuple containing the minimum distance, nearest facility name, latitude, and longitude. If no facility is found, empty strings are returned for distance, facility name, latitude, and longitude.

    Raises:
        ValueError: If an invalid string is provided for the "facilities" argument.
    """
    min_distance, nearest_facility, nearest_facility_lat, nearest_facility_long = (
        "",
        "",
        "",
        "",
    )
    location_coords = (location_latitude, location_longitude)

    if facilities == "schools":
        file_name = "primary_schools.csv"
        reference_column = "Primary Schools"
    elif facilities == "hawker_centres_markets":
        file_name = "hawker_centres_markets.csv"
        reference_column = "Name of Hawker Centre / Market"
    elif facilities == "shopping_malls":
        file_name = "shopping_malls.csv"
        reference_column = "Shopping Mall"
    elif facilities == "stations":
        file_name = "stations.csv"
        reference_column = "STN_NAM_DE"
    else:
        raise ValueError(
            'Please provide a valid string for "facilities" from "schools", "hawker_centres_markets", "shopping_malls" or "stations"!'
        )

    csv_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", file_name)
    df = pd.read_csv(csv_path)
    min_distance = float("inf")
    nearest_facility = None

    for _, facility in df.iterrows():
        facility_coords = (facility["Latitude"], facility["Longitude"])

        distance = geodesic(location_coords, facility_coords).meters
        if distance < min_distance:
            min_distance = distance
            nearest_facility = facility[reference_column]
            nearest_facility_lat = facility["Latitude"]
            nearest_facility_long = facility["Longitude"]

    return min_distance, nearest_facility, nearest_facility_lat, nearest_facility_long


def count_primary_schools_within_distance(
    location_latitude: float, location_longitude: float, distance_km: float
):  # -> int:
    """Counts the number of primary schools within a certain distance from a location.

    Args:
        location_latitude (float): The latitude of the location to search for.
        location_longitude (float): The longitude of the location to search for.
        distance_km (float): The maximum distance in kilometers to consider for counting.

    Returns:
        int: The count of primary schools within the specified distance.
    """
    count = 0
    csv_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "primary_schools.csv"
    )
    df = pd.read_csv(csv_path)

    location_coords = (location_latitude, location_longitude)

    for _, school in df.iterrows():
        distance = geodesic(
            location_coords, (school["Latitude"], school["Longitude"])
        ).kilometers

        if distance <= distance_km:
            count += 1

    return count


def calculate_distance_to_cbd(
    location_latitude: float, location_longitude: float
):  # -> float:
    """Calculates the distance between a location and the Central Business District (CBD) which is predefined by the location of Raffles MRT station.

    Args:
        location_latitude (float): The latitude of the location to calculate the distance from.
        location_longitude (float): The longitude of the location to calculate the distance from.

    Returns:
        float: The distance in meters between the location and the CBD (represented by Raffles Place MRT station).
    """
    location_coords = (location_latitude, location_longitude)
    cbd_coords = (1.283933262, 103.8514631)
    distance = geodesic(location_coords, cbd_coords).meters
    return distance


def getwalkingdetails(
    start_coordinates: str, end_coordinates: str, token: str
) -> tuple:
    """Get the walking distance, time taken to walk, and the walking route from start to end coordinates.

    Args:
        start_coordinates (str): The starting coordinates of the walking route.
        end_coordinates (str): The ending coordinates of the walking route.
        token (str): The API token for accessing the routing service.

    Returns:
        tuple: A tuple containing the total distance (in meters), total time (in seconds),
               and the geometry of the walking route.
    """
    req = requests.get(
        "https://developers.onemap.sg/privateapi/routingsvc/route?start="
        + start_coordinates
        + "&end="
        + end_coordinates
        + "&routeType=walk&token="
        + token
    )
    resultsdict = eval(req.text)
    return (
        resultsdict["route_summary"]["total_distance"],
        resultsdict["route_summary"]["total_time"],
        resultsdict["route_geometry"],
    )


def find_neighbours(
    lat_lon: tuple, flat_type: str, radius: int, df: pd.DataFrame
) -> pd.DataFrame:
    """Returns a DataFrame of building names within a specified radius (in meters) of a given latitude-longitude pair.

    Args:
        lat_lon (tuple): Latitude and longitude coordinates of the target location.
        flat_type (str): The desired type of flat.
        radius (int): The radius (in meters) within which to search for nearby buildings.
        df (pd.DataFrame): The DataFrame containing the building information.

    Returns:
        pd.DataFrame: A DataFrame with the buildings within the specified radius and matching the flat type.
    """
    df = df.copy()
    # Initialize an empty list to store the building names
    indices = []
    buildings = []
    # Loop through the rows of the dataframe with the same flat type
    dfslice = df[df["flat_type"] == flat_type].reset_index(drop=True)

    for index, row in dfslice[::-1].iterrows():
        if row["address"] not in buildings:
            # Get the lat-lon pair of the current row
            point = (row["lat"], row["lon"])
            # Calculate the distance between the input point and the current point
            distance = geodesic(lat_lon, point).meters  # km, <=1

            # print(distance)
            # If the distance is less than or equal to 1km, append the building name to the list
            if distance <= radius:
                indices.append(index)
                buildings.append(row["address"])
    # Return the dataframe slice of the same flat types in the neighbourhood
    return dfslice.loc[indices]


if __name__ == "__main__":
    zone, district = get_district_and_zone("210039")
    lat, long, postal = get_address_details("210039")
    min_geodisic_distance_to_station, _, _, _ = get_nearest_facility(
        lat, long, "stations"
    )
    min_geodisic_distance_to_shopping_mall, _, _, _ = get_nearest_facility(
        lat, long, "shopping_malls"
    )
    min_geodisic_distance_to_hawker_market, _, _, _ = get_nearest_facility(
        lat, long, "hawker_centres_markets"
    )
    pri_sch_1km = count_primary_schools_within_distance(lat, long, 1)
    pri_sch_2km = count_primary_schools_within_distance(lat, long, 2)
    geodesic_distance_to_cbd = calculate_distance_to_cbd(lat, long)

    print(zone)
