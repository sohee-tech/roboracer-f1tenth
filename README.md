# RoboRacer — F1TENTH Autonomous Racing

> **Competition:** IFAC 2026 F1TENTH Autonomous Racing Grand Prix
> **Stack:** ROS 2 Humble · Python 3 · Docker · F1TENTH Gym Simulator

---

## Overview

RoboRacer is a full-stack autonomous racing software stack built for the [F1TENTH](https://f1tenth.org/) 1:10-scale race car platform, developed for the **IFAC 2026** competition. The system covers the complete autonomy pipeline — from LiDAR-based safety monitoring through path planning to low-level drive control — running entirely inside a Dockerized ROS 2 Humble workspace.

---

## My Contribution — `safety_brake_node`

I designed and implemented the **LiDAR-based Automatic Emergency Braking (AEB)** safety layer (`safety` package). This node acts as a hardware-independent safety monitor that sits above all control nodes and can immediately suppress vehicle motion when a forward obstacle is detected.

### How It Works

```
/scan (LaserScan)
        │
        ▼
 ┌──────────────────────────────────┐
 │  Filter: forward ±20° sector     │
 │  Find minimum valid range        │
 └──────────────┬───────────────────┘
                │
       min_dist < 0.5 m ?
        ┌───────┴────────┐
       YES               NO
        │                │
  stop = true      stop = false
        │
        ▼
/safety/stop_required  →  pure_pursuit_node overrides speed → 0
/safety/min_front_distance  →  monitoring / logging
```

1. **Sector filtering** — On every `/scan` message, only rays within the forward **±20°** cone are considered. Rays outside this arc, and any `inf`/`NaN` readings, are discarded.
2. **Distance check** — The minimum range in that sector is compared against the **0.5 m** threshold (configurable via parameter).
3. **Signal broadcast** — A `Bool` flag is published to `/safety/stop_required` every scan cycle regardless of state, so downstream nodes always have a fresh value.
4. **Control override** — `pure_pursuit_node` subscribes to `/safety/stop_required` and overrides the computed speed to **0.0** before publishing the `AckermannDriveStamped` command, while keeping the steering angle intact so the car remains aligned.

### Topic Interface

| Direction | Topic | Type | Description |
|-----------|-------|------|-------------|
| Subscribes | `/scan` | `sensor_msgs/LaserScan` | Raw LiDAR data |
| Subscribes | `/localization/odom` | `nav_msgs/Odometry` | Current vehicle speed (logged in warnings) |
| **Publishes** | `/safety/stop_required` | `std_msgs/Bool` | `true` → emergency stop active |
| **Publishes** | `/safety/min_front_distance` | `std_msgs/Float32` | Closest forward obstacle distance (m) |

### Configurable Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `front_half_angle_deg` | `20.0` | Half-width of the forward detection cone (degrees) |
| `stop_distance_m` | `0.5` | Braking threshold distance (metres) |

### Integration with the Control Layer

`pure_pursuit_node` (in the `control` package) subscribes to `/safety/stop_required`. The safety override is applied at the very end of the control loop, after Pure Pursuit geometry and PID speed computation are complete:

```
Pure Pursuit  →  compute steering + PID speed
                        │
               stop_required == true?
                ┌────────┴────────┐
               YES               NO
                │                 │
           speed = 0.0      speed unchanged
                └────────┬────────┘
                         ▼
              publish AckermannDriveStamped
```

This design keeps the safety layer **decoupled** — neither node has a direct dependency on the other's internals, and the safety node can protect any future control implementation that subscribes to the same topic.

---

## Package Structure

```
roboracer-f1tenth/
└── algorithms/
    ├── safety/                         # AEB safety layer (my work)
    │   ├── safety/
    │   │   └── safety_brake_node.py    # LiDAR-based emergency braking node
    │   ├── launch/
    │   │   └── safety.launch.py
    │   └── package.xml
    │
    └── control/                        # Pure Pursuit path tracking
        ├── control/
        │   └── pure_pursuit_node.py    # Pure Pursuit + PID speed control
        ├── launch/
        │   └── control.launch.py
        └── package.xml
```

---

## Running the Stack

### Prerequisites

- Docker with NVIDIA runtime (or CPU-only F1TENTH gym image)
- ROS 2 Humble workspace with `ackermann_msgs` installed

### Build

```bash
cd roboracer-f1tenth
colcon build --symlink-install
source install/setup.bash
```

### Launch

**Safety node only:**
```bash
ros2 launch safety safety.launch.py
```

**Control node (simulation):**
```bash
ros2 launch control control.launch.py drive_mode:=sim
```

**Control node (real car):**
```bash
ros2 launch control control.launch.py drive_mode:=real
```

**Monitor safety state:**
```bash
ros2 topic echo /safety/stop_required
ros2 topic echo /safety/min_front_distance
```

### Override parameters at launch

```bash
ros2 launch safety safety.launch.py \
  front_half_angle_deg:=30.0 \
  stop_distance_m:=0.8
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Publish `stop_required` on every scan, not only on state change | Downstream nodes always have a fresh signal; no stale `false` if the safety node restarts |
| Keep steering intact during emergency stop | Allows the car to remain pointed correctly for immediate resumption after obstacle clearance |
| Parametrize cone angle and threshold | Tunable without recompile; easy to adapt for different track densities or speeds |
| Separate `safety` and `control` packages | Safety concerns stay isolated and testable independently of any control algorithm |

---

## License

MIT
