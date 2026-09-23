import json
import math
import os
import random
import csv


# =========================================================
# CONFIGURATION
# =========================================================

# Random delivery delay settings
MIN_DELAY = 5
MAX_DELAY = 30


# =========================================================
# DISTANCE
# =========================================================

def calculate_distance(point1, point2):

    x1, y1 = point1
    x2, y2 = point2

    return math.sqrt(
        (x2 - x1) ** 2 +
        (y2 - y1) ** 2
    )


# =========================================================
# NORMALIZE INPUT DATA
# =========================================================

def normalize_data(data):

    if not isinstance(data, dict):
        raise ValueError(
            "JSON data must be an object."
        )

    # -----------------------------------------------------
    # Warehouses
    # -----------------------------------------------------

    if "warehouses" not in data:
        raise ValueError(
            "Missing 'warehouses' field."
        )

    if isinstance(data["warehouses"], list):

        warehouse_map = {}

        for warehouse in data["warehouses"]:

            if not isinstance(warehouse, dict):
                raise ValueError(
                    "Each warehouse must be an object."
                )

            if "id" not in warehouse:
                raise ValueError(
                    "Warehouse is missing 'id'."
                )

            if "location" not in warehouse:
                raise ValueError(
                    f"Warehouse {warehouse['id']} "
                    "is missing 'location'."
                )

            warehouse_id = warehouse["id"]
            location = warehouse["location"]

            if warehouse_id in warehouse_map:
                raise ValueError(
                    f"Duplicate warehouse ID: "
                    f"{warehouse_id}"
                )

            warehouse_map[warehouse_id] = location

    elif isinstance(data["warehouses"], dict):

        warehouse_map = data["warehouses"].copy()

    else:

        raise ValueError(
            "'warehouses' must be a list or dictionary."
        )

    # -----------------------------------------------------
    # Agents
    # -----------------------------------------------------

    if "agents" not in data:
        raise ValueError(
            "Missing 'agents' field."
        )

    if isinstance(data["agents"], list):

        agent_map = {}

        for agent in data["agents"]:

            if not isinstance(agent, dict):
                raise ValueError(
                    "Each agent must be an object."
                )

            if "id" not in agent:
                raise ValueError(
                    "Agent is missing 'id'."
                )

            if "location" not in agent:
                raise ValueError(
                    f"Agent {agent['id']} "
                    "is missing 'location'."
                )

            agent_id = agent["id"]
            location = agent["location"]

            if agent_id in agent_map:
                raise ValueError(
                    f"Duplicate agent ID: {agent_id}"
                )

            agent_map[agent_id] = location

    elif isinstance(data["agents"], dict):

        agent_map = data["agents"].copy()

    else:

        raise ValueError(
            "'agents' must be a list or dictionary."
        )

    # -----------------------------------------------------
    # Packages
    # -----------------------------------------------------

    if "packages" not in data:
        raise ValueError(
            "Missing 'packages' field."
        )

    if not isinstance(data["packages"], list):
        raise ValueError(
            "'packages' must be a list."
        )

    packages = []
    package_ids = set()

    for package in data["packages"]:

        if not isinstance(package, dict):
            raise ValueError(
                "Each package must be an object."
            )

        if "id" not in package:
            raise ValueError(
                "Package is missing 'id'."
            )

        package_id = package["id"]

        if package_id in package_ids:
            raise ValueError(
                f"Duplicate package ID: {package_id}"
            )

        package_ids.add(package_id)

        # Support both formats
        if "warehouse_id" in package:

            warehouse_id = package["warehouse_id"]

        elif "warehouse" in package:

            warehouse_id = package["warehouse"]

        else:

            raise ValueError(
                f"Package {package_id} is missing "
                "'warehouse' or 'warehouse_id'."
            )

        if "destination" not in package:

            raise ValueError(
                f"Package {package_id} is missing "
                "'destination'."
            )

        packages.append({
            "id": package_id,
            "warehouse": warehouse_id,
            "destination": package["destination"]
        })

    # -----------------------------------------------------
    # Return common structure
    # -----------------------------------------------------

    return {
        "warehouses": warehouse_map,
        "agents": agent_map,
        "packages": packages
    }


# =========================================================
# VALIDATE DATA
# =========================================================

def validate_data(data):

    required_fields = [
        "warehouses",
        "agents",
        "packages"
    ]

    for field in required_fields:

        if field not in data:
            raise ValueError(
                f"Missing field: {field}"
            )

    warehouses = data["warehouses"]
    agents = data["agents"]
    packages = data["packages"]

    # -----------------------------------------------------
    # Warehouses
    # -----------------------------------------------------

    if not isinstance(warehouses, dict):

        raise ValueError(
            "'warehouses' must be a dictionary "
            "after normalization."
        )

    if len(warehouses) == 0:

        raise ValueError(
            "At least one warehouse is required."
        )

    for warehouse_id, location in warehouses.items():

        if (
            not isinstance(location, list)
            or len(location) != 2
        ):

            raise ValueError(
                f"Warehouse {warehouse_id} must have "
                "[x, y] coordinates."
            )

        if not all(
            isinstance(value, (int, float))
            for value in location
        ):

            raise ValueError(
                f"Warehouse {warehouse_id} has "
                "invalid coordinates."
            )

    # -----------------------------------------------------
    # Agents
    # -----------------------------------------------------

    if not isinstance(agents, dict):

        raise ValueError(
            "'agents' must be a dictionary "
            "after normalization."
        )

    if len(agents) == 0:

        raise ValueError(
            "At least one agent is required."
        )

    for agent_id, location in agents.items():

        if (
            not isinstance(location, list)
            or len(location) != 2
        ):

            raise ValueError(
                f"Agent {agent_id} must have "
                "[x, y] coordinates."
            )

        if not all(
            isinstance(value, (int, float))
            for value in location
        ):

            raise ValueError(
                f"Agent {agent_id} has "
                "invalid coordinates."
            )

    # -----------------------------------------------------
    # Packages
    # -----------------------------------------------------

    if not isinstance(packages, list):

        raise ValueError(
            "'packages' must be a list."
        )

    package_ids = set()

    for package in packages:

        package_id = package["id"]

        if package_id in package_ids:

            raise ValueError(
                f"Duplicate package ID: {package_id}"
            )

        package_ids.add(package_id)

        warehouse_id = package["warehouse"]

        if warehouse_id not in warehouses:

            raise ValueError(
                f"Package {package_id} refers to "
                f"unknown warehouse {warehouse_id}."
            )

        destination = package["destination"]

        if (
            not isinstance(destination, list)
            or len(destination) != 2
        ):

            raise ValueError(
                f"Package {package_id} must have "
                "[x, y] destination coordinates."
            )

        if not all(
            isinstance(value, (int, float))
            for value in destination
        ):

            raise ValueError(
                f"Package {package_id} has "
                "invalid destination coordinates."
            )


# =========================================================
# FIND NEAREST AGENT
# =========================================================

def find_nearest_agent(
    warehouse_location,
    agents,
    current_location=None
):

    nearest_agent = None
    shortest_distance = float("inf")

    for agent_id in agents:

        # For normal assignment, use the agent's current
        # position.
        if current_location is not None:

            agent_location = current_location[agent_id]

        else:

            agent_location = agents[agent_id]

        distance = calculate_distance(
            agent_location,
            warehouse_location
        )

        if distance < shortest_distance:

            shortest_distance = distance
            nearest_agent = agent_id

    return nearest_agent


# =========================================================
# ASSIGN PACKAGES
# =========================================================

def assign_packages(data):

    warehouses = data["warehouses"]
    agents = data["agents"]

    assignments = {}

    for package in data["packages"]:

        package_id = package["id"]
        warehouse_id = package["warehouse"]

        warehouse_location = warehouses[warehouse_id]

        nearest_agent = find_nearest_agent(
            warehouse_location,
            agents
        )

        assignments[package_id] = nearest_agent

    return assignments


# =========================================================
# RANDOM DELIVERY DELAY
# =========================================================

def generate_random_delay():

    return random.randint(
        MIN_DELAY,
        MAX_DELAY
    )


# =========================================================
# SIMULATE DELIVERIES
# =========================================================

def simulate_deliveries(
    data,
    assignments,
    use_delays=False,
    mid_day_agent=None
):

    warehouses = data["warehouses"]
    agents = data["agents"]
    packages = data["packages"]

    # -----------------------------------------------------
    # Copy agents so original data isn't modified
    # -----------------------------------------------------

    current_agents = agents.copy()

    # -----------------------------------------------------
    # Tracking information
    # -----------------------------------------------------

    total_distance = {}

    packages_delivered = {}

    current_location = {}

    total_delay = {}

    route_history = {}

    # -----------------------------------------------------
    # Initialize agents
    # -----------------------------------------------------

    for agent_id, location in current_agents.items():

        total_distance[agent_id] = 0.0

        packages_delivered[agent_id] = 0

        total_delay[agent_id] = 0

        current_location[agent_id] = location[:]

        route_history[agent_id] = []

        # Starting location
        route_history[agent_id].append(
            {
                "type": "start",
                "location": location[:]
            }
        )

    # -----------------------------------------------------
    # Determine when new agent joins
    #
    # If there are 10 packages, it joins before package 6.
    # -----------------------------------------------------

    join_index = None

    if mid_day_agent is not None:

        join_index = len(packages) // 2

    # -----------------------------------------------------
    # Process packages
    # -----------------------------------------------------

    for index, package in enumerate(packages):

        # -------------------------------------------------
        # New agent joins halfway through the day
        # -------------------------------------------------

        if (
            mid_day_agent is not None
            and index == join_index
        ):

            new_agent_id = mid_day_agent["id"]
            new_agent_location = (
                mid_day_agent["location"]
            )

            if new_agent_id in current_agents:

                raise ValueError(
                    f"Agent {new_agent_id} already exists."
                )

            current_agents[new_agent_id] = (
                new_agent_location
            )

            total_distance[new_agent_id] = 0.0

            packages_delivered[new_agent_id] = 0

            total_delay[new_agent_id] = 0

            current_location[new_agent_id] = (
                new_agent_location[:]
            )

            route_history[new_agent_id] = []

            route_history[new_agent_id].append(
                {
                    "type": "join",
                    "location": new_agent_location[:]
                }
            )

            print(
                f"\n>>> New agent {new_agent_id} "
                f"joined mid-day at "
                f"{new_agent_location}"
            )

        # -------------------------------------------------
        # Package information
        # -------------------------------------------------

        package_id = package["id"]

        warehouse_id = package["warehouse"]

        destination = package["destination"]

        warehouse_location = warehouses[warehouse_id]

        # -------------------------------------------------
        # If the package has not been assigned because
        # a new agent joined, find the nearest current
        # agent.
        # -------------------------------------------------

        if package_id not in assignments:

            agent_id = find_nearest_agent(
                warehouse_location,
                current_agents,
                current_location
            )

        else:

            agent_id = assignments[package_id]

            # -------------------------------------------------
            # If assigned agent is not available anymore,
            # choose another agent.
            # -------------------------------------------------

            if agent_id not in current_agents:

                agent_id = find_nearest_agent(
                    warehouse_location,
                    current_agents,
                    current_location
                )

        # -------------------------------------------------
        # Agent -> Warehouse
        # -------------------------------------------------

        distance_to_warehouse = calculate_distance(
            current_location[agent_id],
            warehouse_location
        )

        # -------------------------------------------------
        # Warehouse -> Destination
        # -------------------------------------------------

        distance_to_destination = calculate_distance(
            warehouse_location,
            destination
        )

        delivery_distance = (
            distance_to_warehouse
            + distance_to_destination
        )

        total_distance[agent_id] += delivery_distance

        packages_delivered[agent_id] += 1

        # -------------------------------------------------
        # Random delay
        # -------------------------------------------------

        delay = 0

        if use_delays:

            delay = generate_random_delay()

            total_delay[agent_id] += delay

        # -------------------------------------------------
        # Store route
        # -------------------------------------------------

        route_history[agent_id].append(
            {
                "type": "warehouse",
                "package": package_id,
                "location": warehouse_location[:]
            }
        )

        route_history[agent_id].append(
            {
                "type": "destination",
                "package": package_id,
                "location": destination[:]
            }
        )

        # -------------------------------------------------
        # Agent is now at destination
        # -------------------------------------------------

        current_location[agent_id] = destination[:]

        print(
            f"{package_id} -> {agent_id} "
            f"| Distance: {delivery_distance:.2f}"
            f" | Delay: {delay} min"
        )

    return (
        total_distance,
        packages_delivered,
        total_delay,
        route_history
    )


# =========================================================
# GENERATE REPORT
# =========================================================

def generate_report(
    data,
    use_delays=False,
    mid_day_agent=None
):

    # -----------------------------------------------------
    # Initial assignment
    # -----------------------------------------------------

    assignments = assign_packages(data)

    # -----------------------------------------------------
    # Simulate
    # -----------------------------------------------------

    (
        total_distance,
        packages_delivered,
        total_delay,
        route_history
    ) = simulate_deliveries(
        data,
        assignments,
        use_delays,
        mid_day_agent
    )

    report = {}

    # -----------------------------------------------------
    # Generate report for each agent
    # -----------------------------------------------------

    for agent_id in total_distance:

        count = packages_delivered[agent_id]

        distance = total_distance[agent_id]

        delay = total_delay[agent_id]

        if count > 0:

            efficiency = distance / count

        else:

            efficiency = 0.0

        report[agent_id] = {
            "packages_delivered": count,
            "total_distance": round(
                distance,
                2
            ),
            "efficiency": round(
                efficiency,
                2
            )
        }

        # Add delay information only if enabled
        if use_delays:

            report[agent_id][
                "total_delay_minutes"
            ] = delay

    # -----------------------------------------------------
    # Find best agent
    # -----------------------------------------------------

    active_agents = []

    for agent_id in packages_delivered:

        if packages_delivered[agent_id] > 0:

            active_agents.append(agent_id)

    if len(active_agents) > 0:

        best_agent = min(
            active_agents,
            key=lambda agent_id:
                total_distance[agent_id]
                / packages_delivered[agent_id]
        )

    else:

        best_agent = None

    report["best_agent"] = best_agent

    return (
        report,
        assignments,
        route_history
    )


# =========================================================
# ASCII ROUTE VISUALIZATION
# =========================================================

def print_ascii_routes(
    data,
    route_history
):

    print("\n")
    print("=" * 60)
    print("ASCII ROUTE VISUALIZATION")
    print("=" * 60)

    for agent_id, routes in route_history.items():

        print(
            f"\nAgent {agent_id}"
        )

        print("-" * 40)

        if not routes:

            print("No route.")

            continue

        for index, point in enumerate(routes):

            location = point["location"]

            point_type = point["type"]

            if point_type == "start":

                print(
                    f"START       -> {location}"
                )

            elif point_type == "join":

                print(
                    f"JOIN        -> {location}"
                )

            elif point_type == "warehouse":

                print(
                    f"  |"
                )

                print(
                    f"  +-- {point['package']} "
                    f"WAREHOUSE -> {location}"
                )

            elif point_type == "destination":

                print(
                    f"  |"
                )

                print(
                    f"  +-- {point['package']} "
                    f"DESTINATION -> {location}"
                )

    print("\nRoute format:")
    print(
        "Agent -> Warehouse -> Destination -> "
        "Next Warehouse -> Next Destination"
    )


# =========================================================
# ASCII COORDINATE MAP
# =========================================================

def print_coordinate_map(
    data,
    route_history
):

    print("\n")
    print("=" * 60)
    print("ASCII COORDINATE MAP")
    print("=" * 60)

    all_points = []

    # Warehouses
    for warehouse_id, location in data[
        "warehouses"
    ].items():

        all_points.append(
            (
                location[0],
                location[1],
                warehouse_id
            )
        )

    # Agents
    for agent_id, location in data[
        "agents"
    ].items():

        all_points.append(
            (
                location[0],
                location[1],
                agent_id
            )
        )

    if len(all_points) == 0:

        print("No coordinates to display.")

        return

    min_x = min(
        point[0]
        for point in all_points
    )

    max_x = max(
        point[0]
        for point in all_points
    )

    min_y = min(
        point[1]
        for point in all_points
    )

    max_y = max(
        point[1]
        for point in all_points
    )

    width = 50
    height = 15

    grid = [
        [" " for _ in range(width)]
        for _ in range(height)
    ]

    # -----------------------------------------------------
    # Add warehouses
    # -----------------------------------------------------

    for warehouse_id, location in data[
        "warehouses"
    ].items():

        x = location[0]
        y = location[1]

        if max_x == min_x:

            grid_x = 0

        else:

            grid_x = int(
                (x - min_x)
                / (max_x - min_x)
                * (width - 1)
            )

        if max_y == min_y:

            grid_y = 0

        else:

            grid_y = int(
                (max_y - y)
                / (max_y - min_y)
                * (height - 1)
            )

        grid_y = max(
            0,
            min(height - 1, grid_y)
        )

        grid_x = max(
            0,
            min(width - 1, grid_x)
        )

        grid[grid_y][grid_x] = "W"

    # -----------------------------------------------------
    # Add agents
    # -----------------------------------------------------

    for agent_id, location in data[
        "agents"
    ].items():

        x = location[0]
        y = location[1]

        if max_x == min_x:

            grid_x = 0

        else:

            grid_x = int(
                (x - min_x)
                / (max_x - min_x)
                * (width - 1)
            )

        if max_y == min_y:

            grid_y = 0

        else:

            grid_y = int(
                (max_y - y)
                / (max_y - min_y)
                * (height - 1)
            )

        grid_y = max(
            0,
            min(height - 1, grid_y)
        )

        grid_x = max(
            0,
            min(width - 1, grid_x)
        )

        grid[grid_y][grid_x] = "A"

    # -----------------------------------------------------
    # Print map
    # -----------------------------------------------------

    for row in grid:

        print(
            "|" +
            "".join(row) +
            "|"
        )

    print(
        "+" +
        "-" * width +
        "+"
    )

    print("\nLegend:")
    print("W = Warehouse")
    print("A = Agent")


# =========================================================
# EXPORT TOP PERFORMER TO CSV
# =========================================================

def export_top_performer_csv(
    report,
    file_name="top_performer.csv"
):

    best_agent = report["best_agent"]

    if best_agent is None:

        print(
            "\nNo top performer because "
            "no packages were delivered."
        )

        return

    agent_data = report[best_agent]

    with open(
        file_name,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        # Header
        writer.writerow([
            "agent_id",
            "packages_delivered",
            "total_distance",
            "efficiency",
            "total_delay_minutes"
        ])

        # Data
        writer.writerow([
            best_agent,
            agent_data["packages_delivered"],
            agent_data["total_distance"],
            agent_data["efficiency"],
            agent_data.get(
                "total_delay_minutes",
                0
            )
        ])

    print(
        f"\nTop performer exported to "
        f"{file_name}"
    )


# =========================================================
# FILE SELECTION
# =========================================================

def get_file_name():

    print("\nAvailable options:")
    print("1. Base case")
    print("2. Test case 1-10")

    choice = input(
        "\nEnter your choice: "
    ).strip()

    if choice == "1":

        return "base_case.json"

    if choice == "2":

        test_number = input(
            "Enter test case number (1-10): "
        ).strip()

        if not test_number.isdigit():

            raise ValueError(
                "Test case number must be a number."
            )

        test_number = int(test_number)

        if test_number < 1 or test_number > 10:

            raise ValueError(
                "Test case number must be "
                "between 1 and 10."
            )

        return (
            f"test_case/test_case_"
            f"{test_number}.json"
        )

    raise ValueError(
        "Invalid choice."
    )


# =========================================================
# BONUS FEATURE MENU
# =========================================================

def get_bonus_options():

    print("\nBonus Features")

    print(
        "1. Random delivery delays"
    )

    print(
        "2. ASCII route visualization"
    )

    print(
        "3. New agent joining mid-day"
    )

    print(
        "4. Export top performer to CSV"
    )

    print(
        "5. Enable all bonus features"
    )

    print(
        "6. No bonus features"
    )

    choice = input(
        "\nEnter your choice: "
    ).strip()

    return choice


# =========================================================
# GET MID-DAY AGENT
# =========================================================

def get_mid_day_agent(data):

    print("\nNew Agent Information")

    agent_id = input(
        "Enter new agent ID: "
    ).strip()

    if not agent_id:

        raise ValueError(
            "Agent ID cannot be empty."
        )

    if agent_id in data["agents"]:

        raise ValueError(
            f"Agent {agent_id} already exists."
        )

    x = input(
        "Enter agent X coordinate: "
    ).strip()

    y = input(
        "Enter agent Y coordinate: "
    ).strip()

    try:

        x = float(x)
        y = float(y)

    except ValueError:

        raise ValueError(
            "Coordinates must be numbers."
        )

    return {
        "id": agent_id,
        "location": [x, y]
    }


# =========================================================
# MAIN
# =========================================================

def main():

    try:

        # -------------------------------------------------
        # Select file
        # -------------------------------------------------

        file_name = get_file_name()

        print(
            f"\nReading: {file_name}"
        )

        # -------------------------------------------------
        # Load JSON
        # -------------------------------------------------

        with open(
            file_name,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        # -------------------------------------------------
        # Normalize
        # -------------------------------------------------

        data = normalize_data(data)

        # -------------------------------------------------
        # Validate
        # -------------------------------------------------

        validate_data(data)

        print(
            "Input data validated successfully."
        )

        # -------------------------------------------------
        # Bonus options
        # -------------------------------------------------

        bonus_choice = get_bonus_options()

        use_delays = False
        use_ascii = False
        use_new_agent = False
        use_csv = False

        if bonus_choice == "1":

            use_delays = True

        elif bonus_choice == "2":

            use_ascii = True

        elif bonus_choice == "3":

            use_new_agent = True

        elif bonus_choice == "4":

            use_csv = True

        elif bonus_choice == "5":

            use_delays = True
            use_ascii = True
            use_new_agent = True
            use_csv = True

        elif bonus_choice == "6":

            pass

        else:

            raise ValueError(
                "Invalid bonus feature choice."
            )

        # -------------------------------------------------
        # New agent
        # -------------------------------------------------

        mid_day_agent = None

        if use_new_agent:

            mid_day_agent = get_mid_day_agent(
                data
            )

        # -------------------------------------------------
        # Generate report
        # -------------------------------------------------

        (
            report,
            assignments,
            route_history
        ) = generate_report(
            data,
            use_delays,
            mid_day_agent
        )

        # -------------------------------------------------
        # Package assignments
        # -------------------------------------------------

        print("\n")
        print("=" * 60)
        print("PACKAGE ASSIGNMENTS")
        print("=" * 60)

        for package_id, agent_id in assignments.items():

            print(
                f"{package_id} -> {agent_id}"
            )

        # -------------------------------------------------
        # Report
        # -------------------------------------------------

        print("\n")
        print("=" * 60)
        print("DELIVERY REPORT")
        print("=" * 60)

        for agent_id, details in report.items():

            if agent_id == "best_agent":
                continue

            print(
                f"\n{agent_id}"
            )

            print(
                f"  Packages delivered: "
                f"{details['packages_delivered']}"
            )

            print(
                f"  Total distance: "
                f"{details['total_distance']:.2f}"
            )

            print(
                f"  Efficiency: "
                f"{details['efficiency']:.2f}"
            )

            if use_delays:

                print(
                    f"  Total delay: "
                    f"{details['total_delay_minutes']} "
                    f"minutes"
                )

        print(
            f"\nBest Agent: "
            f"{report['best_agent']}"
        )

        # -------------------------------------------------
        # ASCII route
        # -------------------------------------------------

        if use_ascii:

            print_ascii_routes(
                data,
                route_history
            )

            print_coordinate_map(
                data,
                route_history
            )

        # -------------------------------------------------
        # Save JSON report
        # -------------------------------------------------

        report_file = (
            create_report_filename(
                file_name
            )
        )

        with open(
            report_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                report,
                file,
                indent=4
            )

        print(
            f"\nReport saved to: "
            f"{report_file}"
        )

        # -------------------------------------------------
        # Export CSV
        # -------------------------------------------------

        if use_csv:

            export_top_performer_csv(
                report
            )

    except FileNotFoundError as error:

        print(
            "\nError: File not found."
        )

        print(error)

    except json.JSONDecodeError:

        print(
            "\nError: Invalid JSON file."
        )

    except ValueError as error:

        print(
            f"\nInvalid input: {error}"
        )


# =========================================================
# CREATE REPORT FILE NAME
# =========================================================

def create_report_filename(file_name):

    base_name = os.path.basename(
        file_name
    )

    base_name = os.path.splitext(
        base_name
    )[0]

    return (
        f"{base_name}_report.json"
    )


# =========================================================
# PROGRAM START
# =========================================================

if __name__ == "__main__":

    main()