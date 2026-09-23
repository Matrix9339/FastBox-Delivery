# FastBox Delivery System

## Overview

Mystery Delivery System is a Python-based logistics simulation program designed to simulate how packages can be assigned to delivery agents and delivered from warehouses to their respective destinations.

The main objective of this project is to take information about warehouses, delivery agents, and packages from JSON files, determine which agent is closest to each package's warehouse, assign the package to that agent, simulate the delivery, and finally generate a performance report for all agents.

The project also includes additional functionality such as random delivery delays, route visualization, support for an agent joining during the day, and exporting the top-performing agent to a CSV file.

The program is designed to work with both the provided base case and multiple test cases.

---

## Problem Statement

A logistics company has several warehouses, delivery agents, and packages that need to be delivered.

Each package:

- Belongs to a particular warehouse.
- Has a destination location.
- Needs to be assigned to a delivery agent.

Each delivery agent starts from a particular location.

For every package, the system needs to determine which agent is closest to the package's warehouse. Once an agent is assigned, the delivery is simulated using the following route:

```text
Agent → Warehouse → Destination