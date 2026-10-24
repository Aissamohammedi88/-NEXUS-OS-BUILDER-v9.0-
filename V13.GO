package main

import (
    "encoding/json"
    "fmt"
    "net/http"
    "time"
)

type SystemStatus struct {
    Status    string    `json:"status"`
    Timestamp time.Time `json:"timestamp"`
    NodeID    string    `json:"node_id"`
}

func HealthCheckHandler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    status := SystemStatus{
        Status:    "operational",
        Timestamp: time.Now(),
        NodeID:    "nexus-ipc-node-01",
    }
    json.NewEncoder(w).Encode(status)
}

func main() {
    fmt.Println("Demarrage du serveur IPC Nexus sur le port 8080...")
    http.HandleFunc("/api/v1/health", HealthCheckHandler)
    if err := http.ListenAndServe(":8080", nil); err != nil {
        fmt.Printf("Erreur serveur: %v\n", err)
    }
}
