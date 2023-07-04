import folium
import polyline
import math
import pandas as pd
import joblib
import streamlit as st

import utils.map_utils as map_utils

from streamlit_folium import st_folium
from datetime import datetime, timedelta

hdb = pd.read_csv("./data/rental_with_engineered_features.csv")
std_dev = hdb['monthly_rent'].describe()["std"]

LAT_START = 1.3521
LONG_START = 103.8198
ZOOM_START = 10
RADIUS = 1000  # Set radius of the neighbours

if "center" not in st.session_state:
    st.session_state["lat"] = LAT_START
    st.session_state["long"] = LONG_START
    st.session_state["center"] = [LAT_START, LONG_START]
if "zoom" not in st.session_state:
    st.session_state["zoom"] = ZOOM_START
if "markers" not in st.session_state:
    st.session_state["markers"] = []

FLAT_TYPE = ["1-ROOM", "2-ROOM", "3-ROOM", "4-ROOM", "5-ROOM", "EXECUTIVE"]
RENTAL_DATE = {"Immediate": 0, "3 Months": 3, "6 Months": 6}


def get_prediction_input(lat: float, long: float, flat_type: int, future_rental_date: int) -> dict:
    
    distance_to_station, _, _, _ = map_utils.get_nearest_facility(lat, long, "stations")
    distance_to_hawker, _, _, _ = map_utils.get_nearest_facility(lat, long, 
                                                                 "hawker_centres_markets")
    distance_to_mall, _, _, _ = map_utils.get_nearest_facility(lat, long, "shopping_malls")
    distance_to_cbd = map_utils.calculate_distance_to_cbd(lat, long)

    # Get the current date
    current_date = datetime.now()

    # Add 'future_rental_date' months to the current date
    future_date = current_date + timedelta(days=(future_rental_date * 30))

    data_start_date = datetime.strptime('2021-01', '%Y-%m')
    months_difference = (future_date.year - data_start_date.year) * 12 \
        + (future_date.month - data_start_date.month)

    data = {
        "rent_approval_date":[months_difference],
        "flat_type":[flat_type],
        "lat":[lat],
        "lon":[long],
        "min_geodisic_distance_to_station":[distance_to_station],
        "min_geodisic_distance_to_hawker_market":[distance_to_hawker],
        "min_geodisic_distance_to_shopping_mall":[distance_to_mall],
        "geodesic_distance_to_cbd":[distance_to_cbd],
    }
    print(data)
    input_df = pd.DataFrame(data)

    return input_df


def address_updated():
    """
    Callback function that streamlit calls when user enters an address
    at the input field and currently only does the following:
    1. zooms the map in
    2. displays a marker at the rental location
    3. centers map at the rental location
    """
    TOKEN = st.secrets["token"]
    st.session_state["markers"] = []
    address = st.session_state["address"]
    flat_type = st.session_state["flat"]

    (
        latrental,
        longrental,
        postal,
        address,
        buildingname,
    ) = map_utils.get_address_details(address)

    # dynamically update marker on map
    # folium.Marker(location=(lat, long), popup=samplepopup).add_to(mapfolium)

    # Add the circle of the radius
    neighbour_radius = folium.Circle(
        location=[latrental, longrental], radius=RADIUS, color="navy", fill=True
    )
    st.session_state["markers"].append(neighbour_radius)

    # Add list of facilities
    # Colours: 'white', 'orange', 'blue', 'lightred', 'darkpurple', 'darkred', 'purple',
    # 'black', 'lightgray', 'beige', 'lightblue', 'pink', 'green', 'gray', 'cadetblue',
    # 'darkgreen', 'red', 'darkblue', 'lightgreen'
    facility_icon = {
        "stations": {"icon": "subway", "colour": "darkblue"},
        "shopping_malls": {"icon": "shopping-bag", "colour": "black"},
        "hawker_centres_markets": {"icon": "cutlery", "colour": "orange"},
        "schools": {"icon": "book", "colour": "purple"},
    }
    for facility in ["stations", "shopping_malls", "hawker_centres_markets", "schools"]:
        # Add markers to the map for nearest train station
        _, facloc, faclat, faclong = map_utils.get_nearest_facility(
            latrental, longrental, facility
        )
        # print(facloc)

        facicon = folium.Icon(
            icon=facility_icon[facility]["icon"],
            prefix="fa",
            color=facility_icon[facility]["colour"],
        )
        facpopup = folium.Popup(f"{facloc}<br>", max_width=len(facloc) * 10)
        facmarker = folium.Marker(
            location=(faclat, faclong), icon=facicon, popup=facpopup
        )

        st.session_state["markers"].append(facmarker)

        # Add polyline from house to nearest facility
        # facsecs in the time to walk to facility, in seconds.
        # Divide by 60 to get minutes.
        facsecs, facdist, encoded_polyline = map_utils.getwalkingdetails(
            str(latrental) + "," + str(longrental),
            str(faclat) + "," + str(faclong),
            TOKEN,
        )
        facpath = polyline.decode(encoded_polyline)
        facpathpopup = folium.Popup(
            f"{facloc}<br>Total Walking Distance: <b>{facdist}m</b><br> ETA: {math.ceil(facsecs)}mins",
            max_width=len(facloc) * 10,
        )

        newline = folium.PolyLine(
            facpath,
            color=facility_icon[facility]["colour"],
            weight=10,
            opacity=0.8,
            popup=facpathpopup,
        )

        st.session_state["markers"].append(newline)

    # append rental house last, so it appears 'topmost' in case of overlaps
    rentalpopup = folium.Popup(
        f"{address}<br>"
        f"{buildingname}<br>"
        f"SINGAPORE {postal}<br>"
        f"Type: {flat_type}<br>",
        max_width=len(address) * 10,
    )

    rentalicon = folium.Icon(icon="home", prefix="fa", color="blue")
    rental_marker = folium.Marker(
        location=[latrental, longrental], popup=rentalpopup, icon=rentalicon
    )

    st.session_state["markers"].append(rental_marker)

    # dynamically center map on the added marker
    st.session_state["center"] = [latrental, longrental]
    st.session_state["lat"] = latrental
    st.session_state["long"] = longrental

    # dynamically zoom in map
    st.session_state["zoom"] = 15

    # print("update address:", st.session_state["lat"], st.session_state["long"], postal)



model = joblib.load("./model/finalized_model.pkl")

st.set_page_config(layout="wide")

st.title("HDB Rental Advisor")

col_left, col_right = st.columns([1, 2])

with col_left:
    st.text_input(
        "Enter your address or postal code", on_change=address_updated, key="address"
    )

    flat_option = st.selectbox(
        "What is your flat type?", FLAT_TYPE, index=2, key="flat"
    )

    rental_date_option = st.selectbox(
        "When does your new rental period start?",
        RENTAL_DATE.keys(),
        index=0,
        key="rentaldate",
    )

    if st.button("Get advice"):
        with st.spinner('Retrieving rental data...'):
            flat_type = FLAT_TYPE.index(flat_option)
            print(rental_date_option)
            rental_approval_date = RENTAL_DATE[rental_date_option]
            inference_input = get_prediction_input(st.session_state["lat"],
                                                st.session_state["long"],
                                                flat_type,
                                                rental_approval_date)
            print(rental_approval_date)
            curr_pred_result = model.predict(inference_input)

            # print(hdb.head(3))
            neighbours = map_utils.find_neighbours(
                (st.session_state["lat"], st.session_state["long"]),
                flat_option, RADIUS, hdb
            )

            # print(neighbours.head(3))
            for nblat, nblong, nbrental, nbloc, nbflat, nbdate in neighbours[
                [
                    "lat",
                    "lon",
                    "monthly_rent",
                    "address",
                    "flat_type",
                    "rent_approval_date",
                ]
            ].values:
                nbpopup = folium.Popup(
                    f"{nbloc}<br>"
                    f"Type: {nbflat}<br>"
                    f"Lease Start: {nbdate}<br>"
                    f"Monthly Rental: <b>{nbrental}</b>",
                    max_width=len(nbloc) * 10,
                )

                # print(nbpopup)
                if nbrental > curr_pred_result:
                    nbicon = folium.Icon(icon="user", prefix="fa", color="red")
                else:
                    nbicon = folium.Icon(icon="user", prefix="fa", color="green")
                # , icon=nbicon
                nbmarker = folium.Marker(
                    location=(nblat, nblong), popup=nbpopup, icon=nbicon
                )

                # Using insert to place the neighbourhood rentals before the
                # input house, displays the markers in order
                st.session_state["markers"].insert(0, nbmarker)

        pred_rental_price = curr_pred_result[0]
        lb_rental_price = pred_rental_price - std_dev
        ub_rental_price = pred_rental_price + std_dev
        if rental_approval_date == 0:
            st.write(f"The property at your given location has a predicted rental of "
                    f"\${lb_rental_price:.0f} - \${ub_rental_price:.0f} now")
        else:
            st.write(f"The property at your given location has a predicted rental of "
                    f"\${lb_rental_price:.0f} - \${ub_rental_price:.0f} in {rental_approval_date} months time")

# Map column
with col_right:
    sg_map = folium.Map(location=st.session_state["center"], zoom_start=ZOOM_START)
    marker_group = folium.FeatureGroup(name="Markers")
    for marker in st.session_state["markers"]:
        marker_group.add_child(marker)

    # call to render Folium map in Streamlit
    st_folium(
        sg_map,
        center=st.session_state["center"],
        zoom=st.session_state["zoom"],
        feature_group_to_add=marker_group,
        height=500,
        width=800,
        returned_objects=[],
    )

st.info("Disclaimer: this app is meant as proof of concept only, \
    and not for any actual real world prediction of property rentals")


