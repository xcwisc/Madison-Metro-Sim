from datetime import timedelta
from math import sin, cos, asin, sqrt, pi
import heapq
import pandas as pd
import geopandas as gpd


class Node:
    def __init__(self, trip_id, stop_sequence, stop_id, stop_lat, stop_lon, arrival_time, max_walking_distance):
        self.trip_id = trip_id
        self.stop_sequence = stop_sequence
        self.stop_id = stop_id
        self.stop_lat = stop_lat
        self.stop_lon = stop_lon
        self.arrival_time = arrival_time
        # this should be modified by search in graph
        self.walking_distance = max_walking_distance
        self.children = []

    def distance(self, other):
        """Calculates the distance between two points on earth using the
        harversine distance (distance between points on a sphere)
        See: https://en.wikipedia.org/wiki/Haversine_formula

        :return: distance in meters between points
        """

        lat1, lon1, lat2, lon2 = (
            a/180*pi for a in [self.stop_lat, self.stop_lon, other.stop_lat, other.stop_lon])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon/2) ** 2
        c = 2 * asin(min(1, sqrt(a)))
        d = 3956 * 1609.344 * c
        return d

    def __str__(self):
        return f"trip_id: {self.trip_id} stop_sequence: {self.stop_sequence} stop_id: {self.stop_id} stop_lat: {self.stop_lat} stop_lon: {self.stop_lon} arrival_time: {self.arrival_time} walking_distance: {self.walking_distance}"

    def __repr__(self):
        rv = self.__str__()
        rv += "\nChildren:\n"
        for child in self.children:
            rv += f"  cost: {child.cost} "
            child = child.node
            rv += str(child)
            rv += "\n"
        return rv

    def __lt__(self, other):
        # always retain sequence here
        return False


class NodeCostPair:
    def __init__(self, node, cost):
        self.node = node
        self.cost = cost  # the cost here means the walking distance


class Graph:
    def __init__(self, df, start_time, elapse_time, max_walking_distance, avg_walking_speed):
        self.df = df
        self.start_time = start_time
        self.elapse_time = elapse_time
        self.max_walking_distance = max_walking_distance
        self.avg_walking_speed = avg_walking_speed
        self.nodes = []
        self._constuct_graph()

    def get_gdf(self, start_stop):
        start = self._find_start(start_stop)
        self._clear_graph()
        self._dijkstra(start)

        rows = dict()
        start_time = pd.to_timedelta(self.start_time)
        end_time = start_time + pd.to_timedelta(self.elapse_time)
        for node in self.nodes:
            if node.walking_distance < self.max_walking_distance:
                radius = self.max_walking_distance - node.walking_distance
                time_left = (end_time - node.arrival_time).total_seconds()
                radius = min(radius, self.avg_walking_speed * time_left)
                if node.stop_id not in rows or radius > rows[node.stop_id][3]:
                    rows[node.stop_id] = [node.stop_id, node.stop_lon,
                                          node.stop_lat, radius]
        rows = [row for row in rows.values()]

        # TODO: get the max radius from walking_distance and arrival time
        # radius = min(avg_walking_speed * time_left, max_walking_distance - walking_distance)

        df = pd.DataFrame(
            rows, columns=['stop_id', 'stop_lon', 'stop_lat', 'radius'])
        gdf = gpd.GeoDataFrame(
            df, geometry=gpd.points_from_xy(df.stop_lon, df.stop_lat), crs={'init': 'epsg:4326'})

        # https://epsg.io/3174
        gdf = gdf.to_crs({'init': 'epsg:3174'})
        gdf['geometry'] = gdf.geometry.buffer(gdf['radius'])
        gdf = gdf.to_crs({'init': 'epsg:4326'})

        return gdf

    def _clear_graph(self):
        for node in self.nodes:
            node.walking_distance = self.max_walking_distance

    def _dijkstra(self, start):
        start.walking_distance = 0
        pq = [(0, start)]
        while len(pq) > 0:
            curr_distance, curr_node = heapq.heappop(pq)

            if curr_distance > curr_node.walking_distance:
                continue

            for child in curr_node.children:
                cost = child.cost
                child = child.node

                distance = curr_distance + cost

                if distance < child.walking_distance:
                    child.walking_distance = distance
                    heapq.heappush(pq, (distance, child))

    def _constuct_graph(self):
        # gen nodes
        for index, row in self.df.iterrows():
            node = Node(row["trip_id"], row["stop_sequence"], row["stop_id"], row["stop_lat"],
                        row["stop_lon"], row["arrival_time"], self.max_walking_distance)
            self.nodes.append(node)

        # gen edges
        for start in self.nodes:
            for end in self.nodes:
                # unreachable for sure (can't go back in time)
                if start.arrival_time >= end.arrival_time:
                    continue

                # direct sequence
                if start.trip_id == end.trip_id:
                    if start.stop_sequence == end.stop_sequence - 1:
                        nodeCostPair = NodeCostPair(end, 0)
                        start.children.append(nodeCostPair)
                    continue

                # wait on the stop
                if start.stop_id == end.stop_id:
                    nodeCostPair = NodeCostPair(end, 0)
                    start.children.append(nodeCostPair)
                    continue

                # walk
                distance = start.distance(end)
                time_delta = distance / self.avg_walking_speed
                time_delta = timedelta(seconds=time_delta)
                if distance < self.max_walking_distance and start.arrival_time + time_delta < end.arrival_time:
                    nodeCostPair = NodeCostPair(end, distance)
                    start.children.append(nodeCostPair)

    def _find_start(self, start_stop):
        start = None
        for node in self.nodes:
            if node.stop_id == start_stop:
                if start is None or node.arrival_time < start.arrival_time:
                    start = node
        return start
