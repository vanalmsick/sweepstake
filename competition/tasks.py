# -*- coding: utf-8 -*-
import os
import datetime
import time
from django.core.mail import EmailMultiAlternatives, get_connection
from django.db.models import Min, Q
from sweepstake.celery import app
from django.conf import settings

from .api_football_scores import get_api_match_data, get_api_match_ids
from competition.models import Match
from general.models import EmailTemplates, CustomUser


def __get_email_template(template_name):
    email_obj = EmailTemplates.objects.filter(name=template_name)

    if settings.DEBUG or len(email_obj) == 0:
        with open(os.path.join("templates", "emails", f"{template_name}.html"), "r") as file:
            email_body = file.read()
        email_subject = template_name

        # add template if does not exist
        if len(email_obj) == 0:
            email_obj = EmailTemplates(name=template_name, html=email_body)
            email_obj.save()

    else:
        email_obj = email_obj.first()
        email_subject = email_obj.email_subject
        email_body = email_obj.html

    return email_subject, email_body


def update_api_match_ids(override_data=False):
    match_id_data = get_api_match_ids(season_year="2024")
    for match in match_id_data:
        match_search = Match.objects.filter(match_time=match["fixture"]["date"])
        if len(match_search) > 1:
            match_search = match_search.filter(
                Q(team_a__name__icontains=match["teams"]["home"]["name"])
                | Q(team_a__name__icontains=match["teams"]["away"]["name"])
                | Q(team_b__name__icontains=match["teams"]["home"]["name"])
                | Q(team_b__name__icontains=match["teams"]["away"]["name"])
            )
        if len(match_search) == 1:
            match_found = match_search[0]
            setattr(match_found, "api_match_id", int(match["fixture"]["id"]))
            if match["fixture"]["status"]["short"] in ["FT", "AET", "PEN"]:
                if match_found.api_match_data is None or override_data:
                    setattr(match_found, "api_match_data", match)
                if match_found.score_a is None:
                    home_score = match["goals"]["home"]
                    setattr(match_found, "score_a", home_score)
                if match_found.score_b is None:
                    away_score = match["goals"]["away"]
                    setattr(match_found, "score_b", away_score)
            match_found.save()
        print(f"API data added for match {match_found}")


@app.task()
def daily_api_scores():
    """clery beat daily 14:00 scheduled task - this task will check if matches are scheduled for today and schedule api fetching of the scores"""
    print("Checking if matches today and schedule api match score fetching")
    today = datetime.datetime.today()

    # Check if today first day if new group phase to fetch match ids if so
    first_day_new_phase = False
    for min_dict in Match.objects.all().values("phase").annotate(min_match_date=Min("match_time__date")):
        if min_dict["min_match_date"] == today.date():
            first_day_new_phase = True

    if first_day_new_phase:
        print("Today is new tournament phase - fetching match ids from API...")
        update_api_match_ids()

    # Check if today matches to schedule match score api requests
    todays_matches = Match.objects.filter(
        match_time__date=today.date(), score_a__isnull=True, score_b__isnull=True
    ).order_by("match_time")

    for match in todays_matches:
        match_id = match.id
        match_id_api = match.api_match_id
        match_eta = match.match_time + datetime.timedelta(minutes=90 + 15 + 15)

        if match_id_api is not None:
            app.send_task(
                "competition.tasks.api_match_score_request",
                args=[
                    match_id,
                    match_id_api,
                ],
                eta=match_eta,
            )
            print(f"Scheduled API Match Score request for {match} at {match_eta}")


@app.task()
def api_match_score_request(match_id, match_id_api, override_data=False):
    """API request to fetch match data"""
    print(f"Checking match score via API for match {match_id}")

    match_obj = Match.objects.get(pk=match_id)

    match_finished = False
    wait_time = 0
    while match_finished is False and wait_time <= 60:
        match_api_data = get_api_match_data(match_id=match_id_api)

        if match_api_data is not None and match_api_data["fixture"]["status"]["short"] in ["FT", "AET", "PEN"]:
            match_finished = True
            setattr(match_obj, "api_match_data", match_api_data)
            if match_obj.score_a is None or override_data:
                home_score = match_api_data["goals"]["home"]
                setattr(match_obj, "score_a", home_score)
            if match_obj.score_b is None or override_data:
                away_score = match_api_data["goals"]["away"]
                setattr(match_obj, "score_b", away_score)
            match_obj.save()
            print(f"Match scores for {match_obj} successfully fetched via API.")

        else:
            print(f"Match {match_obj} did not finish yet - wait 10min and try again...")
            wait_time += 10
            time.sleep(60 * 10)

    if match_finished is False:
        raise Exception(
            f"Match {match_obj} did not finish even after {wait_time}min of waiting - no api scores fetched"
        )


@app.task()
def daily_emails():
    """clery beat daily 12:45 scheduled task - this task will trigger either the last_admission_email or daily_matchday_email"""
    print("Checking if daily emails need to be send out")
    today = datetime.datetime.today()
    first_match_date = Match.objects.all().order_by("match_time").first().match_time
    if today.weekday() == 4:  # if friday
        upcomming_matches = Match.objects.filter(
            match_time__date__gte=today.date(), match_time__date__lte=(today + datetime.timedelta(days=2)).date()
        ).order_by("match_time")
    else:  # not friday
        upcomming_matches = Match.objects.filter(match_time__date=today.date()).order_by("match_time")
    email_to_send = None

    # first match is tomorrow
    if (first_match_date - datetime.timedelta(days=1)).date() == today.date():
        print("Sending final reminder emails today")
        email_to_send = "competition.tasks.last_admission_email"

    # today are matches
    elif len(upcomming_matches) > 0 or settings.DEBUG:
        print("Sending daily match emails today")
        email_to_send = "competition.tasks.daily_matchday_email"

    # if emails are send out today
    if email_to_send is not None:
        user_lst = CustomUser.objects.all().order_by("pk")
        prev_email_eta = settings.TIME_ZONE_OBJ.localize(datetime.datetime.now())
        prev_email_eta += datetime.timedelta(minutes=1)

        for i, user in enumerate(user_lst):
            app.send_task(
                email_to_send,
                args=[
                    user.pk,
                ],
                eta=prev_email_eta,
            )
            print(f"Email {email_to_send} for {user.pk} scheduled at {prev_email_eta}")
            if i == 0:
                prev_email_eta += datetime.timedelta(minutes=5)
            else:
                prev_email_eta += datetime.timedelta(seconds=45)
    else:
        print("No daily emails today")


@app.task()
def daily_matchday_email(user_pk, override_date=None):
    """Email to remind the users to put in predictions for today's matches"""
    user_obj = CustomUser.objects.get(pk=user_pk)
    today = datetime.datetime.today()
    if override_date is not None:
        today = override_date

    if isinstance(today, str):
        is_friday = False
        upcomming_matches = Match.objects.filter(match_time__date=today).order_by("match_time")
    elif today.weekday() == 4:  # if friday
        is_friday = True
        upcomming_matches = Match.objects.filter(
            match_time__date__gte=today.date(), match_time__date__lte=(today + datetime.timedelta(days=2)).date()
        ).order_by("match_time")
    else:  # not friday
        is_friday = False
        upcomming_matches = Match.objects.filter(match_time__date=today.date()).order_by("match_time")

    upcomming_matches_html = ""
    for match in upcomming_matches:
        bet = match.matchbet_set.filter(user=user_obj).first()
        bet_a = "-" if bet is None else bet.score_a
        bet_b = "-" if bet is None else bet.score_b
        localDatetime = match.match_time.astimezone(settings.TIME_ZONE_OBJ)
        upcomming_matches_html += f'<tr><td><b>{localDatetime.strftime("%a %H:%M" if is_friday else "%H:%M")}</b></td><td style="text-align: right;">{match.team_a.name} <img src="{ match.team_a.flag }" height="20" width="20"></td><td style="text-align: center;">{bet_a}:{bet_b}</td><td><img src="{ match.team_b.flag }" height="20" width="20"> {match.team_b.name}</td><td>{match.tv_broadcaster}</td></tr>\n'
    upcomming_matches_html = "<table>\n" + upcomming_matches_html + "</table>\n"

    email_subject, email_body = __get_email_template("daily_email")

    first_name = user_obj.first_name
    my_predictions_link = f"{settings.MAIN_HOST}/predictions/my/"
    leaderboard_link = f"{settings.MAIN_HOST}/leaderboard/"

    email_body = email_body.format(
        first_name=first_name,
        my_predictions_link=my_predictions_link,
        leaderboard_link=leaderboard_link,
        table_today_matches=upcomming_matches_html,
    )

    send_email(subject=email_subject, body=email_body, to_email=user_obj.email)


@app.task()
def last_admission_email(user_pk):
    """Email to remind users that tomorrow the first match kicks-off and they need to put in predictions"""
    user_obj = CustomUser.objects.get(pk=user_pk)

    email_subject, email_body = __get_email_template("final_reminder")

    first_name = user_obj.first_name
    my_predictions_link = f"{settings.MAIN_HOST}/predictions/my/"

    email_body = email_body.format(
        first_name=first_name,
        my_predictions_link=my_predictions_link,
    )

    send_email(subject=email_subject, body=email_body, to_email=user_obj.email)


@app.task()
def welcome_email(user_pk):
    """Welcome with email verification and payment instructions"""
    user_obj = CustomUser.objects.get(pk=user_pk)

    email_subject, email_body = __get_email_template("welcome_email")

    first_name = user_obj.first_name
    id = user_obj.pk
    verify_link = f"{settings.MAIN_HOST}/verify/{id}/"
    qr_image_link = f"{settings.MAIN_HOST}/static/qr_pay.jpg"

    email_body = email_body.format(first_name=first_name, verify_link=verify_link, qr_image_link=qr_image_link)

    send_email(subject=email_subject, body=email_body, to_email=user_obj.email)


@app.task()
def payment_reminder_email(user_pk, cc=[]):
    """Payment reminder email"""
    user_obj = CustomUser.objects.get(pk=user_pk)
    cc_lst = [CustomUser.objects.get(pk=i).email for i in cc]

    email_subject, email_body = __get_email_template("payment_reminder")

    first_name = user_obj.first_name
    qr_image_link = f"{settings.MAIN_HOST}/static/qr_pay.jpg"

    email_body = email_body.format(first_name=first_name, qr_image_link=qr_image_link)

    send_email(subject=email_subject, body=email_body, to_email=user_obj.email, cc=cc_lst, reply_to=cc_lst)


def bs_tag_visible(element):
    """Remove not visible html from BeautifulSoup soup for clean text extraction"""
    if element.parent.name in ["style", "script", "head", "title", "meta", "[document]"]:
        return False
    # if isinstance(element, Comment):
    #    return False
    return True


def send_email(subject, body, to_email, cc=[], reply_to=[]):
    """General function via which all emails are sent out"""
    to_email = [settings.EMAIL_FROM] if settings.DEBUG else [to_email]
    from_email = settings.EMAIL_FROM
    reply_to_email = [from_email] if settings.EMAIL_REPLY_TO is None else settings.EMAIL_REPLY_TO
    with open(os.path.join("templates", "emails", "base.html"), "r") as file:
        email_template = file.read()

    html_message = email_template
    for tag, replace_value in dict(
        MAIN_BODY=body, EMAIL_SUBJECT=subject, EMAIL_REPLY_TO=reply_to_email[0], MAIN_HOST=settings.MAIN_HOST
    ).items():
        html_message = html_message.replace("{" + f"{tag}" + "}", str(replace_value))
    # bs_soup = BeautifulSoup(body, "html.parser")
    # bs_texts = bs_soup.findAll(text=True)
    # visible_texts = filter(bs_tag_visible, bs_texts)
    # text_message = " ".join(t.strip() for t in visible_texts)

    connection = get_connection()
    mail = EmailMultiAlternatives(
        subject=subject, body="", from_email=from_email, to=to_email, cc=cc, reply_to=reply_to, connection=connection
    )
    mail.attach_alternative(html_message, "text/html")
    mail.content_subtype = "html"

    if "admin" in to_email[0].lower() or "local" in to_email[0].lower():
        print(f'Email "{subject}" sent not to {to_email} as looks like test email')
    else:
        mail.send()
        print(f'Email "{subject}" sent to {to_email}')
