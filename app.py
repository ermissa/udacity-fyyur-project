# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from dotenv import load_dotenv
from flask_migrate import Migrate
from flask import abort
from extensions import migrate
from models import *

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

load_dotenv()
app = Flask(__name__)
moment = Moment(app)
app.config.from_object("config")
db.init_app(app)
migrate.init_app(app, db)


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#


def format_datetime(value, format="medium"):
    date = dateutil.parser.parse(value)
    if format == "full":
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == "medium":
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale="en")


app.jinja_env.filters["datetime"] = format_datetime

# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#


@app.route("/")
def index():
    return render_template("pages/home.html")


#  Venues
#  ----------------------------------------------------------------


@app.route("/venues")
def venues():
    venues = Venue.query.all()

    data = {}
    for venue in venues:
        # create a key for the city and state to group venues by city and state
        city_state_key = f"{venue.city},{venue.state}"
        if city_state_key not in data:
            # add key if it doesn't exist
            data[city_state_key] = {
                "city": venue.city,
                "state": venue.state,
                "venues": [],
            }

        num_upcoming_shows = len(
            Show.query.filter(
                Show.venue_id == venue.id, Show.start_time > datetime.now()
            ).all()
        )

        data[city_state_key]["venues"].append(
            {
                "id": venue.id,
                "name": venue.name,
                "num_upcoming_shows": num_upcoming_shows,
            }
        )

    # convert the dictionary values to a list
    data = list(data.values())
    return render_template("pages/venues.html", areas=data)


@app.route("/venues/search", methods=["POST"])
def search_venues():
    search_term = request.form.get("search_term", "")
    venues = Venue.query.filter(Venue.name.ilike(f"%{search_term}%")).all()

    response = {"count": len(venues), "data": []}

    for venue in venues:
        num_upcoming_shows = len(
            Show.query.filter(
                Show.venue_id == venue.id, Show.start_time > datetime.now()
            ).all()
        )
        response["data"].append(
            {
                "id": venue.id,
                "name": venue.name,
                "num_upcoming_shows": num_upcoming_shows,
            }
        )

    return render_template(
        "pages/search_venues.html", results=response, search_term=search_term
    )


@app.route("/venues/<int:venue_id>")
def show_venue(venue_id):
    venue = Venue.query.get(venue_id)
    if venue is None:
        return not_found_error("Venue not found.")

    past_shows = (
        Show.query.join(Artist)
        .filter(Show.venue_id == venue_id, Show.start_time < datetime.now())
        .all()
    )
    upcoming_shows = (
        Show.query.join(Artist)
        .filter(Show.venue_id == venue_id, Show.start_time >= datetime.now())
        .all()
    )

    # remove curly brace characters from genres string
    venue.genres = "".join(filter(lambda ch: ch not in "}{", venue.genres))

    data = {
        "id": venue.id,
        "name": venue.name,
        "genres": venue.genres.split(",") if venue.genres else [],
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        "phone": venue.phone,
        "website": venue.website_link,
        "facebook_link": venue.facebook_link,
        "seeking_talent": venue.seeking_talent,
        "seeking_description": venue.seeking_description,
        "image_link": venue.image_link,
        "past_shows": [
            {
                "artist_id": show.artist_id,
                "artist_name": show.artist.name,
                "artist_image_link": show.artist.image_link,
                "start_time": str(show.start_time),
            }
            for show in past_shows
        ],
        "upcoming_shows": [
            {
                "artist_id": show.artist_id,
                "artist_name": show.artist.name,
                "artist_image_link": show.artist.image_link,
                "start_time": str(show.start_time),
            }
            for show in upcoming_shows
        ],
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows),
    }

    return render_template("pages/show_venue.html", venue=data)


#  Create Venue
#  ----------------------------------------------------------------


@app.route("/venues/create", methods=["GET"])
def create_venue_form():
    form = VenueForm()
    return render_template("forms/new_venue.html", form=form)


@app.route("/venues/create", methods=["POST"])
def create_venue_submission():
    form = VenueForm(request.form)
    if form.validate():
        try:
            new_venue = Venue(
                name=form.name.data,
                city=form.city.data,
                state=form.state.data,
                address=form.address.data,
                phone=form.phone.data,
                genres=form.genres.data,
                image_link=form.image_link.data,
                facebook_link=form.facebook_link.data,
                website_link=form.website_link.data,
                seeking_talent=form.seeking_talent.data,
                seeking_description=form.seeking_description.data,
            )

            db.session.add(new_venue)
            db.session.commit()

            flash("Venue " + form.name.data + " was successfully listed!")
            return render_template("pages/home.html")
        except Exception as e:
            flash(
                f"An error occurred. Venue {form.name.data} could not be listed. Error: {str(e)}",
                "error",
            )
            db.session.rollback()
            return render_template("pages/home.html")
        finally:
            db.session.close()

    flash("Invalid data submitted. Please check the form for errors.", "error")
    return render_template("pages/home.html")


@app.route("/venues/<venue_id>", methods=["DELETE"])
def delete_venue(venue_id):
    try:
        if venue_id is None or venue_id == "":
            flash("Venue ID is required for deletion.")
            return redirect(url_for("venues"))

        venue = Venue.query.get(venue_id)
        if venue:
            db.session.delete(venue)
            db.session.commit()
            db.session.close()
            flash("Venue successfully deleted!")
            return redirect(url_for("venues"))
        else:
            flash("Venue not found. Deletion failed.")
            return redirect(url_for("venues"))
    except Exception as e:
        db.session.rollback()
        db.session.close()
        flash(f"An error occurred: {str(e)}")
        return redirect(url_for("venues"))


#  Artists
#  ----------------------------------------------------------------
@app.route("/artists")
def artists():
    data = []
    try:
        artists = Artist.query.all()
        data = [
            {
                "id": artist.id,
                "name": artist.name,
            }
            for artist in artists
        ]

    except Exception as e:
        flash(f"An error occurred: {str(e)}")
    return render_template("pages/artists.html", artists=data)


@app.route("/artists/search", methods=["POST"])
def search_artists():
    response = {"count": 0, "data": []}
    try:
        search_term = request.form.get("search_term", "")
        artists = Artist.query.filter(Artist.name.ilike(f"%{search_term}%")).all()
        response = {"count": len(artists), "data": []}

        for artist in artists:
            num_upcoming_shows = len(
                Show.query.filter(
                    Show.artist_id == artist.id, Show.start_time > datetime.now()
                ).all()
            )
            response["data"].append(
                {
                    "id": artist.id,
                    "name": artist.name,
                    "num_upcoming_shows": num_upcoming_shows,
                }
            )
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    return render_template(
        "pages/search_artists.html", results=response, search_term=search_term
    )


@app.route("/artists/<int:artist_id>")
def show_artist(artist_id):
    data = {}
    try:
        artist = Artist.query.get(artist_id)

        past_shows = (
            Show.query.join(Venue)
            .filter(Show.artist_id == artist_id, Show.start_time < datetime.now())
            .all()
        )

        upcoming_shows = (
            Show.query.join(Venue)
            .filter(Show.artist_id == artist_id, Show.start_time >= datetime.now())
            .all()
        )

        artist.genres = "".join(filter(lambda ch: ch not in "}{", artist.genres))

        data = {
            "id": artist.id,
            "name": artist.name,
            "genres": artist.genres.split(",") if artist.genres else [],
            "city": artist.city,
            "state": artist.state,
            "phone": artist.phone,
            "website": artist.website_link,
            "facebook_link": artist.facebook_link,
            "seeking_venue": artist.seeking_venue,
            "seeking_description": artist.seeking_description,
            "image_link": artist.image_link,
            "past_shows": [
                {
                    "venue_id": show.venue.id,
                    "venue_name": show.venue.name,
                    "venue_image_link": show.venue.image_link,
                    "start_time": str(show.start_time),
                }
                for show in past_shows
            ],
            "upcoming_shows": [
                {
                    "venue_id": show.venue.id,
                    "venue_name": show.venue.name,
                    "venue_image_link": show.venue.image_link,
                    "start_time": str(show.start_time),
                }
                for show in upcoming_shows
            ],
            "past_shows_count": len(past_shows),
            "upcoming_shows_count": len(upcoming_shows),
        }

    except Exception as e:
        flash(f"An error occurred: {str(e)}")

    return render_template("pages/show_artist.html", artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route("/artists/<int:artist_id>/edit", methods=["GET"])
def edit_artist(artist_id):
    form = ArtistForm()
    try:
        artist = Artist.query.get(artist_id)
        form = ArtistForm(obj=artist)
    except Exception as e:
        flash(f"An error occurred: {str(e)}")
    return render_template("forms/edit_artist.html", form=form, artist=artist)


@app.route("/artists/<int:artist_id>/edit", methods=["POST"])
def edit_artist_submission(artist_id):
    form = ArtistForm(request.form)
    try:
        artist = Artist.query.get(artist_id)
        form.populate_obj(artist)
        db.session.commit()
        flash("Artist " + artist.name + " was successfully updated!")
    except Exception as e:
        flash(f"An error occurred: {str(e)}")

    return redirect(url_for("show_artist", artist_id=artist_id))


@app.route("/venues/<int:venue_id>/edit", methods=["GET"])
def edit_venue(venue_id):
    form = VenueForm()
    try:
        venue = Venue.query.get(venue_id)
        form = VenueForm(obj=venue)
    except Exception as e:
        flash(f"An error occurred: {str(e)}")
    return render_template("forms/edit_venue.html", form=form, venue=venue)


@app.route("/venues/<int:venue_id>/edit", methods=["POST"])
def edit_venue_submission(venue_id):
    form = VenueForm(request.form)
    try:
        venue = Venue.query.get(venue_id)
        form.populate_obj(venue)
        db.session.commit()
        flash("Venue " + venue.name + " was successfully updated!")
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred: {str(e)}")
    finally:
        db.session.close()

    return redirect(url_for("show_venue", venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------


@app.route("/artists/create", methods=["GET"])
def create_artist_form():
    form = ArtistForm()
    return render_template("forms/new_artist.html", form=form)


@app.route("/artists/create", methods=["POST"])
def create_artist_submission():
    form = ArtistForm(request.form)
    if form.validate():
        try:
            new_artist = Artist(
                name=form.name.data,
                city=form.city.data,
                state=form.state.data,
                phone=form.phone.data,
                genres=form.genres.data,
                image_link=form.image_link.data,
                facebook_link=form.facebook_link.data,
                website_link=form.website_link.data,
                seeking_venue=form.seeking_venue.data,
                seeking_description=form.seeking_description.data,
            )

            db.session.add(new_artist)
            db.session.commit()
            flash("Artist " + form.name.data + " was successfully listed!")
            return render_template("pages/home.html")
        except Exception as e:
            flash(
                f"An error occurred. Artist {form.name.data} could not be listed. Error: {str(e)}",
                "error",
            )
            db.session.rollback()
        finally:
            db.session.close()
    else:
        flash("Invalid data submitted. Please check the form for errors.", "error")

    return render_template("pages/home.html")


#  Shows
#  ----------------------------------------------------------------


@app.route("/shows")
def shows():
    data = []
    try:
        shows = (
            Show.query.join(Artist, Show.artist_id == Artist.id)
            .join(Venue, Show.venue_id == Venue.id)
            .all()
        )

        data = [
            {
                "venue_id": show.venue_id,
                "venue_name": show.venue.name,
                "artist_id": show.artist_id,
                "artist_name": show.artist.name,
                "artist_image_link": show.artist.image_link,
                "start_time": str(show.start_time),
            }
            for show in shows
        ]

    except Exception as e:
        print(f"An error occurred: {str(e)}")

    return render_template("pages/shows.html", shows=data)


@app.route("/shows/create")
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template("forms/new_show.html", form=form)


@app.route("/shows/create", methods=["POST"])
def create_show_submission():
    form = ShowForm(request.form)

    try:
        if form.validate():
            artist_id = form.artist_id.data
            venue_id = form.venue_id.data
            start_time = form.start_time.data

            new_show = Show(
                artist_id=artist_id, venue_id=venue_id, start_time=start_time
            )

            db.session.add(new_show)
            db.session.commit()
            flash("Show was successfully listed!")
            return render_template("pages/home.html")
        else:
            flash(
                "An error occurred. Show could not be listed. Please check your form data."
            )
            return render_template("pages/home.html")

    except Exception as e:
        db.session.rollback()
        flash("An error occurred. Show could not be listed.")
        return render_template("pages/home.html")
    finally:
        db.session.close()


@app.errorhandler(404)
def not_found_error(error):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def server_error(error):
    return render_template("errors/500.html"), 500


if not app.debug:
    file_handler = FileHandler("error.log")
    file_handler.setFormatter(
        Formatter("%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]")
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info("errors")

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == "__main__":
    app.run()

# Or specify port manually:
"""
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
"""
