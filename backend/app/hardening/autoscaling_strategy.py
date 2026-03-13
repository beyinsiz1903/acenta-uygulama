"""PART 8 — Auto-Scaling Strategy.

Scaling design for: API servers, worker nodes, Redis cluster, MongoDB replicas.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("hardening.autoscaling")


# Kubernetes HPA configurations
SCALING_CONFIGS = {
    "api_servers": {
        "component": "syroce-api",
        "type": "Deployment",
        "current_replicas": 2,
        "min_replicas": 2,
        "max_replicas": 10,
        "scaling_metrics": [
            {"type": "cpu", "target_utilization": 70, "unit": "%"},
            {"type": "memory", "target_utilization": 80, "unit": "%"},
            {"type": "custom", "metric": "http_requests_per_second", "target": 500},
        ],
        "scale_up_policy": {
            "stabilization_window_seconds": 60,
            "max_pods_per_scale": 2,
            "cooldown_seconds": 120,
        },
        "scale_down_policy": {
            "stabilization_window_seconds": 300,
            "max_pods_per_scale": 1,
            "cooldown_seconds": 300,
        },
        "resource_requests": {"cpu": "500m", "memory": "512Mi"},
        "resource_limits": {"cpu": "2000m", "memory": "2Gi"},
    },
    "worker_nodes": {
        "component": "syroce-worker",
        "type": "Deployment",
        "current_replicas": 1,
        "min_replicas": 1,
        "max_replicas": 8,
        "scaling_metrics": [
            {"type": "custom", "metric": "celery_queue_depth", "target": 50},
            {"type": "cpu", "target_utilization": 75, "unit": "%"},
        ],
        "scale_up_policy": {
            "stabilization_window_seconds": 30,
            "max_pods_per_scale": 3,
            "cooldown_seconds": 60,
        },
        "scale_down_policy": {
            "stabilization_window_seconds": 600,
            "max_pods_per_scale": 1,
            "cooldown_seconds": 300,
        },
        "resource_requests": {"cpu": "250m", "memory": "256Mi"},
        "resource_limits": {"cpu": "1000m", "memory": "1Gi"},
    },
    "redis_cluster": {
        "component": "syroce-redis",
        "type": "StatefulSet",
        "current_replicas": 1,
        "min_replicas": 3,
        "max_replicas": 6,
        "scaling_metrics": [
            {"type": "custom", "metric": "redis_memory_usage_pct", "target": 70},
            {"type": "custom", "metric": "redis_connected_clients", "target": 200},
        ],
        "topology": "cluster",
        "sentinel_quorum": 2,
        "persistence": {"rdb_save": "900 1", "aof_enabled": True},
        "resource_requests": {"cpu": "250m", "memory": "512Mi"},
        "resource_limits": {"cpu": "1000m", "memory": "2Gi"},
    },
    "mongodb_replicas": {
        "component": "syroce-mongodb",
        "type": "StatefulSet",
        "current_replicas": 1,
        "min_replicas": 3,
        "max_replicas": 7,
        "scaling_metrics": [
            {"type": "custom", "metric": "mongo_connections_pct", "target": 70},
            {"type": "custom", "metric": "mongo_replication_lag_seconds", "target": 5},
        ],
        "topology": "replica_set",
        "read_preference": "secondaryPreferred",
        "write_concern": {"w": "majority", "j": True},
        "storage": {"size": "100Gi", "storage_class": "gp3", "iops": 3000},
        "resource_requests": {"cpu": "500m", "memory": "1Gi"},
        "resource_limits": {"cpu": "4000m", "memory": "8Gi"},
    },
}


# Capacity planning thresholds
CAPACITY_THRESHOLDS = {
    "api_servers": {
        "requests_per_second": {"current": 200, "warning": 400, "critical": 800, "max_capacity": 1000},
        "concurrent_connections": {"current": 100, "warning": 300, "critical": 500, "max_capacity": 600},
        "memory_usage_pct": {"current": 45, "warning": 70, "critical": 85, "max_capacity": 95},
    },
    "mongodb": {
        "connections": {"current": 50, "warning": 200, "critical": 400, "max_capacity": 500},
        "storage_gb": {"current": 5, "warning": 50, "critical": 80, "max_capacity": 100},
        "ops_per_second": {"current": 500, "warning": 5000, "critical": 10000, "max_capacity": 15000},
    },
    "redis": {
        "memory_usage_mb": {"current": 50, "warning": 300, "critical": 450, "max_capacity": 512},
        "connections": {"current": 20, "warning": 150, "critical": 250, "max_capacity": 300},
        "ops_per_second": {"current": 1000, "warning": 50000, "critical": 80000, "max_capacity": 100000},
    },
    "celery": {
        "queue_depth": {"current": 5, "warning": 50, "critical": 200, "max_capacity": 500},
        "task_latency_ms": {"current": 500, "warning": 5000, "critical": 15000, "max_capacity": 30000},
    },
}


def get_autoscaling_status() -> dict:
    """Get complete auto-scaling strategy and current capacity."""
    return {
        "scaling_configs": SCALING_CONFIGS,
        "capacity_thresholds": CAPACITY_THRESHOLDS,
        "recommendations": [
            {"component": "api_servers", "action": "Ready for horizontal scaling via Kubernetes HPA", "priority": "P0"},
            {"component": "worker_nodes", "action": "Configure queue-depth-based HPA with KEDA", "priority": "P0"},
            {"component": "redis", "action": "Deploy Redis Cluster with 3 nodes minimum", "priority": "P1"},
            {"component": "mongodb", "action": "Deploy as ReplicaSet with 3 members", "priority": "P1"},
        ],
    }
