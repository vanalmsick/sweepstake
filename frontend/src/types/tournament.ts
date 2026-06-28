import type { TeamRead } from './team'

export type PredictionsOpen = 'automatic' | 'open' | 'closed'

export type MatchScoreMethod = 'final' | 'no-penalty' | 'regular-time'

export interface FootballDataOrgTournament {
  id: number
  name: string
  area: string
  current_season_start: string | null
  current_season_end: string | null
  emblem_url: string | null
}


export interface TournamentUser {
  id: number
  user_name: string | null
  stake_paid: boolean
}

export interface Tournament {
  id: number
  name: string
  stake: string | null
  join_code: string | null
  football_data_org_id: number | null
  first_place_team_id: number | null
  second_place_team_id: number | null
  third_place_team_id: number | null
  first_place_points: number | null
  second_place_points: number | null
  third_place_points: number | null
  match_winner_points: number | null
  match_score_points: number | null
  group_winner_points: number | null
  stage_winner_points: number | null
  predictions_open: PredictionsOpen
  match_score_method: MatchScoreMethod
  admin_lst: TournamentUser[]
  participant_lst: TournamentUser[]
  start_date: string | null
  end_date: string | null
  first_place: TeamRead | null
  second_place: TeamRead | null
  third_place: TeamRead | null
}

export interface TournamentCreate {
  name: string
  stake?: string | null
  football_data_org_id?: number
  first_place_team_id?: number
  second_place_team_id?: number
  third_place_team_id?: number
  first_place_points?: number
  second_place_points?: number
  third_place_points?: number
  match_winner_points?: number
  match_score_points?: number
  group_winner_points?: number
  stage_winner_points?: number
  predictions_open?: PredictionsOpen
  match_score_method?: MatchScoreMethod
}

export type TournamentUpdate = Partial<TournamentCreate>

export interface TournamentMemberUpdate {
  user_id: number
  role: 'admin' | 'participant'
  action: 'add' | 'remove'
}

export interface TournamentStakePaidUpdate {
  user_id: number
  stake_paid: boolean
}

export type TournamentAdminAction =
  | 'send-payment-reminder'
  | 'update-tournament'
  | 'send-welcome-email'

export interface TournamentAdminActionRequest {
  action: TournamentAdminAction
}
