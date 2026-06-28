import { useState } from 'react'
import { useSearchParams, useLocation } from 'react-router-dom'
import { ChevronLeft, ChevronRight, X, Copy, Check } from 'lucide-react'
import { useScrollLock } from './base'
import { useGetTournamentQuery } from '../api/tournamentApi'
import { StakeText } from '../components/TournamentPageHeader'

// ---------------------------------------------------------------------------
// Page definitions
// ---------------------------------------------------------------------------

interface GuidePage {
  title: string
  emoji: string
  body: React.ReactNode
}

const PARTICIPANT_PAGES: GuidePage[] = [
  {
    title: 'How to Navigate:',
    emoji: '🏆',
    body: (
      <div className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
        <img
          src="/guide-navigation.webp"
          alt="Navigation bar showing Overview, Leaderboard, and My Predictions tabs"
          className="w-80 rounded-lg border border-gray-200 dark:border-gray-700"
        />
        <ul className="space-y-2 pl-4 list-none">
          <li className="font-semibold list-disc list-inside">Overview: <span className="font-normal">View the competition rules, upcoming matches, and tournament results.</span></li>
          <li className="font-semibold list-disc list-inside">Leaderboard: <span className="font-normal">See where you and your friends are on the leaderboard.</span></li>
          <li className="font-semibold list-disc list-inside">My Predictions: <span className="font-normal">Place your predictions and see your points earned from past matches.</span></li>
        </ul>
      </div>
    ),
  },
  {
    title: 'Deadlines to Submit Your Predictions:',
    emoji: '📅',
    body: (
      <div className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
        <p className="font-medium text-gray-800 dark:text-gray-200 mb-1">Tournament / Stage / Group Predictions</p>
        <p>Submit your predictions <b>1 day until 23:59 before</b> the first match of the tournament / stage / group. On the top right you can see when the predictions close.</p>
        <img
          src="/guide-prediction-group.webp"
          alt="Group winner predictions with a deadline shown on the top right"
          className="w-80 rounded-lg border border-gray-200 dark:border-gray-700"
        />
        <p className="font-medium text-gray-800 dark:text-gray-200 mb-1">Match Predictions</p>
        <p>Submit your predictions <b>up 1 minute before</b> the match kicks off. The red line with the countdown shows the remaining time.</p>
        <img
          src="/guide-prediction-match.webp"
          alt="Match predictions with a deadline shown on the top right"
          className="w-80 rounded-lg border border-gray-200 dark:border-gray-700"
        />
        <p className="text-xs text-gray-400 dark:text-gray-500"><b>Note:</b> The organiser can add predictions for you even past the deadline in case you joined the competition late.</p>
      </div>
    ),
  },
  {
    title: "View Others' Predictions:",
    emoji: '🔍',
    body: (
      <div className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
        <p>If predictions for a match, group, stage, or the tournament winner are closed, a 🔍 icon will appear:</p>
        <img
          src="/guide-results-button.webp"
          alt="Group winner predictions with a deadline shown on the top right"
          className="w-80 rounded-lg border border-gray-200 dark:border-gray-700"
        />
        <p>By clicking on it, you can view your friends' predictions:</p>
        <img
          src="/guide-results-popup.webp"
          alt="Match predictions with a deadline shown on the top right"
          className="w-80 rounded-lg border border-gray-200 dark:border-gray-700"
        />
      </div>
    ),
  },
]

const ADMIN_EXTRA_PAGES: GuidePage[] = [
  {
    title: 'You are the Admin!',
    emoji: '⚙️',
    body: (
      <div className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
        <p>
          As an admin, you can configure your SweepStake with the ✏️ Edit button:
        </p>
        <img
          src="/guide-admin-tournament-1.webp"
          alt="Admin editing the SweepStake settings with a form showing fields for entry fee and Football-data.org API key"
          className="w-80 rounded-lg border border-gray-200 dark:border-gray-700"
        />
        <p>
          Empty the <b>stake field</b> if there is no entry fee, else update it with instructions on how to pay. Links are automatically detected.
        </p>
        <img
          src="/guide-admin-tournament-2.webp"
          alt="Admin editing the SweepStake settings with a form showing fields for entry fee and Football-data.org API key"
          className="w-80 rounded-lg border border-gray-200 dark:border-gray-700"
        />
        <p>
          Populate the <b>Football-data.org field</b> to enable automatic match schedules and scores from Football-data.org.
        </p>
        <img
          src="/guide-admin-tournament-3.webp"
          alt="Admin editing the SweepStake settings with a form showing fields for entry fee and Football-data.org API key"
          className="w-80 rounded-lg border border-gray-200 dark:border-gray-700"
        />
        <p>
          <ul className="list-disc list-inside space-y-1">
            <li>Change the <b>point fields</b> to customize how points are awarded for different predictions. Enter 0 to disable predictions in that category.</li>
            <li>Also, populate the <b>1st, 2nd, and 3rd place fields</b> to award users points for correctly predicting the top teams.</li>
          </ul>
        </p>
        <img
          src="/guide-admin-tournament-4.webp"
          alt="Admin editing the SweepStake settings with a form showing fields for entry fee and Football-data.org API key"
          className="w-80 rounded-lg border border-gray-200 dark:border-gray-700"
        />
        <p>
          <ul className="list-disc list-inside space-y-1">
            <li>Tick the <b>💲 button (green)</b> to confirm that the user paid the stake.</li>
            <li>Tick the <b>👑 button (yellow)</b> to promote the user to admin.</li>
            <li>Tick the <b>❌ button (red)</b> to remove the user from the SweepStake competition.</li>
          </ul>
        </p>
      </div>
    ),
  },
  {
    title: 'Editing Matches',
    emoji: '✏️',
    body: (
      <div className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
        <p>On the Overview page you can add matches, teams, groups, stages pressing the <b>+ icon</b> or edit them with the <b>✏️ icon</b>.</p>
        <img
          src="/guide-navigation.webp"
          alt="Navigation bar showing Overview, Leaderboard, and My Predictions tabs"
          className="w-80 rounded-lg border border-gray-200 dark:border-gray-700"
        />
      </div>
    ),
  },
  {
    title: 'Others\' Predictions',
    emoji: '👥',
    body: (
      <div className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
        <p>As admin you can edit other users' predictions even after the cutoff - e.g. in case they joined the SweepStake late.</p>
        <p>For that go to <b>Leaderboard</b> → <b>🔍 icon</b> next to the user's name.</p>
        <p>Every change you make to other users' predictions <b>is logged for transparency</b> and <b>you cannot change your own predictions</b> after the cutoff - to ensure fairness only another admin can change your predictions.</p>
      </div>
    ),
  },
]

// ---------------------------------------------------------------------------
// Live scoring rules — fetches tournament data from the current URL
// ---------------------------------------------------------------------------

function ScoringRulesBody({ tournamentId }: { tournamentId: number | null }) {
  const { data: tournament } = useGetTournamentQuery(tournamentId!, { skip: tournamentId == null })

  if (!tournament) {
    return <p className="text-sm text-gray-500 dark:text-gray-400">Loading scoring rules…</p>
  }

  const matchScoreMethodDesc = 
    tournament.match_score_method === 'final' ? '(regular time + extra time + penalties)' :
        tournament.match_score_method === 'regular-time' ? '(regular time only; no extra time & penalties)' :
        '(regular time + extra time; no penalties)';
  const rules: { label: string; points: number | null }[] = [
    { label: '🥇 Correct tournament winner', points: tournament.first_place_points },
    { label: '🥈 Correct runner-up', points: tournament.second_place_points },
    { label: '🥉 Correct third place', points: tournament.third_place_points },
    { label: '👥 Correct group winner', points: tournament.group_winner_points },
    { label: '🏆 Correct stage winner', points: tournament.stage_winner_points },
    { label: `⚽ Correct match winner ${matchScoreMethodDesc}`, points: tournament.match_winner_points },
    { label: `🎯 Exact match score ${matchScoreMethodDesc}`, points: tournament.match_score_points },
  ].filter((r) => r.points != null && r.points !== 0)

  return (
    <div className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
      <p>These points are awarded for each correct prediction:</p>
      <ul className="divide-y divide-gray-100 dark:divide-gray-700 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        {rules.map((r) => (
          <li key={r.label} className="flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-800">
            <span className="text-sm text-gray-700 dark:text-gray-300">{r.label}</span>
            <span className="text-sm font-semibold text-blue-600 dark:text-blue-400">
              {r.points} pts
            </span>
          </li>
        ))}
      </ul>
      {rules.length === 0 && (
        <p className="text-gray-400 dark:text-gray-500 text-xs">No scoring rules configured yet.</p>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Stake page body
// ---------------------------------------------------------------------------

function StakePageBody({ stake }: { stake: string }) {
  return (
    <div className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
      <p>This SweepStake has an entry stake. Please make sure you pay it to be in:</p>
      <div className="rounded-lg border border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 px-4 py-3">
        <StakeText text={stake} />
      </div>
      <p className="text-xs text-gray-400 dark:text-gray-500"><b>Note:</b> It might take a few days for the payment to be reflected in your account as the organiser has to manually tick a box.</p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Invite friends body — builds copy-able invite text from live tournament data
// ---------------------------------------------------------------------------

function InviteFriendsBody({ name, joinCode }: { name: string; joinCode: string }) {
  const [copied, setCopied] = useState(false)
  const base = window.location.origin
  const text =
    `Hi, I am taking part in the "${name}" SweepStake.\n` +
    `It would be even more fun if you'd join, too!\n\n` +
    `Join code: ${joinCode}\n` +
    `Here is the link to join: ${base}?join=${joinCode}`

  function handleCopy() {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
      <p>Share this message with friends to invite them:</p>
      <div className="relative rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-4 py-3 pr-16">
        <pre className="whitespace-pre-wrap text-xs text-gray-700 dark:text-gray-300 font-sans">{text}</pre>
        <button
          type="button"
          onClick={handleCopy}
          className="absolute top-2 right-2 inline-flex items-center gap-1 rounded-full border border-gray-300 dark:border-gray-600 px-2.5 py-1 text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition"
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Modal component
// ---------------------------------------------------------------------------

function GuideModalInner({
  variant,
  tournamentId,
  onClose,
}: {
  variant: 'participant' | 'admin'
  tournamentId: number | null
  onClose: () => void
}) {
  useScrollLock()
  const { data: tournament } = useGetTournamentQuery(tournamentId!, { skip: tournamentId == null })

  const pages: GuidePage[] = [
    ...PARTICIPANT_PAGES.slice(0, -1),
    {
      title: 'Competition Rules',
      emoji: '📊',
      body: <ScoringRulesBody tournamentId={tournamentId} />,
    },
    PARTICIPANT_PAGES[PARTICIPANT_PAGES.length - 1],
    ...(tournament?.stake ? [{
      title: 'Pay the Stake',
      emoji: '💰',
      body: <StakePageBody stake={tournament.stake} />,
    }] : []),
    ...(variant === 'admin' ? [
      ...ADMIN_EXTRA_PAGES,
      ...(tournament?.join_code ? [{
        title: 'Inviting Friends',
        emoji: '👥',
        body: <InviteFriendsBody name={tournament.name} joinCode={tournament.join_code} />,
      }] : []),
    ] : []),
  ]

  const [index, setIndex] = useState(0)
  const page = pages[index]
  const isFirst = index === 0
  const isLast = index === pages.length - 1

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-gray-900 shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-5 pb-2 mb-3 flex-shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-2xl leading-none" aria-hidden>{page.emoji}</span>
            <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 leading-snug">
              {page.title}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition flex-shrink-0 ml-2"
            aria-label="Close guide"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 pb-4 overflow-y-auto flex-1">
          {page.body}
        </div>

        {/* Footer — dots + navigation */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-100 dark:border-gray-800 flex-shrink-0">
          {/* Dot indicators */}
          <div className="flex items-center gap-1.5">
            {pages.map((_, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setIndex(i)}
                aria-label={`Go to page ${i + 1}`}
                className={[
                  'rounded-full transition-all',
                  i === index
                    ? 'w-4 h-2 bg-blue-600'
                    : 'w-2 h-2 bg-gray-300 dark:bg-gray-600 hover:bg-gray-400 dark:hover:bg-gray-500',
                ].join(' ')}
              />
            ))}
          </div>

          {/* Prev / Next */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setIndex((i) => Math.max(0, i - 1))}
              disabled={isFirst}
              className="inline-flex items-center gap-1 rounded-full border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              <ChevronLeft size={15} />
              Back
            </button>
            {isLast ? (
              <button
                type="button"
                onClick={onClose}
                className="inline-flex items-center gap-1 rounded-full bg-blue-600 hover:bg-blue-700 px-4 py-1.5 text-sm font-medium text-white transition"
              >
                Done
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setIndex((i) => Math.min(pages.length - 1, i + 1))}
                className="inline-flex items-center gap-1 rounded-full bg-blue-600 hover:bg-blue-700 px-4 py-1.5 text-sm font-medium text-white transition"
              >
                Next
                <ChevronRight size={15} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

/** Mount this once at the app level. Reads `?guide=participant|admin` and renders the modal. */
export function GuideModalController() {
  const [searchParams, setSearchParams] = useSearchParams()
  const location = useLocation()
  const guideParam = searchParams.get('guide')

  const tournamentMatch = location.pathname.match(/^\/tournament\/(\d+)/)
  const tournamentId = tournamentMatch ? Number(tournamentMatch[1]) : null

  if (guideParam !== 'participant' && guideParam !== 'admin') return null

  function handleClose() {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.delete('guide')
      return next
    }, { replace: true })
  }

  return <GuideModalInner variant={guideParam} tournamentId={tournamentId} onClose={handleClose} />
}
