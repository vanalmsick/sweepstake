import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BellRing, CircleDollarSign, Crown, HelpCircle, Loader2, RefreshCw, UserX } from 'lucide-react'
import {
  useCreateTournamentMutation,
  useUpdateTournamentMutation,
  useDeleteTournamentMutation,
  useManageTournamentMemberMutation,
  useSetStakePaidMutation,
  useSendAdminActionMutation,
} from '../api/tournamentApi'
import { useGetParticipantActivityQuery } from '../api/statsApi'
import type { PredictionsOpen, MatchScoreMethod, TournamentAdminAction } from '../types'
import { useListFootballDataOrgTournamentsQuery } from '../api/footballDataOrgApi'
import { useListTeamsQuery } from '../api/teamApi'
import { useGetMeQuery } from '../api/authApi'
import type { Tournament } from '../types'
import {
  BtnDanger,
  BtnPrimary,
  BtnSecondary,
  ErrorMsg,
  FieldLabel,
  ModalBody,
  ModalFooter,
  ModalShell,
  fieldClass,
} from './base'

// ---------------------------------------------------------------------------
// Shared point-scoring fields used by both Create and Edit
// ---------------------------------------------------------------------------

type PointState = {
  firstPlacePoints: string
  setFirstPlacePoints: (v: string) => void
  secondPlacePoints: string
  setSecondPlacePoints: (v: string) => void
  thirdPlacePoints: string
  setThirdPlacePoints: (v: string) => void
  matchWinnerPoints: string
  setMatchWinnerPoints: (v: string) => void
  matchScorePoints: string
  setMatchScorePoints: (v: string) => void
  groupWinnerPoints: string
  setGroupWinnerPoints: (v: string) => void
  stageWinnerPoints: string
  setStageWinnerPoints: (v: string) => void
}

function PointFields(p: PointState & { disabled?: boolean }) {
  const fields = [
    { label: '🥇 1st place points', value: p.firstPlacePoints, set: p.setFirstPlacePoints },
    { label: '🥈 2nd place points', value: p.secondPlacePoints, set: p.setSecondPlacePoints },
    { label: '🥉 3rd place points', value: p.thirdPlacePoints, set: p.setThirdPlacePoints },
    { label: '⚽ Match winner points', value: p.matchWinnerPoints, set: p.setMatchWinnerPoints },
    { label: '🎯 Exact score points', value: p.matchScorePoints, set: p.setMatchScorePoints },
    { label: '👥 Group winner points', value: p.groupWinnerPoints, set: p.setGroupWinnerPoints },
    { label: '🏆 Stage winner points', value: p.stageWinnerPoints, set: p.setStageWinnerPoints },
  ]
  return (
    <div className="grid grid-cols-2 gap-3">
      {fields.map(({ label, value, set }) => (
        <div key={label}>
          <FieldLabel>{label}</FieldLabel>
          <input
            type="number"
            min="0"
            value={value}
            onChange={(e) => set(e.target.value)}
            placeholder="—"
            disabled={p.disabled}
            className={fieldClass}
          />
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Edit-only: point fields interleaved with team winner dropdowns
// ---------------------------------------------------------------------------

type EditPointAndTeamState = PointState & {
  tournamentId: number
  firstPlaceTeamId: string
  setFirstPlaceTeamId: (v: string) => void
  secondPlaceTeamId: string
  setSecondPlaceTeamId: (v: string) => void
  thirdPlaceTeamId: string
  setThirdPlaceTeamId: (v: string) => void
  disabled?: boolean
}

function EditPointAndTeamFields(p: EditPointAndTeamState) {
  const { data: teams = [], isLoading: teamsLoading } = useListTeamsQuery(p.tournamentId)

  const teamSelect = (value: string, set: (v: string) => void) =>
    teamsLoading ? (
      <div className={`${fieldClass} flex items-center gap-2 text-gray-400 dark:text-gray-500`}>
        <Loader2 className="animate-spin h-4 w-4 flex-shrink-0" />
        <span className="text-sm">Loading teams…</span>
      </div>
    ) : (
      <select
        value={value}
        onChange={(e) => set(e.target.value)}
        disabled={p.disabled}
        className={fieldClass}
      >
        <option value="">— none —</option>
        {teams.map((t) => (
          <option key={t.id} value={t.id}>
            {t.name}
          </option>
        ))}
      </select>
    )

  const numInput = (value: string, set: (v: string) => void) => (
    <input
      type="number"
      min="0"
      value={value}
      onChange={(e) => set(e.target.value)}
      placeholder="—"
      disabled={p.disabled}
      className={fieldClass}
    />
  )

  return (
    <div className="grid grid-cols-2 gap-3">
      <div>
        <FieldLabel>🥇 1st place points</FieldLabel>
        {numInput(p.firstPlacePoints, p.setFirstPlacePoints)}
      </div>
      <div>
        <FieldLabel>🥇 1st place winner</FieldLabel>
        {teamSelect(p.firstPlaceTeamId, p.setFirstPlaceTeamId)}
      </div>
      <div>
        <FieldLabel>🥈 2nd place points</FieldLabel>
        {numInput(p.secondPlacePoints, p.setSecondPlacePoints)}
      </div>
      <div>
        <FieldLabel>🥈 2nd place winner</FieldLabel>
        {teamSelect(p.secondPlaceTeamId, p.setSecondPlaceTeamId)}
      </div>
      <div>
        <FieldLabel>🥉 3rd place points</FieldLabel>
        {numInput(p.thirdPlacePoints, p.setThirdPlacePoints)}
      </div>
      <div>
        <FieldLabel>🥉 3rd place winner</FieldLabel>
        {teamSelect(p.thirdPlaceTeamId, p.setThirdPlaceTeamId)}
      </div>
      <div>
        <FieldLabel>🏆 Stage winner points</FieldLabel>
        {numInput(p.stageWinnerPoints, p.setStageWinnerPoints)}
      </div>
      <div>
        <FieldLabel>👥 Group winner points</FieldLabel>
        {numInput(p.groupWinnerPoints, p.setGroupWinnerPoints)}
      </div>
      <div>
        <FieldLabel>🎯 Exact score points</FieldLabel>
        {numInput(p.matchScorePoints, p.setMatchScorePoints)}
      </div>
      <div>
        <FieldLabel>⚽ Match winner points</FieldLabel>
        {numInput(p.matchWinnerPoints, p.setMatchWinnerPoints)}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Shared tournament info fields (name, stake, fdo tournament)
// ---------------------------------------------------------------------------

function TournamentInfoFields({
  name,
  setName,
  stake,
  setStake,
  footballDataOrgId,
  setFootballDataOrgId,
  predictionsOpen,
  setPredictionsOpen,
  matchScoreMethod,
  setMatchScoreMethod,
  autoFocusName,
  disabled,
}: {
  name: string
  setName: (v: string) => void
  stake: string
  setStake: (v: string) => void
  footballDataOrgId: string
  setFootballDataOrgId: (v: string) => void
  predictionsOpen: PredictionsOpen
  setPredictionsOpen: (v: PredictionsOpen) => void
  matchScoreMethod: MatchScoreMethod
  setMatchScoreMethod: (v: MatchScoreMethod) => void
  autoFocusName?: boolean
  disabled?: boolean
}) {
  const { data: fdoTournaments, isLoading: fdoLoading } = useListFootballDataOrgTournamentsQuery()
  return (
    <>
      <div>
        <FieldLabel>Name</FieldLabel>
        <input
          autoFocus={autoFocusName}
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={disabled}
          className={fieldClass}
        />
      </div>
      <div>
        <FieldLabel>Stake / Prize <i>(empty if no entry stake)</i></FieldLabel>
        <textarea
          value={stake}
          onChange={(e) => setStake(e.target.value)}
          rows={3}
          placeholder="Describe the stake or prize… URLs will be auto-linked."
          disabled={disabled}
          className={`${fieldClass} resize-y`}
        />
      </div>
      <div>
        <FieldLabel>Football-data.org tournament <i>(recommended)</i></FieldLabel>
        {fdoLoading ? (
          <div className={`${fieldClass} flex items-center gap-2 text-gray-400 dark:text-gray-500`}>
            <Loader2 className="animate-spin h-4 w-4 flex-shrink-0" />
            <span className="text-sm">Loading tournaments…</span>
          </div>
        ) : (
          <select
            value={footballDataOrgId}
            onChange={(e) => setFootballDataOrgId(e.target.value)}
            disabled={disabled}
            className={fieldClass}
          >
            <option value="">— none —</option>
            {fdoTournaments?.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        )}
      </div>
      <div>
        <FieldLabel>
          Predictions Open{' '}
          <span className="relative inline-flex items-center group/tip cursor-help">
            <HelpCircle size={13} className="text-gray-400 dark:text-gray-500" />
            <span className="pointer-events-none absolute bottom-full left-0 mb-2 w-72 rounded-lg bg-gray-800 dark:bg-gray-900 text-white text-xs font-normal px-3 py-2 shadow-lg opacity-0 group-hover/tip:opacity-100 transition-opacity z-50 normal-case tracking-normal leading-relaxed">
              With <strong>Automatic</strong>, tournament, group, and stage predictions are automatically closed on the day of their respective first match.
              {' '}<strong>Open</strong> keeps those predictions open regardless of schedule.
              {' '}<strong>Closed</strong> prevents users from submitting tournament, group, and stage predictions.
              {' '}Match predictions are always controlled by the individual match kick-off time.
              {' '}Admins can always update other users' predictions.
              <span className="absolute top-full left-3 border-4 border-transparent border-t-gray-800 dark:border-t-gray-900" />
            </span>
          </span>
        </FieldLabel>
        <select
          value={predictionsOpen}
          onChange={(e) => setPredictionsOpen(e.target.value as PredictionsOpen)}
          disabled={disabled}
          className={fieldClass}
        >
          <option value="automatic">Automatic</option>
          <option value="open">Open</option>
          <option value="closed">Closed</option>
        </select>
      </div>
      <div>
        <FieldLabel>
          Match Score Method{' '}
          <span className="relative inline-flex items-center group/tip cursor-help">
            <HelpCircle size={13} className="text-gray-400 dark:text-gray-500" />
            <span className="pointer-events-none absolute bottom-full left-0 mb-2 w-72 rounded-lg bg-gray-800 dark:bg-gray-900 text-white text-xs font-normal px-3 py-2 shadow-lg opacity-0 group-hover/tip:opacity-100 transition-opacity z-50 normal-case tracking-normal leading-relaxed">
              <strong>Final Score</strong>: Includes regular time, extra time, and penalties.
              {' '}<strong>Excluding Penalties</strong>: Includes regular time and extra time, but excludes penalty shootouts.
              {' '}<strong>Regular Time Only</strong>: Only the score at the end of regular time (90 minutes), excluding extra time and penalties.
              <span className="absolute top-full left-3 border-4 border-transparent border-t-gray-800 dark:border-t-gray-900" />
            </span>
          </span>
        </FieldLabel>
        <select
          value={matchScoreMethod}
          onChange={(e) => setMatchScoreMethod(e.target.value as MatchScoreMethod)}
          disabled={disabled}
          className={fieldClass}
        >
          <option value="final">Final Score (regular time + extra time + penalties)</option>
          <option value="no-penalty">Score Excluding Penalties (regular time + extra time; no penalties)</option>
          <option value="regular-time">Regular Time Score (regular time; no extra time &amp; penalties)</option>
        </select>
      </div>
    </>
  )
}

// ---------------------------------------------------------------------------
// CreateTournamentModal
// ---------------------------------------------------------------------------

export function CreateTournamentModal({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate()
  const [createTournament, { isLoading }] = useCreateTournamentMutation()

  const [name, setName] = useState('')
  const [stake, setStake] = useState("Please contribute a €5 stake to the pot. The SweepStake winner receives 50% of the pot, with the remaining 50% donated to a charity of the winner's choosing.\nwww.PayPal.com/{your_name/5\n[Remove this text entirely if there is no stake.]")
  const [footballDataOrgId, setFootballDataOrgId] = useState('')
  const [firstPlacePoints, setFirstPlacePoints] = useState('25')
  const [secondPlacePoints, setSecondPlacePoints] = useState('15')
  const [thirdPlacePoints, setThirdPlacePoints] = useState('')
  const [matchWinnerPoints, setMatchWinnerPoints] = useState('3')
  const [matchScorePoints, setMatchScorePoints] = useState('5')
  const [groupWinnerPoints, setGroupWinnerPoints] = useState('8')
  const [stageWinnerPoints, setStageWinnerPoints] = useState('')
  const [predictionsOpen, setPredictionsOpen] = useState<PredictionsOpen>('automatic')
  const [matchScoreMethod, setMatchScoreMethod] = useState<MatchScoreMethod>('no-penalty')
  const [error, setError] = useState<string | null>(null)

  async function handleCreate() {
    if (!name.trim()) return
    setError(null)
    try {
      const tournament = await createTournament({
        name: name.trim(),
        stake: stake.trim() || null,
        football_data_org_id: footballDataOrgId !== '' ? Number(footballDataOrgId) : undefined,
        first_place_points: firstPlacePoints !== '' ? Number(firstPlacePoints) : undefined,
        second_place_points: secondPlacePoints !== '' ? Number(secondPlacePoints) : undefined,
        third_place_points: thirdPlacePoints !== '' ? Number(thirdPlacePoints) : undefined,
        match_winner_points: matchWinnerPoints !== '' ? Number(matchWinnerPoints) : undefined,
        match_score_points: matchScorePoints !== '' ? Number(matchScorePoints) : undefined,
        group_winner_points: groupWinnerPoints !== '' ? Number(groupWinnerPoints) : undefined,
        stage_winner_points: stageWinnerPoints !== '' ? Number(stageWinnerPoints) : undefined,
        predictions_open: predictionsOpen,
        match_score_method: matchScoreMethod,
      }).unwrap()
      onClose()
      navigate(`/tournament/${tournament.id}?guide=admin`)
    } catch {
      setError('Failed to create tournament. Please try again.')
    }
  }

  return (
    <ModalShell title="Create Tournament" onClose={onClose}>
      <ModalBody scrollable>
        <TournamentInfoFields
          name={name}
          setName={setName}
          stake={stake}
          setStake={setStake}
          footballDataOrgId={footballDataOrgId}
          setFootballDataOrgId={setFootballDataOrgId}
          predictionsOpen={predictionsOpen}
          setPredictionsOpen={setPredictionsOpen}
          matchScoreMethod={matchScoreMethod}
          setMatchScoreMethod={setMatchScoreMethod}
          autoFocusName
          disabled={isLoading}
        />
        <PointFields
          firstPlacePoints={firstPlacePoints}
          setFirstPlacePoints={setFirstPlacePoints}
          secondPlacePoints={secondPlacePoints}
          setSecondPlacePoints={setSecondPlacePoints}
          thirdPlacePoints={thirdPlacePoints}
          setThirdPlacePoints={setThirdPlacePoints}
          matchWinnerPoints={matchWinnerPoints}
          setMatchWinnerPoints={setMatchWinnerPoints}
          matchScorePoints={matchScorePoints}
          setMatchScorePoints={setMatchScorePoints}
          groupWinnerPoints={groupWinnerPoints}
          setGroupWinnerPoints={setGroupWinnerPoints}
          stageWinnerPoints={stageWinnerPoints}
          setStageWinnerPoints={setStageWinnerPoints}
          disabled={isLoading}
        />
        <ErrorMsg msg={error} />
      </ModalBody>
      <ModalFooter>
        <BtnSecondary onClick={onClose}>Cancel</BtnSecondary>
        <BtnPrimary onClick={handleCreate} disabled={isLoading || !name.trim()} loading={isLoading}>
          {isLoading ? 'Creating…' : 'Create'}
        </BtnPrimary>
      </ModalFooter>
    </ModalShell>
  )
}

// ---------------------------------------------------------------------------
// EditTournamentModal
// ---------------------------------------------------------------------------

export function EditTournamentModal({
  tournament,
  onClose,
}: {
  tournament: Tournament
  onClose: () => void
}) {
  const navigate = useNavigate()
  const { data: me } = useGetMeQuery()
  const [updateTournament, { isLoading: isSaving }] = useUpdateTournamentMutation()
  const [deleteTournament, { isLoading: isDeleting }] = useDeleteTournamentMutation()
  const [manageMember] = useManageTournamentMemberMutation()
  const [setStakePaid] = useSetStakePaidMutation()
  const [sendAdminAction, { isLoading: isActionLoading }] = useSendAdminActionMutation()
  const { data: participantActivity = [] } = useGetParticipantActivityQuery(tournament.id)
  const activityMap = Object.fromEntries(participantActivity.map((a) => [a.user_id, a]))
  const [currentAction, setCurrentAction] = useState<TournamentAdminAction | null>(null)
  const isLoading = isSaving || isDeleting

  const COOLDOWN_MS = 30 * 60 * 1000
  const lsKey = (action: TournamentAdminAction) => `action_cooldown_${tournament.id}_${action}`
  const [lastTriggered, setLastTriggered] = useState<Partial<Record<TournamentAdminAction, number>>>(() => {
    const actions: TournamentAdminAction[] = ['send-payment-reminder', 'update-tournament', 'send-welcome-email']
    return Object.fromEntries(
      actions.flatMap((a) => {
        const v = localStorage.getItem(lsKey(a))
        return v ? [[a, parseInt(v, 10)]] : []
      })
    )
  })
  function minsLeft(action: TournamentAdminAction): number | null {
    const ts = lastTriggered[action]
    if (!ts) return null
    const left = COOLDOWN_MS - (Date.now() - ts)
    return left > 0 ? Math.ceil(left / 60_000) : null
  }

  const [name, setName] = useState(tournament.name)
  const [stake, setStake] = useState(tournament.stake ?? '')
  const [footballDataOrgId, setFootballDataOrgId] = useState(
    tournament.football_data_org_id?.toString() ?? '',
  )
  const [firstPlacePoints, setFirstPlacePoints] = useState(
    tournament.first_place_points?.toString() ?? '',
  )
  const [secondPlacePoints, setSecondPlacePoints] = useState(
    tournament.second_place_points?.toString() ?? '',
  )
  const [thirdPlacePoints, setThirdPlacePoints] = useState(
    tournament.third_place_points?.toString() ?? '',
  )
  const [matchWinnerPoints, setMatchWinnerPoints] = useState(
    tournament.match_winner_points?.toString() ?? '',
  )
  const [matchScorePoints, setMatchScorePoints] = useState(
    tournament.match_score_points?.toString() ?? '',
  )
  const [groupWinnerPoints, setGroupWinnerPoints] = useState(
    tournament.group_winner_points?.toString() ?? '',
  )
  const [stageWinnerPoints, setStageWinnerPoints] = useState(
    tournament.stage_winner_points?.toString() ?? '',
  )
  const [firstPlaceTeamId, setFirstPlaceTeamId] = useState(
    tournament.first_place_team_id?.toString() ?? '',
  )
  const [secondPlaceTeamId, setSecondPlaceTeamId] = useState(
    tournament.second_place_team_id?.toString() ?? '',
  )
  const [thirdPlaceTeamId, setThirdPlaceTeamId] = useState(
    tournament.third_place_team_id?.toString() ?? '',
  )
  const [predictionsOpen, setPredictionsOpen] = useState<PredictionsOpen>(
    tournament.predictions_open ?? 'automatic',
  )
  const [matchScoreMethod, setMatchScoreMethod] = useState<MatchScoreMethod>(
    tournament.match_score_method ?? 'no-penalty',
  )
  const [error, setError] = useState<string | null>(null)
  const [memberError, setMemberError] = useState<string | null>(null)

  async function handleToggleStakePaid(userId: number, isCurrentlyPaid: boolean) {
    setMemberError(null)
    try {
      await setStakePaid({
        id: tournament.id,
        data: { user_id: userId, stake_paid: !isCurrentlyPaid },
      }).unwrap()
    } catch {
      setMemberError('Failed to update stake payment status.')
    }
  }

  async function handleToggleAdmin(userId: number, isCurrentlyAdmin: boolean) {
    if (
      isCurrentlyAdmin &&
      userId === me?.id &&
      !window.confirm(
        'Remove yourself as admin? If you are the last admin the tournament will be permanently deleted.',
      )
    )
      return
    setMemberError(null)
    try {
      await manageMember({
        id: tournament.id,
        data: { user_id: userId, role: 'admin', action: isCurrentlyAdmin ? 'remove' : 'add' },
      }).unwrap()
    } catch {
      setMemberError('Failed to update admin status.')
    }
  }

  async function handleRemoveParticipant(userId: number, isCurrentlyAdmin: boolean) {
    const isSelf = userId === me?.id
    const displayName =
      tournament.participant_lst.find((p) => p.id === userId)?.user_name ?? `User #${userId}`
    const message = isSelf
      ? 'Remove yourself from this tournament? This cannot be undone.'
      : `Remove "${displayName}" from this tournament? This cannot be undone.`
    if (!window.confirm(message)) return
    setMemberError(null)
    try {
      if (isCurrentlyAdmin) {
        await manageMember({
          id: tournament.id,
          data: { user_id: userId, role: 'admin', action: 'remove' },
        }).unwrap()
      }
      await manageMember({
        id: tournament.id,
        data: { user_id: userId, role: 'participant', action: 'remove' },
      }).unwrap()
      if (isSelf) {
        onClose()
        navigate('/overview')
      }
    } catch {
      setMemberError('Failed to remove participant.')
    }
  }

  async function handleAdminAction(action: TournamentAdminAction) {
    setError(null)
    setCurrentAction(action)
    try {
      await sendAdminAction({ id: tournament.id, action }).unwrap()
      const now = Date.now()
      localStorage.setItem(lsKey(action), String(now))
      setLastTriggered((prev) => ({ ...prev, [action]: now }))
    } catch {
      setError('Failed to perform action. Please try again.')
    } finally {
      setCurrentAction(null)
    }
  }

  async function handleDelete() {
    if (
      !window.confirm(
        `Delete "${tournament.name}"? This cannot be undone. All user predictions will also be unrecoverably deleted.`,
      )
    )
      return
    setError(null)
    try {
      await deleteTournament(tournament.id).unwrap()
      onClose()
      navigate('/overview')
    } catch {
      setError('Failed to delete tournament. Please try again.')
    }
  }

  async function handleSave() {
    setError(null)
    try {
      await updateTournament({
        id: tournament.id,
        data: {
          name: name || undefined,
          stake: stake.trim() || null,
          football_data_org_id: footballDataOrgId !== '' ? Number(footballDataOrgId) : undefined,
          first_place_team_id: firstPlaceTeamId !== '' ? Number(firstPlaceTeamId) : undefined,
          second_place_team_id: secondPlaceTeamId !== '' ? Number(secondPlaceTeamId) : undefined,
          third_place_team_id: thirdPlaceTeamId !== '' ? Number(thirdPlaceTeamId) : undefined,
          first_place_points: firstPlacePoints !== '' ? Number(firstPlacePoints) : undefined,
          second_place_points: secondPlacePoints !== '' ? Number(secondPlacePoints) : undefined,
          third_place_points: thirdPlacePoints !== '' ? Number(thirdPlacePoints) : undefined,
          match_winner_points: matchWinnerPoints !== '' ? Number(matchWinnerPoints) : undefined,
          match_score_points: matchScorePoints !== '' ? Number(matchScorePoints) : undefined,
          group_winner_points: groupWinnerPoints !== '' ? Number(groupWinnerPoints) : undefined,
          stage_winner_points: stageWinnerPoints !== '' ? Number(stageWinnerPoints) : undefined,
          predictions_open: predictionsOpen,
          match_score_method: matchScoreMethod,
        },
      }).unwrap()
      onClose()
    } catch {
      setError('Failed to save changes. Please try again.')
    }
  }

  return (
    <ModalShell title="Edit Tournament" onClose={onClose}>
      <ModalBody scrollable>
        <TournamentInfoFields
          name={name}
          setName={setName}
          stake={stake}
          setStake={setStake}
          footballDataOrgId={footballDataOrgId}
          setFootballDataOrgId={setFootballDataOrgId}
          predictionsOpen={predictionsOpen}
          setPredictionsOpen={setPredictionsOpen}
          matchScoreMethod={matchScoreMethod}
          setMatchScoreMethod={setMatchScoreMethod}
          disabled={isLoading}
        />
        <EditPointAndTeamFields
          tournamentId={tournament.id}
          firstPlacePoints={firstPlacePoints}
          setFirstPlacePoints={setFirstPlacePoints}
          secondPlacePoints={secondPlacePoints}
          setSecondPlacePoints={setSecondPlacePoints}
          thirdPlacePoints={thirdPlacePoints}
          setThirdPlacePoints={setThirdPlacePoints}
          matchWinnerPoints={matchWinnerPoints}
          setMatchWinnerPoints={setMatchWinnerPoints}
          matchScorePoints={matchScorePoints}
          setMatchScorePoints={setMatchScorePoints}
          groupWinnerPoints={groupWinnerPoints}
          setGroupWinnerPoints={setGroupWinnerPoints}
          stageWinnerPoints={stageWinnerPoints}
          setStageWinnerPoints={setStageWinnerPoints}
          firstPlaceTeamId={firstPlaceTeamId}
          setFirstPlaceTeamId={setFirstPlaceTeamId}
          secondPlaceTeamId={secondPlaceTeamId}
          setSecondPlaceTeamId={setSecondPlaceTeamId}
          thirdPlaceTeamId={thirdPlaceTeamId}
          setThirdPlaceTeamId={setThirdPlaceTeamId}
          disabled={isLoading}
        />
        <div>
          <FieldLabel>Participants</FieldLabel>
          <ul className="space-y-1">
            {tournament.participant_lst.map((p) => {
              const participantIsAdmin = tournament.admin_lst.some((a) => a.id === p.id)
              const activity = activityMap[p.id]
              return (
                <li
                  key={p.id}
                  className="group rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <span className="flex-1 min-w-0 text-sm text-gray-800 dark:text-gray-200 truncate">
                      {p.user_name ?? `User #${p.id}`}
                    </span>
                  {participantIsAdmin && (
                    <span className="flex-shrink-0 rounded-full bg-blue-100 dark:bg-blue-900/60 px-1.5 py-0.5 text-xs font-medium text-blue-700 dark:text-blue-300">
                      admin
                    </span>
                  )}
                  {tournament.stake && (
                    <button
                      type="button"
                      onClick={() => handleToggleStakePaid(p.id, p.stake_paid)}
                      title={p.stake_paid ? 'Mark stake as unpaid' : 'Mark stake as paid'}
                      className={[
                        'flex-shrink-0 p-1 rounded transition',
                        p.stake_paid
                          ? 'text-green-500 hover:text-green-700 dark:text-green-400 dark:hover:text-green-200'
                          : 'text-gray-400 hover:text-green-500 dark:hover:text-green-400',
                      ].join(' ')}
                    >
                      <CircleDollarSign size={14} />
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => handleToggleAdmin(p.id, participantIsAdmin)}
                    title={participantIsAdmin ? 'Demote from admin' : 'Promote to admin'}
                    className={[
                      'flex-shrink-0 p-1 rounded transition',
                      participantIsAdmin
                        ? 'text-yellow-500 hover:text-yellow-600 dark:text-yellow-400 dark:hover:text-yellow-300'
                        : 'text-gray-400 hover:text-yellow-500 dark:hover:text-yellow-400',
                    ].join(' ')}
                  >
                    <Crown size={14} />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleRemoveParticipant(p.id, participantIsAdmin)}
                    title="Remove from competition"
                    className="flex-shrink-0 p-1 rounded text-gray-400 hover:text-red-500 dark:hover:text-red-400 transition"
                  >
                    <UserX size={14} />
                  </button>
                  </div>
                  {activity && (
                    <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-0.5 hidden group-hover:flex">
                      <span className="text-xs text-gray-500 dark:text-gray-400">🏆 Tournament: {activity.tournament_predictions}</span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">🏅 Stage: {activity.stage_predictions}</span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">👥 Group: {activity.group_predictions}</span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">⚽ Match: {activity.match_predictions}</span>
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-3"><b>Note:</b> 💲 user paid stake; 👑 promote to admin; ❌ remove from competition.</p>
          <ErrorMsg msg={memberError} />
        </div>
        <div className="flex flex-wrap gap-2">
          {tournament.stake && (() => {
            const mins = minsLeft('send-payment-reminder')
            return (
              <button
                type="button"
                onClick={() => handleAdminAction('send-payment-reminder')}
                disabled={isLoading || isActionLoading || mins !== null}
                title={mins !== null ? `Available again in ~${mins} min` : undefined}
                className="inline-flex items-center gap-1 rounded-full border border-gray-300 dark:border-gray-600 px-2.5 py-1 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 transition"
              >
                {currentAction === 'send-payment-reminder'
                  ? <Loader2 size={12} className="animate-spin" />
                  : <BellRing size={12} />}
                {currentAction === 'send-payment-reminder'
                  ? 'Sending…'
                  : mins !== null ? `Sending Payment Reminders… (~${mins}m)` : 'Send Payment Reminders'}
              </button>
            )
          })()}
          {tournament.football_data_org_id && (() => {
            const mins = minsLeft('update-tournament')
            return (
              <button
                type="button"
                onClick={() => handleAdminAction('update-tournament')}
                disabled={isLoading || isActionLoading || mins !== null}
                title={mins !== null ? `Available again in ~${mins} min` : undefined}
                className="inline-flex items-center gap-1 rounded-full border border-gray-300 dark:border-gray-600 px-2.5 py-1 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 transition"
              >
                {currentAction === 'update-tournament'
                  ? <Loader2 size={12} className="animate-spin" />
                  : <RefreshCw size={12} />}
                {currentAction === 'update-tournament'
                  ? 'Updating…'
                  : mins !== null ? `API Updating… (~${mins}m)` : 'API Update'}
              </button>
            )
          })()}
          {/* {(() => {
            const mins = minsLeft('send-welcome-email')
            return (
              <button
                type="button"
                onClick={() => handleAdminAction('send-welcome-email')}
                disabled={isLoading || isActionLoading || mins !== null}
                title={mins !== null ? `Available again in ~${mins} min` : undefined}
                className="inline-flex items-center gap-1 rounded-full border border-gray-300 dark:border-gray-600 px-2.5 py-1 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 transition"
              >
                {currentAction === 'send-welcome-email'
                  ? <Loader2 size={12} className="animate-spin" />
                  : <Mail size={12} />}
                {currentAction === 'send-welcome-email'
                  ? 'Sending…'
                  : mins !== null ? `Re-Sending Welcome Email… (~${mins}m)` : 'Re-Send Welcome Emails'}
              </button>
            )
          })()} */}
        </div>
        <ErrorMsg msg={error} />
      </ModalBody>
      <ModalFooter justify="between">
        <BtnDanger onClick={handleDelete} disabled={isLoading || isActionLoading} loading={isDeleting}>
          {isDeleting ? 'Deleting…' : 'Delete'}
        </BtnDanger>
        <div className="flex gap-2">
          <BtnSecondary onClick={onClose}>Cancel</BtnSecondary>
          <BtnPrimary onClick={handleSave} disabled={isLoading} loading={isSaving}>
            {isSaving ? 'Saving…' : 'Save'}
          </BtnPrimary>
        </div>
      </ModalFooter>
    </ModalShell>
  )
}
