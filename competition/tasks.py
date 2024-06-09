# -*- coding: utf-8 -*-
import os
import datetime
from django.core.mail import EmailMultiAlternatives, get_connection
from django.db.models.signals import post_save
from django.dispatch import receiver
from sweepstake.celery import app
from django.conf import settings
from bs4 import BeautifulSoup

from competition.models import Match
from general.models import EmailTemplates, CustomUser


@app.task(bind=True)
def daily_emails(self):
    """clery beat daily 14:00 scheduled task - this task will trigger either the last_admission_email or daily_matchday_email"""
    today = datetime.datetime.today()
    first_match_date = Match.objects.all().order_by("match_time").first().match_time
    upcomming_matches = Match.objects.filter(match_time__date=today).order_by("match_time")
    email_to_send = None

    # first match is tomorrow
    if first_match_date - datetime.timedelta(days=1) == today:
        print("Sending final reminder emails today")
        email_to_send = last_admission_email

    # today are matches
    elif len(upcomming_matches) > 0:
        print("Sending daily match emails today")
        email_to_send = daily_matchday_email

    # if emails are send out today
    if email_to_send is not None:
        user_lst = CustomUser.objects.all().order_by("pk")
        prev_email_eta = settings.TIME_ZONE_OBJ.localize(datetime.datetime.now())
        prev_email_eta += datetime.timedelta(minute=1)

        for i, user in enumerate(user_lst):
            email_to_send.apply_async((user), eta=prev_email_eta)
            if i < 3:
                prev_email_eta += datetime.timedelta(minute=5)
            else:
                prev_email_eta += datetime.timedelta(minute=2)


@app.task(bind=True)
def daily_matchday_email(user_obj, override_date=None):
    """Email to remind the users to put in predictions for today's matches"""
    today = datetime.datetime.today()
    if override_date is not None:
        today = "2024-06-15"
    upcomming_matches = Match.objects.filter(match_time__date=today).order_by("match_time")

    upcomming_matches_html = ""
    for match in upcomming_matches:
        bet = match.matchbet_set.filter(user=user_obj).first()
        bet_a = "-" if bet is None else bet.score_a
        bet_b = "-" if bet is None else bet.score_b
        upcomming_matches_html += f'<tr><td><b>{match.match_time.strftime("%H:%M")}</b></td><td style="text-align: right;">{match.team_a.name} <img src="{ match.team_a.flag }" height="20px" width="20px"></td><td style="text-align: center;">{bet_a}:{bet_b}</td><td><img src="{ match.team_b.flag }" height="20px" width="20px"> {match.team_b.name}</td><td>{match.tv_broadcaster}</td></tr>\n'
    upcomming_matches_html = "<table>\n" + upcomming_matches_html + "</table>\n"

    email_template = EmailTemplates.objects.get(name="daily_email")
    email_subject = email_template.email_subject
    email_body = email_template.html

    if settings.DEBUG:
        with open(os.path.join("templates", "emails", "daily_email.html"), "r") as file:
            email_template = file.read()
            email_body = email_template

    first_name = user_obj.first_name
    my_predictions_link = f"{settings.MAIN_HOST}/predictions/my/"
    leaderboard_link = f"{settings.MAIN_HOST}/leaderboard/"

    email_body = email_body.format(
        first_name=first_name,
        my_predictions_link=my_predictions_link,
        leaderboard_link=leaderboard_link,
        table_today_matches=upcomming_matches_html,
    )

    send_email(subject=email_subject, body=email_body, to_user=user_obj)


@app.task(bind=True)
def last_admission_email(user_obj):
    """Email to remind users that tomorrow the first match kicks-off and they need to put in predictions"""
    email_template = EmailTemplates.objects.get(name="final_reminder")
    email_subject = email_template.email_subject
    email_body = email_template.html

    if settings.DEBUG:
        with open(os.path.join("templates", "emails", "final_reminder.html"), "r") as file:
            email_template = file.read()
            email_body = email_template

    first_name = user_obj.first_name
    my_predictions_link = f"{settings.MAIN_HOST}/predictions/my/"

    email_body = email_body.format(
        first_name=first_name,
        my_predictions_link=my_predictions_link,
    )

    send_email(subject=email_subject, body=email_body, to_user=user_obj)


@app.task(bind=True)
def welcome_email(user_obj):
    """Welcome with email verification and payment instructions"""
    email_template = EmailTemplates.objects.get(name="welcome_email")
    email_subject = email_template.email_subject
    email_body = email_template.html

    if settings.DEBUG:
        with open(os.path.join("templates", "emails", "welcome_email.html"), "r") as file:
            email_template = file.read()
            email_body = email_template

    first_name = user_obj.first_name
    id = user_obj.pk
    verify_link = f"{settings.MAIN_HOST}/verify/{id}/"

    email_body = email_body.format(
        first_name=first_name,
        verify_link=verify_link,
    )

    send_email(subject=email_subject, body=email_body, to_user=user_obj)


@receiver(post_save, sender=CustomUser)
def user_welcome_email_post_save(sender, instance, created, *args, **kwargs):
    """When a new user is created send an welcome email"""
    if created:
        welcome_email.apply_async((instance))


def bs_tag_visible(element):
    """Remove not visible html from BeautifulSoup soup for clean text extraction"""
    if element.parent.name in ["style", "script", "head", "title", "meta", "[document]"]:
        return False
    # if isinstance(element, Comment):
    #    return False
    return True


def send_email(subject, body, to_user):
    """General function via which all emails are sent out"""
    to_email = [settings.EMAIL_FROM] if settings.DEBUG else to_user.email
    from_email = settings.EMAIL_FROM
    reply_to_email = settings.EMAIL_REPLY_TO
    with open(os.path.join("templates", "emails", "base.html"), "r") as file:
        email_template = file.read()

    html_message = email_template
    for tag, replace_value in dict(
        MAIN_BODY=body, EMAIL_SUBJECT=subject, EMAIL_REPLY_TO=reply_to_email[0], MAIN_HOST=settings.MAIN_HOST
    ).items():
        html_message = html_message.replace("{" + f"{tag}" + "}", str(replace_value))
    bs_soup = BeautifulSoup(body, "html.parser")
    bs_texts = bs_soup.findAll(text=True)
    visible_texts = filter(bs_tag_visible, bs_texts)
    text_message = " ".join(t.strip() for t in visible_texts)

    connection = get_connection()
    mail = EmailMultiAlternatives(
        subject=subject, body=text_message, from_email=from_email, to=to_email, connection=connection
    )
    mail.attach_alternative(html_message, "text/html")
    mail.content_subtype = "html"

    if "admin" in to_email[0].lower() or "local" in to_email[0].lower():
        print(f'Email "{subject}" sent not to {to_email} as looks like test email')
    else:
        mail.send()
        print(f'Email "{subject}" sent to {to_email}')
