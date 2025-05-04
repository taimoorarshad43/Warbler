import os

from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, LoginForm, MessageForm, UserEditForm
from models import db, connect_db, User, Message, Follows

CURR_USER_KEY = "curr_user"

# Refactoring to use application factory pattern
def create_app():

    app = Flask(__name__)
    connect_db(app)

    return app

app = create_app()

# Database URI is set in models.py as per Flask 3's specifications

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
toolbar = DebugToolbarExtension(app)


##############################################################################
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""

    # IMPLEMENT THIS - DONE

    do_logout()

    flash("You have successfully logged out.", "success")
    return redirect("/login")


##############################################################################
# General user routes:

@app.route('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.route('/users/<int:user_id>')
def users_show(user_id):
    """Show user profile."""

    user = User.query.get_or_404(user_id)

    # snagging messages in order from the database;
    # user.messages won't be in order by default
    messages = (Message
                .query
                .filter(Message.user_id == user_id)
                .order_by(Message.timestamp.desc())
                .limit(100)
                .all())
    return render_template('users/show.html', user=user, messages=messages)


@app.route('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/following.html', user=user)


@app.route('/users/<int:user_id>/followers')
def users_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/followers.html', user=user)


@app.route('/users/follow/<int:follow_id>', methods=['POST'])
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/stop-following/<int:follow_id>', methods=['POST'])
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/add_like/<int:message_id>', methods=['POST'])
def add_like(message_id):
    """Have currently-logged-in-user like this message.
    
    If message is already liked, remove the like."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    liked_message = Message.query.get_or_404(message_id)

    if liked_message in g.user.likes:            # Check if the message is already liked
        g.user.likes.remove(liked_message)       # If it is, remove the like. Else add the like
    else:
        g.user.likes.append(liked_message)

    db.session.commit()
    return redirect("/")

@app.route('/users/profile', methods=["GET", "POST"])
def profile():
    """Update profile for current user. Will check to see if user has the correct password"""

    # IMPLEMENT THIS - DONE

    if not g.user:                              # If user is not logged in, redirect to login page
        flash("Access unauthorized.", "danger")
        return redirect("/")

    usereditform = UserEditForm()

    password = usereditform.password.data
    username = usereditform.username.data
    email = usereditform.email.data
    image_url = usereditform.image_url.data
    header_image_url = usereditform.header_image_url.data
    bio = usereditform.bio.data

    user = User.query.get(g.user.id)         # Get the current user from the database
    authusername = user.username

    if usereditform.validate_on_submit():       # Handles our POST requests when form is submitted and checks user password

        validuser = User.authenticate(authusername,
                                 password)
        if not validuser:
            flash("Invalid credentials.", 'danger')
            return redirect("/")
        
        # This needs to be changed to have optional fields for image_url fields - DONE

        user.username = username
        user.email = email
        user.image_url = image_url or User.image_url.default.arg
        user.header_image_url = header_image_url
        user.bio = bio

        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(f"/users/{user.id}")
    else:
        return render_template('users/edit.html', form=usereditform, user=user)



@app.route('/users/delete', methods=["POST"])
def delete_user():
    """Delete user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout()

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/signup")


##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["GET", "POST"])
def messages_add():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/new.html', form=form)


@app.route('/messages/<int:message_id>', methods=["GET"])
def messages_show(message_id):
    """Show a message."""

    msg = Message.query.get(message_id)
    return render_template('messages/show.html', message=msg)


@app.route('/messages/<int:message_id>/delete', methods=["POST"])
def messages_destroy(message_id):
    """Delete a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = Message.query.get(message_id)
    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")


##############################################################################
# Homepage and error pages


@app.route('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users

    Also takes in likes
    """

    if g.user:
        # messages = (Message
        #             .query
        #             .order_by(Message.timestamp.desc())
        #             .limit(100)
        #             .all())

        messages = (
            Message
            .query
            .join(
                Follows,
                Follows.user_being_followed_id == Message.user_id
            )
            .filter(Follows.user_following_id == g.user.id)
            .order_by(Message.timestamp.desc())
            .limit(100)
            .all())

        likes = (g.user.likes)                      # Get the likes of the current user

        likes = [like.id for like in likes]        # Get the ids of the likes

        for like in likes:
            print("Like ID: ", like)

        for message in messages:
            if message.id in likes:
                print("Message ID: ", message.id)
            else:
                print("Message ID: ", message.id, "not in likes")
            

        return render_template('home.html', messages=messages, likes = likes)

    else:
        return render_template('home-anon.html')


##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@app.after_request
def add_header(req):
    """Add non-caching headers on every request."""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers['Cache-Control'] = 'public, max-age=0'
    return req
