"""Match London service variations to physical OSM railway connections.

Edges connect only identical OSM node IDs. Coordinates alone never join tracks.
This describes railway alignment, not which individual running track was used.
"""
from __future__ import annotations

import heapq
import math
from collections import defaultdict

import numpy as np

from dashboard.replay import cumulative_distances
from scripts.prepare_replay_geometry import simplify


class RailGraph:
    def __init__(self, variants):
        self.nodes, edges, self.neighbours = {}, set(), defaultdict(list)
        for variant in variants:
            ids, points = variant["node_ids"], variant["coordinates"]
            if len(ids) != len(points):
                raise ValueError("OSM node IDs and coordinates differ in length")
            for key, point in zip(ids, points):
                if key in self.nodes and self.nodes[key] != point:
                    raise ValueError("An OSM node has conflicting coordinates")
                self.nodes[key] = point
            edges.update(tuple(sorted((a, b))) for a, b in zip(ids, ids[1:]) if a != b)
        self.edges = sorted(edges)
        self.lengths = []
        for a, b in self.edges:
            length = cumulative_distances([self.nodes[a], self.nodes[b]])[-1]
            self.lengths.append(length)
            self.neighbours[a].append((b, length))
            self.neighbours[b].append((a, length))
        self.scale = np.array([math.cos(math.radians(51.5)), 1]) * 111195
        self.starts = np.array([self.nodes[a] for a, _ in self.edges], dtype=float).reshape(-1, 2) * self.scale
        self.vectors = np.array([self.nodes[b] for _, b in self.edges], dtype=float).reshape(-1, 2) * self.scale - self.starts
        self.squares = np.maximum(np.sum(self.vectors ** 2, axis=1), 1e-20)
        self.anchor_cache, self.leg_cache = {}, {}

    def anchors(self, point):
        key = tuple(point)
        if key not in self.anchor_cache:
            offset = np.array(point) * self.scale - self.starts
            fractions = np.clip(np.sum(offset * self.vectors, axis=1) / self.squares, 0, 1)
            errors = np.sqrt(np.sum((offset - fractions[:, None] * self.vectors) ** 2, axis=1))
            candidates = np.where(errors <= 150)[0]
            candidates = sorted(candidates, key=lambda i: (errors[i], i))[:8]
            self.anchor_cache[key] = [(int(i), float(fractions[i]), float(errors[i]),
                ((self.starts[i] + fractions[i] * self.vectors[i]) / self.scale).tolist()) for i in candidates]
        return self.anchor_cache[key]

    def leg(self, origin, destination):
        key = (tuple(origin), tuple(destination))
        if key not in self.leg_cache:
            self.leg_cache[key] = self._leg(origin, destination)
        return self.leg_cache[key]

    def _leg(self, origin, destination):
        starts, ends = self.anchors(origin), self.anchors(destination)
        if not starts or not ends:
            return None
        limit = 6 * cumulative_distances([origin, destination])[-1] + 1000
        best, chosen, targets = math.inf, None, defaultdict(list)
        for end in ends:
            index, fraction, error, _ = end
            a, b = self.edges[index]
            targets[a].append((fraction * self.lengths[index] + 2 * error, end))
            targets[b].append(((1 - fraction) * self.lengths[index] + 2 * error, end))
            for start in starts:
                if start[0] == index:
                    score = abs(start[1] - fraction) * self.lengths[index] + 2 * (start[2] + error)
                    if score < best and score <= limit:
                        best, chosen = score, (start, end, [])
        queue, costs, previous, roots = [], {}, {}, {}
        for start in starts:
            index, fraction, error, _ = start
            for node, cost in ((self.edges[index][0], fraction * self.lengths[index]),
                               (self.edges[index][1], (1 - fraction) * self.lengths[index])):
                cost += 2 * error
                if cost < costs.get(node, math.inf):
                    costs[node], previous[node], roots[node] = cost, None, start
                    heapq.heappush(queue, (cost, node))
        while queue:
            cost, node = heapq.heappop(queue)
            if cost != costs[node]:
                continue
            if cost > min(best, limit):
                break
            for tail, end in targets.get(node, []):
                if cost + tail < best and cost + tail <= limit:
                    path, cursor = [], node
                    while cursor is not None:
                        path.append(cursor)
                        cursor = previous[cursor]
                    best, chosen = cost + tail, (roots[node], end, path[::-1])
            for neighbour, length in self.neighbours[node]:
                candidate = cost + length
                if candidate < costs.get(neighbour, math.inf) and candidate <= limit:
                    costs[neighbour], previous[neighbour], roots[neighbour] = candidate, node, roots[node]
                    heapq.heappush(queue, (candidate, neighbour))
        if chosen is None:
            return None
        start, end, nodes = chosen
        points = [start[3], *(self.nodes[node] for node in nodes), end[3]]
        points = [p for i, p in enumerate(points) if i == 0 or p != points[i - 1]]
        return simplify(points) if len(points) >= 2 else [points[0], points[0]]
