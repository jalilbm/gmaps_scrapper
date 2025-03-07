# import geojson
# from shapely.geometry import shape, Point
# import numpy as np
# import os


# def get_location_shape(location_name):
#     # Parse the GeoJSON
#     with open(f"./inputs/locations/{location_name}.geojson", "r") as f:
#         data = geojson.load(f)

#     # Convert to Shapely geometry
#     return shape(data["geojson"])


# def check_point_in_bounds(lon, lat, location_name):
#     point = Point(lon, lat)
#     location = get_location_shape(location_name)
#     return location.contains(point)


# def get_16_z_points(location_name):
#     location = get_location_shape(location_name)

#     # Get bounds
#     min_lon, min_lat, max_lon, max_lat = location.bounds

#     # Size of a zoom 16 tile in meters
#     # tile_size = 611.5  # The tile size might be different based on the location. You may want to fine-tune this.
#     tile_size = 1200

#     # Calculate the conversion factor for longitude
#     mid_lat = (min_lat + max_lat) / 2
#     km_per_degree_longitude = 111.320 * np.cos(mid_lat)

#     # Convert tile size to degrees
#     tile_size_deg_lat = tile_size / 111000
#     tile_size_deg_lon = tile_size / (km_per_degree_longitude * 1000)

#     # Generate the grid of points
#     points = []
#     lat = min_lat
#     while lat < max_lat:
#         lon = min_lon
#         while lon < max_lon:
#             point = Point(lon, lat)
#             if location.contains(point):
#                 points.append({"lon": lon, "lat": lat})
#             lon += tile_size_deg_lon
#         lat += tile_size_deg_lat

#     return points

import geopandas as gpd
from shapely.geometry import Point
import numpy as np


def get_location_shape(location_name):
    # Parse the GeoJSON
    gdf = gpd.read_file(f"./inputs/locations/{location_name}.geojson")

    # Convert to Shapely geometry
    return gdf.geometry.unary_union


def check_point_in_bounds(lon, lat, location_name):
    point = Point(lon, lat)
    location = get_location_shape(location_name)
    return location.contains(point)


def get_16_z_points(location_name):
    location = get_location_shape(location_name)

    # Get bounds
    min_lon, min_lat, max_lon, max_lat = location.bounds

    # Size of a zoom 16 tile in meters
    # tile_size = 611.5  # The tile size might be different based on the location. You may want to fine-tune this.
    tile_size = 2400

    # Calculate the conversion factor for longitude
    mid_lat = (min_lat + max_lat) / 2
    km_per_degree_longitude = 111.320 * np.cos(np.radians(mid_lat))

    # Convert tile size to degrees
    tile_size_deg_lat = tile_size / 111000
    tile_size_deg_lon = tile_size / (km_per_degree_longitude * 1000)

    # Generate the grid of points
    points = []
    lat = min_lat
    while lat < max_lat:
        lon = min_lon
        while lon < max_lon:
            point = Point(lon, lat)
            if location.contains(point):
                points.append({"lon": lon, "lat": lat})
            lon += tile_size_deg_lon
        lat += tile_size_deg_lat

    return points
