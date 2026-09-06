// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann.
// Adapter only. Linked SNAP source retains its separate BSD-3-Clause license.
#include "Snap.h"
#include <iostream>
#include <string>

int main() {
    int nodes = 0, edges = 0;
    if (!(std::cin >> nodes >> edges) || nodes < 1 || nodes > 16 ||
        edges < 0 || edges > nodes * (nodes - 1) / 2) {
        std::cerr << "INVALID_GRAPH_SIZE\n";
        return 2;
    }
    PUNGraph graph = TUNGraph::New();
    for (int i = 0; i < nodes; ++i) { graph->AddNode(i); }
    for (int i = 0; i < edges; ++i) {
        int a = -1, b = -1;
        if (!(std::cin >> a >> b) || a < 0 || b < 0 || a >= nodes ||
            b >= nodes || a == b || graph->IsEdge(a, b)) {
            std::cerr << "INVALID_GRAPH_EDGE\n";
            return 2;
        }
        graph->AddEdge(a, b);
    }
    std::string extra;
    if (std::cin >> extra) { std::cerr << "TRAILING_INPUT\n"; return 2; }
    TCnComV components;
    TSnap::GetWccs(graph, components);
    int diameter = 0, unreachable = 0;
    for (int a = 0; a < nodes; ++a) {
        for (int b = 0; b < nodes; ++b) {
            if (a == b) { continue; }
            const int distance = TSnap::GetShortPath(graph, a, b, false);
            if (distance < 0) { ++unreachable; }
            else if (distance > diameter) { diameter = distance; }
        }
    }
    std::cout << "{\"nodes\":" << graph->GetNodes()
              << ",\"edges\":" << graph->GetEdges()
              << ",\"components\":" << components.Len()
              << ",\"max_component_diameter\":" << diameter
              << ",\"unreachable_ordered_pairs\":" << unreachable
              << ",\"degrees\":[";
    for (int i = 0; i < nodes; ++i) {
        if (i) { std::cout << ','; }
        std::cout << graph->GetNI(i).GetDeg();
    }
    std::cout << "]}\n";
    return 0;
}
