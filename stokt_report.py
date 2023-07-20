import json
import requests
from copy import copy
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import tqdm
import argparse
import os

def route_similarity_metric(r1, r2):
    r1_holds = [hold["id"] for hold in r1["normalizedHolds"]]
    r2_holds = [hold["id"] for hold in r2["normalizedHolds"]]
    # count ids not in common
    assert len(set(r1_holds) ^ set(r2_holds)) == len(set(r2_holds) ^ set(r1_holds))
    return len(set(r1_holds) ^ set(r2_holds))


def routeid2route(routes, id):
    for route in routes:
        if route["id"] == id:
            return route


def download(cookie_string, authorization, faceid):
    print("Downloading routes for face", faceid)

    url = f"https://www.sostokt.com/api/faces/{faceid}/latest-climbs/paginated?grade_from=V0&grade_to=%3F&ordering=most_recent&tags=&search=&exclude_mine=false&show_circuit_only=false"
    user_agent = "Stkt/5 CFNetwork/1408.0.4 Darwin/22.5.0"
    headers = {
        "Cookie": cookie_string,
        "Authorization": authorization,
        "User-Agent": user_agent
    }

    data = []  # List to store the downloaded data

    page = 1
    page_url = url

    while page_url:
        response = requests.get(page_url, headers=headers)
        if response.status_code == 200:
            page_data = response.json()
            data.append(page_data)

            page_url = page_data.get("next", False)  # Adjust this based on your JSON structure
            page += 1
        else:
            print("Failed to download data. Status code:", response.status_code)
            break

    # concatenate all route data together.
    routes = []
    for page in data:
        for route in page["results"]:
            routes.append(route)

    with open("routes.json", "w") as fh:
        fh.write(json.dumps(routes))

    print("Downloading wall data for face ", faceid)

    response = requests.get(f"https://www.sostokt.com/api/faces/{faceid}/setup", headers=headers)
    if response.status_code != 200:
        raise Exception("Failed to download wall config. Status code:", response.status_code)
    with open("wall_config.json", "w") as fh:
        fh.write(json.dumps(response.json()))

    print("Downloading image for face ", faceid)
    with open("wall.jpg", "wb") as fh:
        response = requests.get("https://www.sostokt.com/media/" + response.json()["picture"]["name"])
        if response.status_code != 200:
            raise Exception("Failed to download wall image. Status code:", response.status_code)
        fh.write(response.content)


def normalize():
    routes = json.load(open("routes.json", "r"))

    # NOTE: to get wall config, unselect the  gym then reselct the gym while mitmproxy.
    # should look somethign like https://www.sostokt.com/api/faces/2b9954be-ca1b-442d-a92b-40b488f56027/setup
    # save the image from img = requests.get("https://sostokt.com/media/" + wall_config["picture"]["name"])
    wall_config = json.load(open("wall_config.json", "r"))
    # img_width = wall_config["picture"]["width"]
    # img_height = wall_config["picture"]["height"]

    # hold ids -> holds.
    wall_holds = dict()
    for hold in wall_config["holds"]:
        wall_holds[hold["id"]] = hold

    for route in routes:
        # get route holds from IDs.
        # In the route holds list, the first character is the hold type (start, foot, etc.), and the rest is the hold id
        # as found in the wall config.
        # We need to get the route holds from the wall_holds.
        route_hold_ids = [( hold[0] , int(hold[1:]) )
                 for hold in
                 route["holdsList"].split(" ")
        ]
        route_holds = []
        for hold_id in route_hold_ids:
            hold_type = hold_id[0]
            hold_num_id = hold_id[1]
            hold = copy(wall_holds[hold_num_id])
            hold["type"] = hold_type
            route_holds.append(hold)

        route["normalizedHolds"] = route_holds
        # print(route.keys())
        # print(route["crowdGrade"]["hueco"])
        # draw_polygons("wall.jpg", route_holds)

    open("routes_normalized.json", "w").write(json.dumps(routes, indent=4))

def type2color(hold_type):
    if hold_type == "F":  # feet only
        return 'blue'
    if hold_type == "T":  # top/finish hold
        return 'red'
    elif hold_type == 'O':  # on.
        return 'black'
    elif hold_type == 'S':  # start.
        return 'green'
    else:
        raise Exception("idk what this hold type is: " + hold_type)


def draw_polygons(background_image_path, holds, title="", save_loc=None):
    # Load the background image
    dpi = 100
    image = plt.imread(background_image_path)
    height, width, depth = image.shape
    figsize = width / float(dpi), height / float(dpi)

    fig = plt.figure(figsize=figsize)
    ax = fig.add_axes([0, 0, 1, 1])

    # add title.
    ax.set_title(title, fontsize=72)

    # Display the image
    ax.imshow(image, alpha=0.8)

    # Create a polygon patch
    for hold in holds:
        polygon_coordinates = [list(map(float, point.split(","))) for point in hold["polygonStr"].split()]
        if "type" not in hold.keys():
            hold["type"] = "O"
        polygon_patch = patches.Polygon(polygon_coordinates, linewidth=7, edgecolor=type2color(hold["type"]),
                                        facecolor='none')

        # Add the polygon patch to the axis
        ax.add_patch(polygon_patch)

    # Set the aspect ratio of the axis to match the image
    ax.set_aspect('equal')
    plt.axis('off')

    # Show the plot
    if save_loc is None:
        plt.show()
    else:
        plt.savefig(save_loc, bbox_inches='tight')
    plt.close()


# endregion

def most_popular_hold_ids(routes):
    hold_counts = dict()
    for route in routes:
        for hold in route["normalizedHolds"]:
            hold_id = hold["id"]
            if hold_id not in hold_counts:
                hold_counts[hold_id] = 0
            hold_counts[hold_id] += 1
    return sorted(hold_counts.keys(), key=lambda x: hold_counts[x], reverse=True)



if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--cookie", type=str, required=True)
    arg_parser.add_argument("--auth", type=str, required=True)
    arg_parser.add_argument("--faceid", type=str, required=True)
    arg_parser.add_argument("--skip_download", action="store_true", default=False)
    args = arg_parser.parse_args()

    with open("report.html", "r") as report_fh:
        assert "Similarity" not in report_fh.read(), "clear out route similarity line in report.html before proceeding."

    if not args.skip_download:
        download(args.cookie, args.auth, args.faceid)
    normalize()

    routes = json.load(open("routes_normalized.json", "r"))
    wall_config = json.load(open("wall_config.json", "r"))
    wall_holds = dict()
    for hold in wall_config["holds"]:
        wall_holds[hold["id"]] = hold


    most_popular_hold = [most_popular_hold_ids(routes)[0]]
    draw_polygons("wall.jpg",
                  [wall_holds[hold_id] for hold_id in most_popular_hold],
                  title="Most Popular Hold",
                  save_loc="most_popular_hold.jpg")

    ten_most_popular_holds = most_popular_hold_ids(routes)[:5]
    draw_polygons("wall.jpg",
                  [wall_holds[hold_id] for hold_id in ten_most_popular_holds],
                  title="Five most Popular Holds",
                  save_loc="five_most_popular_holds.jpg")

    ten_most_popular_holds = most_popular_hold_ids(routes)[:10]
    draw_polygons("wall.jpg",
                  [wall_holds[hold_id] for hold_id in ten_most_popular_holds],
                  title="Ten Most Popular Holds",
                  save_loc="ten_most_popular_holds.jpg")

    for grade in ["V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9", "V10", "V11", "V12", "V13", "V14", "V15", "V16", "V17", "V18", "V19", "V20"]:
        grade_routes = [route for route in routes if route["crowdGrade"]["hueco"] == grade]
        if len(grade_routes) == 0:
            continue
        print(grade)
        grade_holds = most_popular_hold_ids(grade_routes)[:10]
        draw_polygons("wall.jpg",
                      [wall_holds[hold_id] for hold_id in grade_holds],
                      title="Ten Most Popular Holds for Grade " + grade,
                      save_loc="ten_most_popular_holds_for_grade_" + grade + ".jpg")

    # unused holds.
    all_hold_ids_on_all_routes = []
    for route in routes:
        for hold in route["normalizedHolds"]:
            all_hold_ids_on_all_routes.append(hold["id"])
    unused_hold_ids = [hold_id for hold_id in wall_holds.keys() if hold_id not in all_hold_ids_on_all_routes]
    print("unused holds: ", unused_hold_ids)
    draw_polygons("wall.jpg",
                  [wall_holds[hold_id] for hold_id in unused_hold_ids],
                  title="Unused Holds",
                  save_loc="unused_holds.jpg")

    holds_used_exactly_once = [hold_id for hold_id in all_hold_ids_on_all_routes if
                               all_hold_ids_on_all_routes.count(hold_id) == 1]
    print("holds used exactly once: ", holds_used_exactly_once)
    draw_polygons("wall.jpg",
                  [wall_holds[hold_id] for hold_id in holds_used_exactly_once],
                  title="Holds Used Exactly Once",
                  save_loc="holds_used_exactly_once.jpg")


    # for each route, find the routes that are closest in terms of hold inclusion.
    for route in routes:
        route_similarity = dict()
        for other_route in routes:
            if other_route["id"] == route["id"]:
                continue
            distance = route_similarity_metric(route, other_route)
            route_similarity[other_route["id"]] = distance
            route["route_similarity"] = sorted(route_similarity.keys(), key=lambda x: route_similarity[x])

    # for each route, print the name of the route and the name of the most similar route.
    # hacky gross slow
    messages = []
    already_processed = []
    for route in routes:
        if route["id"] in already_processed:
            continue
        most_similar_id = route["route_similarity"][0]
        most_similar = routeid2route(routes, most_similar_id)
        if most_similar["route_similarity"][0] == route["id"]:
            already_processed.append(most_similar_id)
        messages.append([
            route_similarity_metric(route, most_similar),
            f"{route['name']} ({route['crowdGrade']['hueco']}) is most hold-similar to {most_similar['name']} ({most_similar['crowdGrade']['hueco']}) with hold-inclusion distance {route_similarity_metric(route, most_similar)}"
        ])
    messages = sorted(messages, key=lambda x: x[0])

    original_contents = open("report.html", "r").read()
    original_contents += "<h2>Route Similarity</h2><ul>"
    for message in messages:
        original_contents += f"<li>{message[1]}</li>"
    original_contents += "</ul></body></html>"

    with open("report.html", "w") as f:
        f.write(original_contents)


    input("Generate pictures of all routes? If not, ctrl-c now.")
    # hacky gross not safe.
    try:
        os.mkdir("all_routes")
    except FileExistsError:
        pass
    for route in tqdm.tqdm(routes):
        print(route["name"])
        safe_name = route["name"].replace("/", "-").replace("$", "-")
        # check if file exists.
        try:
            open(f"all_routes/{safe_name}.jpg", "r")
            continue
        except FileNotFoundError:
            try:
                draw_polygons("wall.jpg", route["normalizedHolds"], route["name"], f"all_routes/{safe_name}.jpg")
            except Exception:
                draw_polygons("wall.jpg", route["normalizedHolds"], route["name"], f"all_routes/{route['id']}.jpg")
        except Exception:
            draw_polygons("wall.jpg", route["normalizedHolds"], route["name"], f"all_routes/{route['id']}.jpg")
