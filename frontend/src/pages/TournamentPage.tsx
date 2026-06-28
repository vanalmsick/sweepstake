import { useState, Fragment, useEffect } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Pencil, Plus, Search } from 'lucide-react'
import { useGetTournamentQuery } from '../api/tournamentApi'
import { useListMatchesQuery } from '../api/matchApi'
import { useListGroupsQuery } from '../api/groupApi'
import { useGetMeQuery } from '../api/authApi'
import { PageShell } from '../components/PageShell'
import { Countdown, ElapsedTime } from '../components/Countdown'
import { TournamentPageHeader } from '../components/TournamentPageHeader'
import type { Match } from '../types'
import { EditTournamentModal } from '../modals/tournament'
import { MatchModal } from '../modals/match'
import { TeamPickerModal } from '../modals/team'
import { StageManagerModal } from '../modals/stage'
import { MatchStatsModal } from '../modals/matchStats'
import { formatDateTime } from '../utils/datetime'
import { groupByStage } from '../utils/match'

export function TournamentPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const tournamentId = Number(id)
  const { data: tournament, isLoading: tLoading, error: tError } = useGetTournamentQuery(tournamentId)
  const { data: matches, isLoading: mLoading, error: mError } = useListMatchesQuery(tournamentId)
  const { data: groups = [] } = useListGroupsQuery(tournamentId)
  const [searchParams, setSearchParams] = useSearchParams()
  const [showAllPast, setShowAllPast] = useState(false)
  const [, setRenderTick] = useState(0)
  useEffect(() => {
    if (!matches) return
    const now = Date.now()
    const timeouts = matches.flatMap((m) => {
      const startMs = new Date(m.start_datetime).getTime()
      const endMs = startMs + 100 * 60 * 1000
      const delay = endMs - now
      if (now >= startMs && delay > 0) {
        return [setTimeout(() => setRenderTick((n) => n + 1), delay)]
      }
      return []
    })
    return () => timeouts.forEach(clearTimeout)
  }, [matches])
  const [showEditTournament, setShowEditTournament] = useState(false)
  const [editingMatch, setEditingMatch] = useState<Match | null>(null)
  const [showAddMatch, setShowAddMatch] = useState(false)
  const [showTeamPicker, setShowTeamPicker] = useState(false)
  const [showStageManager, setShowStageManager] = useState(false)
  const { data: me } = useGetMeQuery()
  const filterIso = searchParams.get('country')
  const filterGroupId = searchParams.get('group') ? Number(searchParams.get('group')) : null
  const statsMatchId = searchParams.get('match') ? Number(searchParams.get('match')) : null

  function toggleFilter(_teamId: number | null, isoCode: string | null) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      if (!isoCode || (filterIso === isoCode)) {
        next.delete('country')
      } else {
        next.set('country', isoCode)
      }
      return next
    }, { replace: true })
  }

  if (tLoading) {
    return (
      <PageShell>
        <div className="flex h-48 items-center justify-center p-8 text-gray-500 dark:text-gray-400">
          Loading Tournament…
        </div>
      </PageShell>
    )
  }

  if (tError || !tournament) {
    return (
      <PageShell>
        <div className="p-6 sm:p-8 space-y-4 max-w-md">
          <h2 className="text-lg font-semibold text-red-500 dark:text-red-400">SweepStake not found</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            If a friend invited you to their SweepStake, ask them for a <span className="font-mono font-semibold text-gray-800 dark:text-gray-200">join code</span> and enter it on the overview page to join.
          </p>
          <button
            onClick={() => navigate('/overview')}
            className="inline-flex items-center gap-1.5 rounded-full border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 hover:border-blue-400 hover:text-blue-600 dark:hover:border-blue-500 dark:hover:text-blue-400 transition"
          >
            <ArrowLeft size={14} />
            Go to overview
          </button>
        </div>
      </PageShell>
    )
  }

  const isAdmin = tournament.admin_lst.some((u) => u.id === me?.id)
  const editButton = isAdmin ? (
    <button
      onClick={() => setShowEditTournament(true)}
      className="inline-flex items-center gap-1.5 rounded-full border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 hover:border-blue-400 hover:text-blue-600 dark:hover:border-blue-500 dark:hover:text-blue-400 transition"
    >
      <Pencil size={14} />
      Edit
    </button>
  ) : undefined

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

  const cutoff = new Date(Date.now() - 36 * 60 * 60 * 1000)

  const sortedMatches = [...(matches ?? [])].sort(
    (a, b) => new Date(a.start_datetime).getTime() - new Date(b.start_datetime).getTime(),
  )
  const filteredMatches = sortedMatches
    .filter((m) => filterIso == null || m.home_team?.iso_code === filterIso || m.away_team?.iso_code === filterIso)
    .filter((m) => filterGroupId == null || m.home_team?.group_id === filterGroupId || m.away_team?.group_id === filterGroupId)
  const hiddenPastCount = filteredMatches.filter((m) => new Date(m.start_datetime) < cutoff).length
  const visibleMatches = showAllPast
    ? filteredMatches
    : filteredMatches.filter((m) => new Date(m.start_datetime) >= cutoff)
  const grouped = groupByStage(visibleMatches)

  return (
    <PageShell>
      {showEditTournament && (
        <EditTournamentModal tournament={tournament} onClose={() => setShowEditTournament(false)} />
      )}
      {editingMatch != null && (
        <MatchModal tournamentId={tournamentId} match={editingMatch} onClose={() => setEditingMatch(null)} />
      )}
      {showAddMatch && (
        <MatchModal tournamentId={tournamentId} onClose={() => setShowAddMatch(false)} />
      )}
      {showStageManager && (
        <StageManagerModal tournamentId={tournamentId} onClose={() => setShowStageManager(false)} />
      )}
      {showTeamPicker && (
        <TeamPickerModal
          tournamentId={tournamentId}
          onSelect={(teamId) => {
            const team = matches?.flatMap((m) => [m.home_team, m.away_team]).find((t) => t?.id === teamId)
            if (team?.iso_code) toggleFilter(teamId, team.iso_code)
          }}
          onClose={() => setShowTeamPicker(false)}
        />
      )}
      {statsMatchId != null && (
        <MatchStatsModal
          matchId={statsMatchId}
          tournamentId={tournamentId}
          match={matches?.find((m) => m.id === statsMatchId)}
          onClose={() =>
            setSearchParams((prev) => {
              const next = new URLSearchParams(prev)
              next.delete('match')
              return next
            }, { replace: true })
          }
        />
      )}
      <div className="p-6 sm:p-8 space-y-8">
        <TournamentPageHeader
          tournament={tournament}
          currentUserId={me?.id}
          rightActions={editButton}
        />

        {/* Rules */}
        {rules.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold mb-3">Scoring Rules</h2>
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
          </section>
        )}

        {/* Matches */}
        <section>
          <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 mb-3">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-semibold">Matches</h2>
              {isAdmin && (
                <button
                  onClick={() => setShowAddMatch(true)}
                  className="inline-flex items-center gap-1 rounded-full bg-blue-600 hover:bg-blue-700 px-2.5 py-1 text-xs font-medium text-white transition"
                >
                  <Plus size={13} />
                  Add
                </button>
              )}
              {isAdmin && (
                <button
                  onClick={() => setShowTeamPicker(true)}
                  className="inline-flex items-center gap-1 rounded-full border border-gray-300 dark:border-gray-600 px-2.5 py-1 text-xs font-medium text-gray-600 dark:text-gray-400 hover:border-blue-400 hover:text-blue-500 dark:hover:text-blue-400 transition"
                >
                  <Pencil size={12} />
                  Teams
                </button>
              )}
              {isAdmin && (
                <button
                  onClick={() => setShowStageManager(true)}
                  className="inline-flex items-center gap-1 rounded-full border border-gray-300 dark:border-gray-600 px-2.5 py-1 text-xs font-medium text-gray-600 dark:text-gray-400 hover:border-blue-400 hover:text-blue-500 dark:hover:text-blue-400 transition"
                >
                  <Pencil size={12} />
                  Stages
                </button>
              )}
              {filterIso != null && (() => {
                const team = matches?.find(
                  (m) => m.home_team?.iso_code === filterIso || m.away_team?.iso_code === filterIso,
                )
                const name = team?.home_team?.iso_code === filterIso
                  ? team?.home_team?.name
                  : team?.away_team?.name
                return (
                  <button
                    onClick={() => toggleFilter(null, null)}
                    className="flex items-center gap-1 rounded-full bg-blue-100 dark:bg-blue-900 px-3 py-0.5 text-xs font-medium text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-800 transition"
                  >
                    {name ?? filterIso} <span aria-hidden>×</span>
                  </button>
                )
              })()}
              {filterGroupId != null && (() => {
                const group = groups.find((g) => g.id === filterGroupId)
                return (
                  <button
                    onClick={() => setSearchParams((prev) => {
                      const next = new URLSearchParams(prev)
                      next.delete('group')
                      return next
                    }, { replace: true })}
                    className="flex items-center gap-1 rounded-full bg-blue-100 dark:bg-blue-900 px-3 py-0.5 text-xs font-medium text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-800 transition"
                  >
                    Group {group?.name ?? filterGroupId} <span aria-hidden>×</span>
                  </button>
                )
              })()}
            </div>
            {groups.length > 1 && (
              <select
                value={filterGroupId ?? ''}
                onChange={(e) => setSearchParams((prev) => {
                  const next = new URLSearchParams(prev)
                  if (e.target.value === '') next.delete('group')
                  else next.set('group', e.target.value)
                  return next
                }, { replace: true })}
                className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm text-gray-700 dark:text-gray-300 py-1 px-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
              >
                <option value="">All groups</option>
                {groups.map((g) => (
                  <option key={g.id} value={g.id}>Group {g.name}</option>
                ))}
              </select>
            )}
          </div>

          {mLoading && (
            <p className="text-gray-500 dark:text-gray-400">Loading matches…</p>
          )}

          {mError && (
            <p className="text-red-500 dark:text-red-400">Failed to load matches.</p>
          )}

          {!mLoading && !mError && grouped.size === 0 && visibleMatches.length === 0 && hiddenPastCount === 0 && (
            <p className="text-gray-500 dark:text-gray-400">No matches scheduled yet.</p>
          )}

          {!showAllPast && hiddenPastCount > 0 && (
            <button
              onClick={() => setShowAllPast(true)}
              className="mb-4 w-full flex items-center gap-3 rounded-lg border border-dashed border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800/50 px-4 py-3 text-sm text-gray-500 dark:text-gray-400 hover:border-gray-400 dark:hover:border-gray-500 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700/50 transition group"
            >
              <span className="flex-1 border-t border-dashed border-gray-300 dark:border-gray-600 group-hover:border-gray-400 dark:group-hover:border-gray-500 transition" />
              <span className="flex items-center gap-1.5 whitespace-nowrap font-medium">
                <svg className="h-4 w-4 rotate-180" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                  <path fillRule="evenodd" d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z" clipRule="evenodd" />
                </svg>
                {hiddenPastCount} past {hiddenPastCount === 1 ? 'match' : 'matches'}
                <svg className="h-4 w-4 rotate-180" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                  <path fillRule="evenodd" d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z" clipRule="evenodd" />
                </svg>
              </span>
              <span className="flex-1 border-t border-dashed border-gray-300 dark:border-gray-600 group-hover:border-gray-400 dark:group-hover:border-gray-500 transition" />
            </button>
          )}

          {(() => { let nowLineInserted = false; const nowMs = Date.now(); return Array.from(grouped.entries()).map(([stage, stageMatches]) => (
            <div key={stage} className="mb-6">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2">
                {stage}
              </h3>
              <ul className="space-y-2">
                {stageMatches.map((match) => {
                  const homeGoals = match.home_goals
                  const awayGoals = match.away_goals
                  const hasScore = homeGoals != null && awayGoals != null
                  const matchStartMs = new Date(match.start_datetime).getTime()
                  const isLive = matchStartMs <= nowMs && nowMs <= matchStartMs + 100 * 60 * 1000
                  if (isLive) nowLineInserted = true
                  const showNow = !nowLineInserted && matchStartMs >= nowMs
                  if (showNow) nowLineInserted = true
                  return (
                    <Fragment key={match.id}>
                      {showNow && (
                        <li className="flex items-center gap-2 pointer-events-none select-none">
                          <span className="relative flex h-3 w-3 flex-shrink-0">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                            <span className="relative inline-flex h-3 w-3 rounded-full bg-red-500" />
                          </span>
                          <span className="flex-1 h-0.5 bg-red-500 relative overflow-hidden rounded-full">
                            <span className="animate-now-line-left bg-gradient-to-r from-transparent via-white to-transparent" />
                          </span>
                          <span className="text-xs font-semibold text-red-500 whitespace-nowrap animate-now-text tabular-nums">
                            <Countdown targetMs={matchStartMs} onZero={() => setRenderTick(n => n + 1)} />
                          </span>
                          <span className="flex-1 h-0.5 bg-red-500 relative overflow-hidden rounded-full">
                            <span className="animate-now-line bg-gradient-to-r from-transparent via-white to-transparent" />
                          </span>
                          <span className="text-xs font-semibold text-red-500 whitespace-nowrap animate-now-text">Now</span>
                        </li>
                      )}
                    <li
                      className={[
                        'grid grid-cols-[1fr_auto_1fr] sm:grid-cols-[auto_1fr_auto_1fr_auto] items-center gap-x-2 gap-y-1 sm:gap-2 rounded-lg border bg-white dark:bg-gray-800 px-4 py-3',
                        isLive ? 'animate-live-border' : 'border-gray-200 dark:border-gray-700',
                      ].join(' ')}
                    >
                      {/* Date / time — row 1 left on mobile, col 1 on desktop */}
                      <span className="row-start-1 col-start-1 sm:row-auto sm:col-auto text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap sm:w-36">
                        {isLive ? (
                          <span className="flex items-center gap-1.5">
                            <span className="relative flex h-2.5 w-2.5 flex-shrink-0">
                              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
                            </span>
                            <span className="font-semibold text-red-500 animate-now-text tabular-nums">
                              Live <ElapsedTime
                                startMs={matchStartMs}
                                maxMs={matchStartMs + 100 * 60 * 1000}
                                onMax={() => setRenderTick((n) => n + 1)}
                              />
                            </span>
                          </span>
                        ) : (
                          formatDateTime(match.start_datetime)
                        )}
                      </span>

                      {/* Home team: name + crest — row 2 left on mobile, col 2 on desktop */}
                      <div
                        onClick={() => toggleFilter(match.home_team_id ?? null, match.home_team?.iso_code ?? null)}
                        className={[
                          'row-start-2 col-start-1 sm:row-auto sm:col-auto group flex items-center justify-end gap-2 rounded-lg px-2 py-1 cursor-pointer transition',
                          filterIso != null && filterIso === match.home_team?.iso_code
                            ? 'bg-blue-100 dark:bg-blue-900'
                            : 'hover:bg-gray-100 dark:hover:bg-gray-700',
                        ].join(' ')}
                      >
                        <span className="text-sm text-right text-gray-900 dark:text-gray-100 truncate">
                          {match.home_team?.name ?? '—'}
                        </span>
                        {match.home_team?.image_url ? (
                          <img
                            src={match.home_team.image_url}
                            alt={match.home_team.name}
                            decoding="async"
                            referrerPolicy="no-referrer"
                            className="h-7 w-7 flex-shrink-0 rounded-full object-cover border border-gray-200 dark:border-gray-700"
                          />
                        ) : (
                          <span className="h-7 w-7 flex-shrink-0 rounded-full bg-gray-200 dark:bg-gray-700 inline-block" />
                        )}
                      </div>

                      {/* Score — row 2 center on mobile, col 3 on desktop */}
                      <span className="row-start-2 col-start-2 sm:row-auto sm:col-auto min-w-[48px] text-center text-sm font-mono font-semibold text-gray-700 dark:text-gray-300">
                        {hasScore ? `${homeGoals} – ${awayGoals}` : 'vs'}
                      </span>

                      {/* Away team: crest + name — row 2 right on mobile, col 4 on desktop */}
                      <div
                        onClick={() => toggleFilter(match.away_team_id ?? null, match.away_team?.iso_code ?? null)}
                        className={[
                          'row-start-2 col-start-3 sm:row-auto sm:col-auto group flex items-center justify-start gap-2 rounded-lg px-2 py-1 cursor-pointer transition',
                          filterIso != null && filterIso === match.away_team?.iso_code
                            ? 'bg-blue-100 dark:bg-blue-900'
                            : 'hover:bg-gray-100 dark:hover:bg-gray-700',
                        ].join(' ')}
                      >
                        {match.away_team?.image_url ? (
                          <img
                            src={match.away_team.image_url}
                            alt={match.away_team.name}
                            decoding="async"
                            referrerPolicy="no-referrer"
                            className="h-7 w-7 flex-shrink-0 rounded-full object-cover border border-gray-200 dark:border-gray-700"
                          />
                        ) : (
                          <span className="h-7 w-7 flex-shrink-0 rounded-full bg-gray-200 dark:bg-gray-700 inline-block" />
                        )}
                        <span className="text-sm text-left text-gray-900 dark:text-gray-100 truncate">
                          {match.away_team?.name ?? '—'}
                        </span>
                      </div>

                      {/* Broadcaster — row 1 right on mobile, col 5 on desktop */}
                      <div className="row-start-1 col-start-3 justify-self-end sm:row-auto sm:col-auto sm:justify-self-auto sm:w-28 flex items-center gap-1.5 sm:justify-end">
                        {match.tv_channel && (
                          <span className="text-xs font-medium text-gray-400 dark:text-gray-500 whitespace-nowrap truncate">
                            {match.tv_channel}
                          </span>
                        )}
                        {isAdmin && (
                          <button
                            onClick={() => setEditingMatch(match)}
                            className="text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 transition"
                            aria-label="Edit match"
                          >
                            <Pencil size={13} />
                          </button>
                        )}
                        {matchStartMs <= nowMs && (
                          <button
                            onClick={() =>
                              setSearchParams((prev) => {
                                const next = new URLSearchParams(prev)
                                next.set('match', String(match.id))
                                return next
                              }, { replace: true })
                            }
                            className="text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 transition flex-shrink-0"
                            aria-label="View match stats"
                          >
                            <Search size={13} />
                          </button>
                        )}
                      </div>
                    </li>
                    </Fragment>
                  )
                })}
              </ul>
            </div>
          )); })()}
        </section>
      </div>
    </PageShell>
  )
}
