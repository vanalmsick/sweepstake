"""Upcoming-matches reminder email sent once daily to each tournament participant."""

from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from src.config import settings
from src.emails.send import render_html, send_email


def _to_local(dt: datetime, tz_str: str) -> datetime:
    tz = ZoneInfo(tz_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz)


def _format_sign_off(admins: list[dict]) -> str:
    names = [a["first_name"] for a in admins if a.get("first_name")]
    if not names:
        return "The Organisers"
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " & " + names[-1]


def _format_reply_to(admins: list[dict]) -> Optional[str]:
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
    matches: list[dict],
    admin_sign_off: str,
    admin_footer: Optional[list[dict]],
    winner_reminder: Optional[dict] = None,
    match_score_method_desc: str = "regular time + extra time - no penalties",
) -> str:
    n = len(matches)
    lines = [
        f"Upcoming Matches, {first_name}!",
        "",
        f"You have {n} upcoming match{'es' if n != 1 else ''} in {tournament_name} in the next 26 hours.",
        "Make sure your predictions are in before kick-off!",
        "",
    ]
    if winner_reminder:
        lines += [
            "⏰ PREDICTION DEADLINE — TODAY AT 23:59",
            "-" * 60,
            f"The first match of {tournament_name} kicks off tomorrow.",
            "Set your winner predictions before tonight at 23:59:",
        ]
        if winner_reminder.get("has_tournament"):
            lines.append("  - Tournament Winner")
        if winner_reminder.get("has_groups"):
            lines.append("  - Group Winners")
        if winner_reminder.get("has_stages"):
            lines.append("  - Stage Winners")
        lines.append("")
    lines += [
        "UPCOMING MATCHES",
        "-" * 60,
    ]
    for m in matches:
        home = m["home_team_name"]
        away = m["away_team_name"]
        dt = f"{m['date_line']} {m['time_line']}"
        ph = m["pred_home_score"]
        pa = m["pred_away_score"]
        pred_str = f"{ph} - {pa}" if ph is not None and pa is not None else "no prediction"
        tv = f"  [{m['tv_channel']}]" if m.get("tv_channel") else ""
        lines.append(f"  {dt}  {home} vs {away}  ({pred_str}){tv}")
    lines += [
        "",
        f"Update your predictions: {tournament_url}",
        "",
        f"Good luck — may the best predictor win!",
        "",
        "Best regards,",
        admin_sign_off,
        "",
        f"P.S. Match predictions are based on the score after {match_score_method_desc}.",
        "",
        "---",
        "SweepStake — Football Prediction Competition",
        f"You received this email because you are a participant in {tournament_name}.",
    ]
    if admin_footer:
        organisers = ", ".join(f"{a['full_name']} ({a['email']})" for a in admin_footer)
        lines.append(f"Organised by: {organisers}")
    return "\n".join(lines)


async def send_upcoming_matches_email(
    to_email: str,
    first_name: str,
    tournament_name: str,
    tournament_id: int,
    matches: list[dict],
    admins: Optional[list[dict]] = None,
    user_id: Optional[int] = None,
    winner_reminder: Optional[dict] = None,
    match_score_method: str = "no-penalty",
) -> None:
    """Send the upcoming-matches reminder for one user / tournament.

    Each dict in *matches* must contain:
        date_line, time_line, home_team_name, home_team_image_url,
        away_team_name, away_team_image_url,
        pred_home_score (int|None), pred_away_score (int|None), tv_channel (str|None)

    *winner_reminder*, when not None, triggers a deadline-warning section at the top.
    It must contain: has_tournament (bool), has_groups (bool), has_stages (bool).
    """
    admins = admins or []
    sign_off = _format_sign_off(admins)
    reply_to = _format_reply_to(admins)
    footer_entries = _admin_footer_entries(admins)
    tournament_url = f"{settings.main_host.rstrip('/')}/tournament/{tournament_id}"

    match_score_method_desc = (
        'regular time + extra time + penalties' if match_score_method == 'final' else
        'regular time only - no extra time & penalties' if match_score_method == 'regular-time' else
        'regular time + extra time - no penalties'
    )

    context = {
        "first_name": first_name,
        "tournament_name": tournament_name,
        "tournament_url": tournament_url,
        "matches": matches,
        "winner_reminder": winner_reminder,
        "admin_sign_off": sign_off,
        "admin_footer": footer_entries,
        "match_score_method_desc": match_score_method_desc,
    }
    html_body = render_html("upcoming_matches_email.html", context)
    text_body = _build_text_body(
        first_name=first_name,
        tournament_name=tournament_name,
        tournament_url=tournament_url,
        matches=matches,
        admin_sign_off=sign_off,
        admin_footer=footer_entries,
        winner_reminder=winner_reminder,
        match_score_method_desc=match_score_method_desc,
    )
    await send_email(
        to_email,
        f"Upcoming Matches: {tournament_name} – SweepStake",
        html_body,
        text_body,
        user_id=user_id,
        reply_to=reply_to,
    )
