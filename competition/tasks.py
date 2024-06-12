# -*- coding: utf-8 -*-
import os
import datetime
from django.core.mail import EmailMultiAlternatives, get_connection
from sweepstake.celery import app
from django.conf import settings

from competition.models import Match
from general.models import EmailTemplates, CustomUser


def __get_email_template(template_name):
    email_obj = EmailTemplates.objects.filter(name=template_name)

    if settings.DEBUG or len(email_obj):
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


@app.task()
def daily_emails():
    """clery beat daily 14:00 scheduled task - this task will trigger either the last_admission_email or daily_matchday_email"""
    print("Checking if daily emails need to be send out")
    today = datetime.datetime.today()
    first_match_date = Match.objects.all().order_by("match_time").first().match_time
    upcomming_matches = Match.objects.filter(match_time__date=today).order_by("match_time")
    email_to_send = None

    # first match is tomorrow
    if first_match_date - datetime.timedelta(days=1) == today:
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
            if i < 3:
                prev_email_eta += datetime.timedelta(minutes=5)
            else:
                prev_email_eta += datetime.timedelta(minutes=2)
    else:
        print("No daily emails today")


@app.task()
def daily_matchday_email(user_pk, override_date=None):
    """Email to remind the users to put in predictions for today's matches"""
    user_obj = CustomUser.objects.get(pk=user_pk)
    today = datetime.datetime.today()
    if override_date is not None:
        today = "2024-06-15"
    upcomming_matches = Match.objects.filter(match_time__date=today).order_by("match_time")

    upcomming_matches_html = ""
    for match in upcomming_matches:
        bet = match.matchbet_set.filter(user=user_obj).first()
        bet_a = "-" if bet is None else bet.score_a
        bet_b = "-" if bet is None else bet.score_b
        upcomming_matches_html += f'<tr><td><b>{match.match_time.strftime("%H:%M")}</b></td><td style="text-align: right;">{match.team_a.name} <img src="{ match.team_a.flag }" height="20" width="20"></td><td style="text-align: center;">{bet_a}:{bet_b}</td><td><img src="{ match.team_b.flag }" height="20" width="20"> {match.team_b.name}</td><td>{match.tv_broadcaster}</td></tr>\n'
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
