"""Welcome email sent when a user joins a competition as a participant."""

import re
from typing import Optional

from markupsafe import Markup, escape

from src.config import settings
from src.emails.send import render_html, send_email

# Matches http://, https://, and bare www. URLs.
# Applied *after* HTML-escaping, so & is already &amp; in the text —
# [^\s<>"'] stops at whitespace and the characters that cannot appear raw.
_URL_RE = re.compile(r'((?:https?://|www\.)[^\s<>"\']+)', re.IGNORECASE)


def _linkify_stake(stake: str) -> Markup:
    """HTML-escape stake text, turn URLs into <a> links, convert newlines to <br>."""
    escaped = str(escape(stake))

    def _make_link(m: re.Match) -> str:
        url = m.group(1).rstrip(".,;:!?)")  # strip trailing sentence punctuation
        href = url if url.lower().startswith(("http://", "https://")) else f"http://{url}"
        return f'<a href="{href}" style="color:#2563eb;text-decoration:underline;">{url}</a>'

    linked = _URL_RE.sub(_make_link, escaped)
    return Markup(linked.replace("\n", "<br>"))


def _format_sign_off(admins: list[dict]) -> str:
    """Return a human-readable list of admin first names, e.g. 'Alice, Bob & Carol'."""
    names = [a["first_name"] for a in admins if a.get("first_name")]
    if not names:
        return "The Organisers"
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " & " + names[-1]


def _format_reply_to(admins: list[dict]) -> Optional[str]:
    """Return a RFC 5322 Reply-To header value for all admins with an email address."""
    parts = []
    for a in admins:
        if not a.get("email"):
            continue
        full = a["first_name"]
        if a.get("last_name"):
            full += f" {a['last_name']}"
        parts.append(f"{full} <{a['email']}>")
    return ", ".join(parts) if parts else None


def _admin_footer_entries(admins: list[dict]) -> list[dict]:
    """Return list of {full_name, email} dicts for the email footer."""
    entries = []
    for a in admins:
        full = a["first_name"]
        if a.get("last_name"):
            full += f" {a['last_name']}"
        entries.append({"full_name": full, "email": a.get("email", "")})
    return entries


def _build_text_body(
    first_name: str,
    tournament_name: str,
    tournament_url: str,
    stake: Optional[str],
    match_winner_points: Optional[int],
    match_score_points: Optional[int],
    group_winner_points: Optional[int],
    stage_winner_points: Optional[int],
    first_place_points: Optional[int],
    second_place_points: Optional[int],
    third_place_points: Optional[int],
    admin_sign_off: str = "The Organisers",
    admin_footer: Optional[list[dict]] = None,
) -> str:
    lines = [
        f"Welcome to {tournament_name}, {first_name}!",
        "",
        f"You have successfully joined the {tournament_name} SweepStake.",
        "",
    ]
    if stake:
        lines += [
            "ENTRY STAKE",
            "-" * 40,
            stake,
            "",
            "Note: it may take a few days for your payment to be confirmed by the organiser.",
            "",
        ]
    lines += ["COMPETITION RULES & SCORING", "-" * 40, "Points awarded per correct prediction:", ""]
    for label, pts in [
        ("Correct tournament winner", first_place_points),
        ("Correct runner-up", second_place_points),
        ("Correct third place", third_place_points),
        ("Correct group winner", group_winner_points),
        ("Correct stage/round winner", stage_winner_points),
        ("Correct match winner", match_winner_points),
        ("Exact match score", match_score_points),
    ]:
        if pts:
            lines.append(f"  {label}: {pts} pts")
    lines += [
        "",
        "PREDICTION DEADLINES",
        "-" * 40,
        "Tournament / Stage / Group predictions: submit by 23:59 the day BEFORE the first match.",
        "Match predictions: submit up to 1 minute before kick-off.",
        "The organiser can add predictions on your behalf if you joined late.",
        "",
        f"Go to Competition: {tournament_url}",
        "",
        f"Good luck — may the best predictor win!",
        "",
        f"Best regards,",
        admin_sign_off,
        "",
        "---",
        "SweepStake — Football Prediction Competition",
        "You received this email because you joined a SweepStake competition.",
    ]
    if admin_footer:
        organisers = ", ".join(f"{a['full_name']} ({a['email']})" for a in admin_footer)
        lines.append(f"Organised by: {organisers}")
    return "\n".join(lines)


async def send_competition_welcome_email(
    to_email: str,
    first_name: str,
    tournament_name: str,
    tournament_id: int,
    stake: Optional[str],
    match_winner_points: Optional[int],
    match_score_points: Optional[int],
    group_winner_points: Optional[int],
    stage_winner_points: Optional[int],
    first_place_points: Optional[int],
    second_place_points: Optional[int],
    third_place_points: Optional[int],
    match_score_method: str = "no-penalty",
    admins: Optional[list[dict]] = None,
    user_id: Optional[int] = None,
) -> None:
    admins = admins or []
    sign_off = _format_sign_off(admins)
    reply_to = _format_reply_to(admins)
    footer_entries = _admin_footer_entries(admins)
    tournament_url = f"{settings.main_host.rstrip('/')}/tournament/{tournament_id}"

    match_score_method_desc = (
        '(regular time + extra time + penalties)' if match_score_method == 'final' else
        '(regular time only; no extra time & penalties)' if match_score_method == 'regular-time' else
        '(regular time + extra time; no penalties)'
    )
    stake_html: Optional[Markup] = _linkify_stake(stake) if stake else None
    context = {
        "first_name": first_name,
        "tournament_name": tournament_name,
        "tournament_url": tournament_url,
        "stake": stake_html,
        "match_winner_points": match_winner_points or None,
        "match_score_points": match_score_points or None,
        "group_winner_points": group_winner_points or None,
        "stage_winner_points": stage_winner_points or None,
        "first_place_points": first_place_points or None,
        "second_place_points": second_place_points or None,
        "third_place_points": third_place_points or None,
        "match_score_method_desc": match_score_method_desc,
        "admin_sign_off": sign_off,
        "admin_footer": footer_entries,
    }
    html_body = render_html("welcome_email.html", context)
    text_body = _build_text_body(
        first_name=first_name,
        tournament_name=tournament_name,
        tournament_url=tournament_url,
        stake=stake,
        match_winner_points=match_winner_points,
        match_score_points=match_score_points,
        group_winner_points=group_winner_points,
        stage_winner_points=stage_winner_points,
        first_place_points=first_place_points,
        second_place_points=second_place_points,
        third_place_points=third_place_points,
        admin_sign_off=sign_off,
        admin_footer=footer_entries,
    )
    await send_email(
        to_email,
        f"Welcome to {tournament_name} – SweepStake",
        html_body,
        text_body,
        user_id=user_id,
        reply_to=reply_to,
    )
